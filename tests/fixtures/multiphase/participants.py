"""Authored active graphs; the oracle is Bragg's wavelength/cell dilation invariant.

Each tuple explicitly states edges, fixed wavelengths, fixed cubic cells and whether
EVERY active component has an anchor. No engine graph/resolver supplies the oracle.
"""

from pathlib import Path

from tests.fixtures.multiphase import support

# (bank -> [(phase, enabled)], fixed wavelengths, fixed cells, admissible)
GRAPHS = {
    'foreign-wavelength': ({'p': [('alpha', True)], 'q': [('beta', True)]}, {'p'}, set(), False),
    'foreign-cell': ({'p': [('alpha', True)], 'q': [('beta', True)]}, set(), {'alpha'}, False),
    'disabled-wavelength-bridge': (
        {'p': [('alpha', True)], 'q': [('alpha', False), ('beta', True)]},
        {'p'},
        set(),
        False,
    ),
    'disabled-cell-bridge': (
        {'p': [('alpha', True)], 'q': [('alpha', False), ('beta', True)]},
        set(),
        {'alpha'},
        False,
    ),
    'inactive-fixed-bank': ({'p': [('alpha', False)], 'q': [('beta', True)]}, {'p'}, set(), False),
    'unused-fixed-structure': (
        {'p': [('beta', True)], 'q': [('beta', True)]},
        set(),
        {'alpha'},
        False,
    ),
    'connected-wavelength': (
        {'p': [('alpha', True)], 'q': [('alpha', True), ('beta', True)]},
        {'p'},
        set(),
        True,
    ),
    'connected-cell': (
        {'p': [('alpha', True)], 'q': [('alpha', True), ('beta', True)]},
        set(),
        {'alpha'},
        True,
    ),
    'each-wavelength': ({'p': [('alpha', True)], 'q': [('beta', True)]}, {'p', 'q'}, set(), True),
    'each-cell': ({'p': [('alpha', True)], 'q': [('beta', True)]}, set(), {'alpha', 'beta'}, True),
    'connected-unanchored': (
        {'p': [('alpha', True)], 'q': [('alpha', True), ('beta', True)]},
        set(),
        set(),
        False,
    ),
    'disabled-free-phase': (
        {'p': [('alpha', True)], 'q': [('alpha', True), ('beta', False)]},
        {'p'},
        set(),
        True,
    ),
}


def write(
    root,
    edges,
    *,
    fixed_wavelengths=(),
    fixed_cells=('alpha', 'beta'),
    reverse=False,
    mode='joint',
):
    root = Path(root)
    support.write_project(root, biso=0)
    for phase in ('alpha', 'beta'):
        path = root / 'structures' / f'{phase}.edi'
        text = path.read_text()
        a = 2.2 if phase == 'alpha' else 3.3
        for field in ('a', 'b', 'c'):
            text = '\n'.join(
                f'_cell.length_{field} {a}' if line.startswith(f'_cell.length_{field} ') else line
                for line in text.split('\n')
            )
        text = text.replace('"P 1"', '"P m -3 m"')
        if phase not in fixed_cells:
            text = text.replace(f'_cell.length_a {a}', f'_cell.length_a {a}()')
        path.write_text(text)
    template = (root / 'experiments/pattern.edi').read_text()
    (root / 'experiments/pattern.edi').unlink()
    for index, (bank, rows) in enumerate(
        reversed(list(edges.items())) if reverse else edges.items()
    ):
        text = template[: template.index('loop_')].replace('data_pattern', f'data_{bank}')
        if bank not in fixed_wavelengths:
            text = text.replace(
                '_instrument.setup_wavelength 1.54', '_instrument.setup_wavelength 1.54()'
            )
        text += (
            'loop_\n_linked_structure.structure_id\n'
            '_linked_structure.scale\n_linked_structure.enabled\n'
        )
        text += ''.join(f'{phase} 1.125() {str(enabled).lower()}\n' for phase, enabled in rows)
        text += '\nloop_\n_data.two_theta\n_data.intensity_meas\n_data.intensity_meas_su\n'
        text += ''.join(f'{x / 2} 1 1\n' for x in range(30, 171))
        (root / 'experiments' / f'{index:02}-{bank}.edi').write_text(text)
    analysis = root / 'analysis/analysis.edi'
    analysis.write_text(
        '_edi.schema_version 3\n_minimizer.max_iterations 1\n'
        + (f'_fitting_mode.type {mode}\n' if mode else '')
    )
    return root


def graph(root, key, *, reverse=False):
    edges, wavelengths, cells, _ = GRAPHS[key]
    return write(root, edges, fixed_wavelengths=wavelengths, fixed_cells=cells, reverse=reverse)


def mixed(root, tof_text):
    root = write(
        root, {'p': [('alpha', True)], 'q': [('beta', True)]}, fixed_wavelengths=('p', 'q')
    )
    text = tof_text[tof_text.index('data_experiment') :].replace(
        'data_experiment', 'data_q\n_edi.schema_version 3'
    )
    text = text.replace('structure 401.4629', 'beta 1.125()')
    text += (
        '\nloop_\n_data.time_of_flight\n_data.intensity_meas\n'
        '_data.intensity_meas_su\n18000 1 1\n20000 1 1\n22000 1 1\n'
    )
    (root / 'experiments/01-q.edi').write_text(text)
    return root
