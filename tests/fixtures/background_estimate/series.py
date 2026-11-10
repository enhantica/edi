"""Independent cubic inputs and saved-series readers; no estimator output is generated."""

import shlex
from pathlib import Path

import numpy as np

from tests.fixtures.background_estimate.project import materialize

HERE = Path(__file__).resolve().parent


def project(destination, kind):
    path = HERE / 'series' / ('known-' + kind + '.oracle')
    lines = path.read_text().splitlines()
    count, origin, low, high, _noise, _terms, _budget = map(float, lines[0].split())
    values = np.asarray([list(map(float, line.split())) for line in lines[1 : 1 + int(count)]])
    row = {
        'input_file': 'series/known-' + kind + '.xye',
        'beam_mode': 'constant wavelength',
        'active_endpoints': values[[0, -1], 0],
        'excluded': [],
    }
    destination = materialize(destination, row, kind=kind)
    file = destination / 'experiments/bank.edi'
    text = file.read_text().replace('_background.origin 80', f'_background.origin {origin:.17g}')
    if kind == 'chebyshev':
        for label, value in [('x_min', low), ('x_max', high)]:
            import re  # noqa: PLC0415

            text = re.sub(
                rf'(?m)^_background\.{label} .*$', f'_background.{label} {value:.17g}', text
            )
    file.write_text(text)
    return destination


def terms(destination):
    lines = (Path(destination) / 'experiments/bank.edi').read_text().splitlines()
    tags, result, active = [], [], False
    for line in lines:
        words = shlex.split(line, comments=True)
        if words == ['loop_']:
            tags, active = [], True
        elif active and words and words[0].startswith('_'):
            if len(words) == 1:
                tags.append(words[0])
            else:
                active = False
        elif active and words and '_background.order' in tags:
            row = dict(zip(tags, words, strict=True))
            result.append((
                int(row['_background.order']),
                float(row['_background.coef'].split('(')[0]),
            ))
    return result
