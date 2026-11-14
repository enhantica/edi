"""Read the owner's grouped scan table and replay its small terminal control vocabulary."""

import re

ROW = re.compile(r'^[█░]{10}  \s*\d+\.\d%  \s*\d+/\d+(?:\s|$)')


def table_rows(text):
    return [line for line in text.splitlines() if ROW.match(line)]


def cells(line):
    groups = line.split(' │ ')
    assert len(groups) == 5, 'Scan rows retain all five groups, including empty final cells'
    progress, counts, clocks, metrics, filename = [group.strip() for group in groups]
    amounts = progress.split()
    assert len(amounts) in {1, 3}, (
        'Progress contains the count and, for known totals, bar and percent'
    )
    counts = counts.split()
    clocks = clocks.split()
    metrics = metrics.split()
    assert len(counts) == 2, 'The count group retains independent successful and failed totals'
    assert 1 <= len(clocks) <= 2, 'The clock group keeps elapsed and an optional estimate'
    assert len(metrics) <= 2, 'The metric group contains last Chi2 and the observed Chi2 range'
    return {
        'bar': amounts[0] if len(amounts) == 3 else '',
        'percent': amounts[1] if len(amounts) == 3 else '',
        'count': amounts[-1],
        'ok': counts[0],
        'failed': counts[1],
        'elapsed': clocks[0],
        'left': clocks[1] if len(clocks) == 2 else '',
        'chi2': metrics[0] if metrics else '',
        'range': metrics[1] if len(metrics) == 2 else '',
        'file': filename,
    }


def terminal_lines(stream):
    rows, row, column = [[]], 0, 0
    position = 0
    while position < len(stream):
        escape = re.match(r'\x1b\[(\d*)([AK])', stream[position:])
        if escape:
            amount = int(escape[1] or '1')
            if escape[2] == 'A':
                row = max(0, row - amount)
            elif amount == 2:
                rows[row] = []
            else:
                rows[row] = rows[row][:column]
            position += len(escape[0])
            continue
        character = stream[position]
        if character == '\r':
            column = 0
        elif character == '\n':
            row += 1
            column = 0
            if row == len(rows):
                rows.append([])
        else:
            while len(rows[row]) <= column:
                rows[row].append(' ')
            rows[row][column] = character
            column += 1
        position += 1
    while rows and not rows[-1]:
        rows.pop()
    return [''.join(line).rstrip() for line in rows]
