"""Declared sparse terms have explicit ids; omitted ids are invalid input controls."""

import re
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
ORDERS = [5, 0, 3]
IDS = ['high', 'floor', 'bend']
COEFFICIENTS = [8.125, 17.25, -2.75]
FREE = [True, False, True]


def materialize(destination, kind, *, explicit=True, references=False):
    destination = Path(destination)
    shutil.copytree(HERE.parent / 'loop_parameter_ids' / kind, destination, dirs_exist_ok=True)
    file = destination / 'experiments/bank.edi'
    text = file.read_text()
    tags = '_background.id\n' if explicit else ''
    block = 'loop_\n' + tags + '_background.order\n_background.coef\n'
    for identity, order, coefficient, free in zip(IDS, ORDERS, COEFFICIENTS, FREE, strict=True):
        block += (
            identity + ' ' if explicit else ''
        ) + f'{order} {coefficient}{"()" if free else ""}\n'
    text = re.sub(
        r'loop_\n_background.id\n_background.order\n_background.coef\n[^\n]+\n[^\n]+\n[^\n]+\n',
        block,
        text,
        count=1,
    )
    file.write_text(text)
    if references:
        analysis = destination / 'analysis/analysis.edi'
        analysis.write_text(
            analysis.read_text()
            + """
loop_
_alias.id
_alias.parameter_unique_name
upper bank.background.high.coef
lower bank.background.floor.coef
bend bank.background.bend.coef

loop_
_constraint.id
_constraint.expression
relation "bend = 2*upper - 19"

loop_
_fit_parameter.id
_fit_parameter.start_value
_fit_parameter.start_uncertainty
bank.background.high 8.125 0.375
bank.background.floor 17.25 0.75

loop_
_fit_parameter_correlation.id
_fit_parameter_correlation.source_kind
_fit_parameter_correlation.parameter_unique_name_i
_fit_parameter_correlation.parameter_unique_name_j
_fit_parameter_correlation.correlation
_fit_parameter_correlation.file_path
pair deterministic bank.background.high.coef bank.background.floor.coef -0.625 high.xy
"""
        )
    return destination


def saved_rows(destination):
    lines = (Path(destination) / 'experiments/bank.edi').read_text().splitlines()
    tags, rows, active = [], [], False
    for line in lines:
        words = line.split()
        if words == ['loop_']:
            tags, active = [], True
        elif active and words and words[0].startswith('_'):
            if len(words) == 1:
                tags.append(words[0])
            else:
                active = False
        elif active and words and '_background.order' in tags:
            rows.append(dict(zip(tags, words, strict=True)))
    return rows


if __name__ == '__main__':
    for kind in ['polynomial', 'chebyshev']:
        materialize(HERE / 'projects' / ('ids-' + kind + '-explicit'), kind, references=True)
