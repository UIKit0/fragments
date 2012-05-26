import os
import argparse
import pdb

from .precisecodevillemerge import Weave
from .config import FragmentsConfig
from .diff import _diff_group, _split_diff
from . import Prompt


def apply(*args):
    """Revert changes to fragments repository"""
    parser = argparse.ArgumentParser(prog="%s apply" % __package__, description="Apply changes in FILENAME that were made since last commit to as many other followed files as possible.")
    parser.add_argument('FILENAME', help="file containing changes to be applied")
    parser.add_argument('-U', '--unified', type=int, dest="NUM", default=3, action="store", help="number of lines of context to show")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-i", "--interactive", action="store_true" , default=True , dest="interactive", help="interactively select changes to apply")
    group.add_argument("-a", "--automatic"  , action="store_false", default=False, dest="interactive", help="automatically apply all changes")
    args = parser.parse_args(args)

    config = FragmentsConfig()
    weave = Weave()
    changed_path = os.path.realpath(args.FILENAME)
    changed_key = changed_path[len(config.root)+1:]
    if changed_key not in config['files']:
        yield "Could not apply changes in %r, it is not being followed" % changed_key
        return
    elif not os.access(changed_path, os.R_OK|os.W_OK):
        yield "Could not apply changes in %r, it no longer exists on disk" % changed_key
        return

    changed_uuid = config['files'][changed_key]
    old_path = os.path.join(config.directory, changed_uuid)

    if not os.access(old_path, os.R_OK|os.W_OK):
        yield "Could not apply changes in %r, it has never been committed" % changed_key
        return

    old_revision = 1
    weave.add_revision(old_revision, file(old_path, 'r').readlines(), [])
    new_revision = 2
    weave.add_revision(new_revision, file(changed_path, 'r').readlines(), [])

    changes_to_apply = []
    diff = weave.merge(old_revision, new_revision)
    display_groups = _split_diff(diff, context_lines=args.NUM)

    i = 0
    old_line = 0 # not sure I need to be keeping track of these
    new_line = 0
    while i < len(diff):
        line_or_tuple = diff[i]
        if isinstance(line_or_tuple, tuple):
            display_group = next(display_groups)
            for dl in _diff_group(display_group): # show the group
                yield dl
            if args.interactive:
                response = (yield Prompt("Apply this change? y/n"))
                if response.lower().startswith('y'):
                    apply_change = True
                elif response.lower().startswith('n'):
                    apply_change = False
            else:
                apply_change = True

            while isinstance(display_group[0][-1], basestring):
                display_group.pop(0) # preceeding context lines have already been added to the changes to apply

            for display_line_or_tuple in display_group:
                if isinstance(display_line_or_tuple[-1], tuple):
                    old, new = display_line_or_tuple[-1]
                    old_line += len(old)
                    new_line += len(new)
                    i += 1
                    if apply_change:
                        changes_to_apply.extend(new)
                    else:
                        changes_to_apply.extend(old)
                else:
                    old_line += 1
                    new_line += 1
                    i += 1
                    changes_to_apply.append(display_line_or_tuple[-1])
        else:
            old_line += 1
            new_line += 1
            i += 1
            changes_to_apply.append(line_or_tuple)

    changed_revision = 3
    weave.add_revision(changed_revision, changes_to_apply, [1])

    current_revision = changed_revision
    for other_key in config['files']:
        other_path = os.path.join(config.root, other_key)
        if other_path == changed_path:
            continue # don't try to apply changes to ourself
        current_revision += 1
        weave.add_revision(current_revision, file(other_path, 'r').readlines(), [])
        merge_result = weave.cherry_pick(changed_revision, current_revision) # Can I apply changes in changed_revision onto this other file?
        if tuple in (type(mr) for mr in merge_result):
            if len(merge_result) == 1 and isinstance(merge_result[0], tuple):
                # total conflict, skip
                yield "Changes in %r cannot apply to %r, skipping" % (changed_key, other_key)
                continue
            other_file = file(other_path, 'w')
            for line_or_conflict in merge_result:
                if isinstance(line_or_conflict, basestring):
                    other_file.write(line_or_conflict)
                else:
                    other_file.write('>'*7 + '\n')
                    for line in line_or_conflict[0]:
                        other_file.write(line)
                    other_file.write('='*7 + '\n')
                    for line in line_or_conflict[1]:
                        other_file.write(line)
                    other_file.write('>'*7 + '\n')
            other_file.close()
            yield "Conflict merging %r => %r" % (changed_key, other_key)
        else:
            # Merge is clean:
            other_file = file(other_path, 'w')
            other_file.writelines(merge_result)
            other_file.close()
            yield "Changes in %r applied cleanly to %r" % (changed_key, other_key)
