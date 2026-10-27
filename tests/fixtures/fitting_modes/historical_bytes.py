"""Retain old analysis hashes across the declared inactive-weight removal.

Only restore the historical inactive weights loop, from committed input weights
and the saved experiment inventory. Everything else remains byte-identical.
"""

import re
import shlex


def historical_analysis(source, saved):
    tokens = shlex.split(saved.decode())
    if '_fitting_mode.type' not in tokens:
        return saved
    mode = tokens[tokens.index('_fitting_mode.type') + 1]
    if mode == 'joint':
        return saved
    assert mode in {'single', 'sequential', 'independent'}, (
        'Inactive-weight projection requires a declared non-joint mode'
    )
    assert b'_joint_fit.' not in saved, (
        'Non-joint saved bytes must omit the entire inactive joint-weight category'
    )
    loop = _historical_weights(source)
    # Fit-result/start-state categories followed the old weights loop. Its preceding
    # blank separator was removed together with the inactive loop.
    boundary = re.search(
        rb'(?m)^(_fit_result\.|loop_\n_fit_(?:parameter|correlation|start)\.)', saved
    )
    index = boundary.start() if boundary else len(saved)
    prefix, suffix = saved[:index], saved[index:]
    if suffix:
        assert prefix.endswith(b'\n\n'), (
            'The historical-weight boundary before a result must have its original separator'
        )
        return prefix + loop + b'\n' + suffix
    assert prefix.endswith(b'\n'), (
        'Non-joint fitless bytes must have exactly their declared final newline'
    )
    assert not prefix.endswith(b'\n\n'), (
        'Non-joint fitless bytes must have exactly their declared final newline'
    )
    return prefix + b'\n' + loop


def _historical_weights(source):
    names = []
    for path in sorted((source / 'experiments').glob('*.edi')):
        # Only the declared block key is needed here. Stop the same STAR lexer
        # at that key instead of tokenizing thousands of irrelevant data rows.
        cells = shlex.shlex(path.read_text(), posix=True)
        cells.whitespace_split = True
        cells.commenters = ''
        block = next(cell[5:] for cell in cells if cell.startswith('data_'))
        assert re.fullmatch(r'[A-Za-z0-9_-]+', block), (
            'Historical-weight projection requires an unambiguous declared experiment key'
        )
        names.append(block)
    assert names, 'Historical-weight projection requires an experiment inventory'
    assert len(names) == len(set(names)), (
        'Historical-weight projection must retain every unique experiment identity'
    )
    weights = dict.fromkeys(names, '1')
    analysis = source / 'analysis/analysis.edi'
    if analysis.is_file():
        cells = shlex.split(analysis.read_text())
        if '_joint_fit.experiment_id' in cells:
            start = cells.index('_joint_fit.experiment_id')
            assert cells[start - 1] == 'loop_', (
                'Historical-weight projection requires an original weight loop'
            )
            assert cells[start + 1] == '_joint_fit.weight', (
                'Historical-weight projection admits only the original two-column weight loop'
            )
            i = start + 2
            seen = set()
            while i < len(cells) and not cells[i].startswith(('_', 'loop_', 'data_')):
                name, number = cells[i : i + 2]
                assert name in weights, (
                    'Historical-weight projection must not hide an unknown experiment row'
                )
                assert name not in seen, (
                    'Historical-weight projection must not hide duplicate experiment rows'
                )
                seen.add(name)
                weights[name] = format(float(number), '.17g')
                i += 2
    loop = b'loop_\n_joint_fit.experiment_id\n_joint_fit.weight\n'
    loop += ''.join(f'{name} {weights[name]}\n' for name in names).encode()
    return loop
