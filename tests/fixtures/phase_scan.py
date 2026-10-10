"""Two-phase scan inputs from frozen bases and linear coefficients."""

import json
from pathlib import Path

import numpy as np

from tests.fixtures.constraint_expressions.project import materialize as relation_project
from tests.fixtures.multiphase import support

COEFFICIENTS = [(2.75, 0.375), (1.625, 0.8125), (3.125, 0.21875)]


def materialize(root, mode='sequential', *, negative=False, zero=False):
    root = support.write_project(root, scales={'alpha': '1.125()', 'beta': '0.875()'})
    basis = json.loads(
        (Path(__file__).parent / 'multiphase/scale-basis-regression-pin.json').read_text()
    )['basis']
    scan = root / 'experiments/scan'
    scan.mkdir()
    for index, (alpha, beta) in enumerate(COEFFICIENTS):
        values = alpha * np.asarray(basis['alpha']) + beta * np.asarray(basis['beta'])
        rows = [f'{x:.17g} {y:.17g} 1' for x, y in zip(support.grid(), values, strict=True)]
        if negative and index == 1:
            rows.insert(1, '25.1234 -7.25 1')
        (scan / f'{index + 1:02d}.xy').write_text('\n'.join(rows) + '\n')
    if zero:
        (scan / '02a.xy').write_text('\n'.join(f'{x:.17g} 0 1' for x in support.grid()) + '\n')
    (root / 'analysis/analysis.edi').write_text(
        '_edi.schema_version 3\n_minimizer.max_iterations 40\n'
        '_minimizer.chi_square_tolerance 1e-10\n'
        f'_fitting_mode.type {mode}\n'
        '_sequential_fit.data_dir experiments/scan\n'
        '_sequential_fit.file_pattern *.xy\n'
    )
    return root


def single(root, values, measured):
    return support.write_project(
        root,
        scales={
            name: f'{value:.17g}()' for name, value in zip(('alpha', 'beta'), values, strict=True)
        },
        measured=measured,
    )


def bounded_start(root, geometry, engine):
    many = geometry in {'phase_sum', 'scan'}
    aliases = [('a', 'bank.background.1.coef'), ('b', 'phase.atom_site.A.adp_iso')]
    expressions = ['b = a - 2']
    if many:
        aliases.append(('c', 'other.atom_site.A.adp_iso'))
        expressions.append('c = 2*a - 4')
    directory = relation_project(
        root,
        aliases,
        expressions,
        polynomial=True,
        second_structure=many,
        observations=[(40 + i, 4) for i in range(8)],
    )
    analysis = directory / 'analysis/analysis.edi'
    analysis.write_text(analysis.read_text() + '\n_minimizer.chi_square_tolerance 1e-10\n')
    project = engine.Project.load(directory)
    for key in list(project.experiments.keys()):
        experiment = project.experiments[key]
        for index, term in enumerate(experiment.background_terms):
            term.coef.free = False
            term.coef.value = 4 if index == 0 else 0
    project.experiments['bank'].background_terms[0].coef.free = True
    return project


def category_scan(root, mode, background='line-segment', *, texture_only=False):
    """Declared free fields, independently enumerated, across all parameter categories."""
    root = support.write_project(
        root,
        scales={'alpha': '1.125', 'beta': '0.875'},
        texture={
            'alpha': ('1.125()', '0.35()', (1, 0, 0)),
            'beta': ('0.925()', '0.25()', (0, 1, 0)),
        },
    )
    expected = {
        f'pattern.preferred_orientation.{name}.{field}'
        for name in ('alpha', 'beta')
        for field in ('march_r', 'march_random_fract')
    }
    if not texture_only:
        for name in ('alpha', 'beta'):
            path = root / f'structures/{name}.edi'
            text = path.read_text()
            lines = text.splitlines()
            lines = [line + '()' if line.startswith('_cell.length_a ') else line for line in lines]
            text = '\n'.join(lines) + '\n'
            text = text.replace('Biso 0 0 0 0.7 0.8', 'Biso 0.17() 0.23 0.31 0.7() 0.8()')
            if name == 'beta':
                text = text.replace('Biso ', 'Uani ').replace('0.8()', '0.8')
                text += (
                    '\nloop_\n_atom_site_aniso.id\n'
                    + ''.join(
                        f'_atom_site_aniso.adp_{key}\n'
                        for key in ('11', '22', '33', '12', '13', '23')
                    )
                    + 'X 0.01() 0.012 0.013 0 0 0\n'
                )
                expected.add('beta.atom_site_aniso.X.adp_11')
            else:
                expected.add('alpha.atom_site.X.adp_iso')
            path.write_text(text)
            expected.update({
                f'{name}.cell.length_a',
                f'{name}.atom_site.X.fract_x',
                f'{name}.atom_site.X.occupancy',
            })
        exp = root / 'experiments/pattern.edi'
        text = exp.read_text()
        for tag in (
            '_peak.broad_gauss_w',
            '_instrument.calib_twotheta_offset',
            '_instrument.setup_wavelength',
        ):
            lines = text.splitlines()
            text = (
                '\n'.join(line + '()' if line.startswith(tag + ' ') else line for line in lines)
                + '\n'
            )
        text = text.replace('alpha 1.125\n', 'alpha 1.125()\n').replace(
            'beta 0.875\n', 'beta 0.875()\n'
        )
        text += '\n_absorption.type cylinder-hewat\n_absorption.mu_r 0.25()\n'
        if background == 'line-segment':
            text += (
                '\n_background.type line-segment\nloop_\n_background.id\n'
                '_background.position\n_background.intensity\n1 15 4()\n2 90 4\n'
            )
            expected.add('pattern.background.1.intensity')
        else:
            origin = (
                '\n_background.origin 40\n'
                if background == 'polynomial'
                else '\n_background.x_min 15\n_background.x_max 90\n'
            )
            text += (
                '\n_background.type '
                + background
                + origin
                + 'loop_\n_background.id\n_background.order\n_background.coef\n1 0 4()\n'
            )
            expected.add('pattern.background.1.coef')
        exp.write_text(text)
        expected.update({
            'pattern.peak.broad_gauss_w',
            'pattern.instrument.twotheta_offset',
            'pattern.instrument.wavelength',
            'pattern.absorption.mu_r',
            'pattern.linked_structure.alpha.scale',
            'pattern.linked_structure.beta.scale',
        })
    scan = root / 'experiments/scan'
    scan.mkdir()
    for index in range(2):
        (scan / f'{index + 1:02d}.xy').write_text(
            ''.join(f'{15 + i * 0.75} {4.25 + i * 0.05 + index} 1\n' for i in range(100))
        )
    (root / 'analysis/analysis.edi').write_text(
        '_edi.schema_version 3\n_minimizer.max_iterations 1\n'
        f'_fitting_mode.type {mode}\n_sequential_fit.data_dir experiments/scan\n'
        '_sequential_fit.file_pattern *.xy\n'
    )
    return root, expected
