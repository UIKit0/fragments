import os
import argparse

from .precisecodevillemerge import Weave
from .config import FragmentsConfig
from .diff import _diff_group, _split_diff
from .color import Prompt
from . import _iterate_over_files


def apply(*args):
    """
    Apply changes in SOURCE_FILENAME that were made since last commit, where possible.
    Limit application to TARGET_FILENAME(s) if specified.
    Files that conflict in their entirety will be skipped.
    Smaller conflicts will be written to the file as conflict sections.
    """
    parser = argparse.ArgumentParser(prog="%s %s" % (__package__, apply.__name__), description=apply.__doc__)
    parser.add_argument('SOURCE_FILENAME', help="file containing changes to be applied")
    parser.add_argument('TARGET_FILENAME', help="file(s) to apply changes to", nargs='*')
    parser.add_argument('-U', '--unified', type=int, dest="NUM", default=3, action="store", help="number of lines of context to show")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-i", "--interactive", action="store_true" , default=True , dest="interactive", help="interactively select changes to apply")
    group.add_argument("-a", "--automatic"  , action="store_false", default=False, dest="interactive", help="automatically apply all changes")
    args = parser.parse_args(args)

    config = FragmentsConfig()
    weave = Weave()
    changed_path = os.path.realpath(args.SOURCE_FILENAME)
    changed_key = os.path.relpath(changed_path, config.root)
    if changed_key not in config['files']:
        yield "Could not apply changes in '%s', it is not being followed" % os.path.relpath(changed_path)
        return
    elif not os.access(changed_path, os.R_OK|os.W_OK):
        yield "Could not apply changes in '%s', it no longer exists on disk" % os.path.relpath(changed_path)
        return

    old_path = os.path.join(config.directory, config['files'][changed_key])

    if not os.access(old_path, os.R_OK|os.W_OK):
        yield "Could not apply changes in '%s', it has never been committed" % os.path.relpath(changed_path)
        return

    old_revision = 1
    weave.add_revision(old_revision, open(old_path, 'r').readlines(), [])
    new_revision = 2
    weave.add_revision(new_revision, open(changed_path, 'r').readlines(), [])

    diff = weave.merge(old_revision, new_revision)

    # Select the chunks to be applied, possibly interactively
    preserve_changes = {}
    discard_changes = {}
    display_groups = list(_split_diff(diff, context_lines=args.NUM))
    index = 0
    while display_groups:
        display_group = display_groups[index]
        for dl in _diff_group(display_group):
            yield dl
        while True:
            if args.interactive:
                response = (yield Prompt("Apply this change? y/n/j/k")).lower()
            if not args.interactive or response.startswith('y'):
                for old_line, new_line, line_or_conflict in display_group:
                    if isinstance(line_or_conflict, tuple):
                        preserve_changes[(old_line, new_line)] = line_or_conflict
                display_groups.pop(index)
                break
            elif response.startswith('n'):
                for old_line, new_line, line_or_conflict in display_group:
                    if isinstance(line_or_conflict, tuple):
                        discard_changes[(old_line, new_line)] = line_or_conflict
                display_groups.pop(index)
                break
            elif response == 'j':
                index = (index + 1) % len(display_groups)
                break
            elif response == 'k':
                index = (index - 1) % len(display_groups)
                break

    if not preserve_changes:
        yield "No changes in '%s' to apply." % os.path.relpath(changed_path)
        return

    # Build the changed file to be applied
    changes_to_apply = []

    i = 0
    old_line = 0
    new_line = 0
    while i < len(diff):
        line_or_conflict = diff[i]
        if isinstance(line_or_conflict, tuple):
            old, new = line_or_conflict
            if (old_line, new_line) in preserve_changes:
                changes_to_apply.extend(new)
            elif (old_line, new_line) in discard_changes:
                changes_to_apply.extend(old)
            else: # pragma: no cover
                raise Exception("Catastrophic error in selecting diff chunks. Please report a bug.")
            old_line += len(old)
            new_line += len(new)
            i += 1
        else:
            old_line += 1
            new_line += 1
            i += 1
            changes_to_apply.append(line_or_conflict)

    # Apply the changes across other files
    changed_revision = 3
    weave.add_revision(changed_revision, changes_to_apply, [1])

    current_revision = changed_revision
    for other_path in _iterate_over_files(args.TARGET_FILENAME, config):
        other_key = os.path.relpath(other_path, config.root)
        if other_path == changed_path:
            continue # don't try to apply changes to ourself
        current_revision += 1
        weave.add_revision(current_revision, open(other_path, 'r').readlines(), [])
        merge_result = weave.cherry_pick(changed_revision, current_revision) # Can I apply changes in changed_revision onto this other file?
        if tuple in (type(mr) for mr in merge_result):
            if len(merge_result) == 1 and isinstance(merge_result[0], tuple):
                # total conflict, skip
                yield "Changes in '%s' cannot apply to '%s', skipping" % (os.path.relpath(changed_path), os.path.relpath(other_path))
                continue
            with file(other_path, 'w') as other_file:
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
            yield "Conflict merging '%s' into '%s'" % (os.path.relpath(changed_path), os.path.relpath(other_path))
        else:
            # Merge is clean:
            with file(other_path, 'w') as other_file:
                other_file.writelines(merge_result)
            yield "Changes in '%s' applied cleanly to '%s'" % (os.path.relpath(changed_path), os.path.relpath(other_path))
