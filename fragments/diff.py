def _visible_in_diff(merge_result, context_lines=3):
    """Collects the set of lines that should be visible in a diff with a certain number of context lines"""
    i = old_line = new_line = 0
    while i < len(merge_result):
        line_or_conflict = merge_result[i]
        if isinstance(line_or_conflict, tuple):
            yield old_line, new_line, line_or_conflict
            old_line += len(line_or_conflict[0])
            new_line += len(line_or_conflict[1])
        else:
            should_yield = False
            for ibefore in range(max(0, i-context_lines), i): # look behind
                if isinstance(merge_result[ibefore], tuple):
                    should_yield = True
                    break
            for iafter in range(i+1, min(len(merge_result), i+1+context_lines)): # look ahead
                if isinstance(merge_result[iafter], tuple):
                    should_yield = True
                    break
            if should_yield:
                yield old_line, new_line, line_or_conflict
            else:
                yield None
            old_line += 1
            new_line += 1
        i += 1
    yield None


def _split_diff(merge_result, context_lines=3):
    """Split diffs and context lines into groups based on None sentinel"""
    collect = []
    for item in _visible_in_diff(merge_result, context_lines=context_lines):
        if item is None:
            if collect:
                yield collect
            collect = []
        else:
            collect.append(item)


def _diff_group_position(group):
    """Generate a unified diff position line for a diff group"""
    old_start = group[0][0]
    new_start = group[0][1]
    old_length = new_length = 0
    for old_line, new_line, line_or_conflict in group:
        if isinstance(line_or_conflict, tuple):
            old, new = line_or_conflict
            old_length += len(old)
            new_length += len(new)
        else:
            old_length += 1
            new_length += 1
    if old_length:
        old_start += 1
    if new_length:
        new_start += 1

    return '@@ -%s,%s +%s,%s @@' % (old_start, old_length, new_start, new_length)


def _diff_group(group):
    """Generate a diff section for diff group"""
    yield _diff_group_position(group)

    for old_line, new_line, line_or_conflict in group:
        if isinstance(line_or_conflict, tuple):
            old, new = line_or_conflict
            for o in old:
                yield '-' + o.strip('\n')
            for n in new:
                yield '+' + n.strip('\n')
        else:
            yield ' ' + line_or_conflict.strip('\n')


def _full_diff(merge_result, key, context_lines=3):
    """Generate a full diff based on a Weave merge result"""
    header_printed = False
    for group in _split_diff(merge_result, context_lines=context_lines):
        if not header_printed:
            header_printed = True
            yield '--- %s' % key
            yield '+++ %s' % key

        for l in _diff_group(group):
            yield l
