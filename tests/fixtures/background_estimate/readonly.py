"""Mode-edit controls with explicit row ids; numbers are authored inputs, not estimates."""

import re
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
KINDS = ['line-segment', 'polynomial', 'chebyshev']


def materialize(destination, kind, *, excluded=False):
    destination = Path(destination)
    shutil.copytree(HERE.parent / 'loop_parameter_ids' / kind, destination)
    path = destination / 'experiments/bank.edi'
    text = path.read_text()
    tags = ('position', 'intensity') if kind == 'line-segment' else ('order', 'coef')
    block = 'loop_\n_background.id\n' + ''.join('_background.' + tag + '\n' for tag in tags)
    count = 12 if kind == 'line-segment' else (6 if kind == 'polynomial' else 8)
    if not excluded and kind != 'line-segment':
        count = 3
    for index in range(count):
        x = 40 + 2.5 * index if kind == 'line-segment' else index
        value = 17.25 + index * 0.125 if kind == 'line-segment' else 0.125 / (index + 1)
        block += f'r{index} {x} {value:.17g}' + ('()' if index % 2 == 0 else '') + '\n'
    text = re.sub(
        r'loop_\n_background.id\n(?:_background.\w+\n)+.*?(?=\nloop_|\Z)',
        block,
        text,
        count=1,
        flags=re.DOTALL,
    )
    if excluded:
        text += '\nloop_\n_excluded_region.start\n_excluded_region.end\n0 1000000000\n'
        # Two independent structures and two tensors exercise every offered loop family.
        structure = destination / 'structures/phase.edi'
        body = structure.read_text().replace('La a Biso', 'La a Bani')
        body += (
            '\nloop_\n_atom_site_aniso.id\n'
            + ''.join(
                '_atom_site_aniso.adp_' + key + '\n'
                for key in ['11', '22', '33', '12', '13', '23']
            )
            + 'A .3() .4 .5() .01 .02() .03\nB .4 .5() .6 .02() .03 .04()\n'
        )
        structure.write_text(body)
        (destination / 'structures/phase2.edi').write_text(
            body.replace('data_phase\n', 'data_phase2\n')
        )
        text = text.replace('phase 0.7\n', 'phase 0.7\nphase2 0.35()\n')
        text = text.replace(
            'phase 0.73 0.2 0 0 1\n', 'phase 0.73 0.2 0 0 1\nphase2 0.93() 0.15() 0 1 0\n'
        )
    text += '\n_background_estimate.mode manual\n_background_estimate.use_model ignore\n'
    path.write_text(text)
    return destination


def snapshot(project):
    experiment = project.experiment
    if experiment.background_type == 'line-segment':
        return [
            (getattr(row, 'id', ''), row.position, row.intensity.value, row.intensity.free)
            for row in experiment.background
        ]
    return [
        (getattr(row, 'id', ''), row.order, row.coef.value, row.coef.free)
        for row in experiment.background_terms
    ]


def edit(project, engine, field):  # noqa: PLR0912 - explicit independent edit channels
    experiment = project.experiment
    points = experiment.background_type == 'line-segment'
    rows = experiment.background if points else experiment.background_terms
    parameter = rows[0].intensity if points else rows[0].coef
    if field == 'id':
        rows[0].id = 'renamed'
    elif field == 'coordinate':
        if points:
            rows[0].position += 0.0625
        else:
            rows[0].order = 3
    elif field == 'value':
        parameter.value += 0.125
    elif field == 'free':
        parameter.free = not parameter.free
    else:
        if field == 'add':
            row = engine.LineSegment() if points else engine.PolynomialTerm()
            row.id = 'added'
            if points:
                row.position = 74.375
                row.intensity.value = 21.125
            else:
                row.order = 4
                row.coef.value = 0.03125
            rows = [*rows, row]
        elif field == 'remove':
            rows = list(rows)[1:]
        else:
            message = 'Unknown authored mode-edit operation'
            raise ValueError(message)
        if points:
            experiment.background = rows
        else:
            experiment.background_terms = rows


if __name__ == '__main__':
    for kind in KINDS:
        materialize(HERE / 'projects' / ('readonly-' + kind), kind, excluded=True)


def edit_saved(project, kind, field):
    """Change only one persisted row property, leaving the saved provenance intact."""
    path = Path(project) / 'experiments/bank.edi'
    lines = path.read_text().splitlines(keepends=True)
    start = lines.index('_background.id\n')
    end = start
    while end < len(lines) and lines[end].startswith('_background.'):
        end += 1
    tags = [line.strip() for line in lines[start:end]]
    stop = end
    while stop < len(lines) and lines[stop].strip() and not lines[stop].startswith(('_', 'loop_')):
        stop += 1
    rows = [line.split() for line in lines[end:stop]]
    if not rows:
        message = 'The saved Auto refusal control must have actual estimated rows'
        raise ValueError(message)
    token = 'position' if kind == 'line-segment' else 'order'
    value = 'intensity' if kind == 'line-segment' else 'coef'
    column = tags.index('_background.' + value)
    if field == 'id':
        rows[0][0] = 'edited-id'
    elif field == 'coordinate':
        index = tags.index('_background.' + token)
        rows[0][index] = str(float(rows[0][index]) + 0.0625) if kind == 'line-segment' else '5'
    elif field == 'value':
        rows[0][column] = str(float(rows[0][column].split('(')[0]) + 0.125)
    elif field == 'free':
        current = rows[0][column]
        rows[0][column] = current.split('(')[0] if '(' in current else current + '()'
    elif field == 'remove':
        if len(rows) < 2:
            message = 'The remove control needs at least two valid estimated rows'
            raise ValueError(message)
        rows.pop(0)
    elif field == 'add':
        row = list(rows[-1])
        row[0] = 'added'
        row[tags.index('_background.' + token)] = '74.375' if kind == 'line-segment' else '5'
        rows.append(row)
    else:
        message = 'Unknown saved row edit'
        raise ValueError(message)
    lines[end:stop] = [' '.join(row) + '\n' for row in rows]
    path.write_text(''.join(lines))
