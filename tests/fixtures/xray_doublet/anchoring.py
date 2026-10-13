"""Bragg-law anchor truth table authored independently of fit admission code."""

from tests.fixtures.multiphase import participants

# Each bank joins its enabled phases; an unrelated or disabled edge carries no anchor.
GRAPHS = {
    'single': ('single', {'p': [('alpha', True)]}, ('p',), True),
    'shared-first': ('joint', {'p': [('alpha', True)], 'q': [('alpha', True)]}, ('p',), True),
    'shared-second': ('joint', {'p': [('alpha', True)], 'q': [('alpha', True)]}, ('q',), True),
    'multiphase': ('single', {'p': [('alpha', True), ('beta', True)]}, ('p',), True),
    'remote-connected': (
        'joint',
        {'p': [('alpha', True)], 'q': [('alpha', True), ('beta', True)]},
        ('q',),
        True,
    ),
    'foreign-component': ('joint', {'p': [('alpha', True)], 'q': [('beta', True)]}, ('q',), False),
    'each-component': ('joint', {'p': [('alpha', True)], 'q': [('beta', True)]}, ('p', 'q'), True),
    'disabled-bridge': (
        'joint',
        {'p': [('alpha', True)], 'q': [('alpha', False), ('beta', True)]},
        ('q',),
        False,
    ),
    'inactive-bank': ('joint', {'p': [('alpha', True)], 'q': [('alpha', False)]}, ('q',), False),
}


def write(root, key, state, *, reverse=False):
    mode, edges, anchors, admitted = GRAPHS[key]
    participants.write(root, edges, fixed_cells=(), mode=mode, reverse=reverse)
    for path in (root / 'experiments').glob('*.edi'):
        text = path.read_text().replace('radiation_probe neutron', 'radiation_probe xray')
        text = '\n'.join(
            line for line in text.splitlines() if not line.startswith('_scattering_source.')
        )
        bank = text.splitlines()[0].removeprefix('data_')
        text += (
            '\n_scattering_source.xray_form_factor it1992\n'
            '_scattering_source.xray_dispersion none\n'
        )
        if bank in anchors:
            text += (
                '_instrument.setup_wavelength_2 1.6732'
                + ('()' if state == 'free-second' else '')
                + '\n'
            )
            text += (
                '_instrument.setup_wavelength_2_to_1_ratio '
                + ('0' if state == 'inactive' else '0.375')
                + '\n'
            )
        path.write_text(text)
    return mode, admitted and state == 'fixed-second'


RELATION_GRAPHS = ('single', 'shared-second', 'remote-connected')
RELATIONS = (
    'moving-second',
    'moving-first',
    'constant-ratio',
    'disabled-ratio',
    'zero-ratio',
    'constant-second',
    'fixed-input-second',
    'constant-first',
    'fixed-input-first',
)


def write_relation(root, key, relation, *, reverse=False):
    first_target = relation in {'moving-first', 'constant-first', 'fixed-input-first'}
    state = (
        'free-second'
        if first_target
        else 'inactive'
        if relation in {'constant-ratio', 'disabled-ratio'}
        else 'fixed-second'
    )
    write(root, key, state, reverse=reverse)
    if first_target:
        for path in (root / 'experiments').glob('*.edi'):
            text = path.read_text()
            if text.splitlines()[0].removeprefix('data_') in GRAPHS[key][2]:
                path.write_text(
                    text.replace(
                        '_instrument.setup_wavelength 1.54()', '_instrument.setup_wavelength 1.54'
                    )
                )
    aliases, constraints = [], []
    if relation.startswith('fixed-input'):
        aliases.append('fixed_adp alpha.atom_site.X.adp_iso')
    for bank in GRAPHS[key][2]:
        aliases.extend([
            f'{bank}_line1 {bank}.instrument.setup_wavelength',
            f'{bank}_line2 {bank}.instrument.setup_wavelength_2',
            f'{bank}_ratio {bank}.instrument.setup_wavelength_2_to_1_ratio',
        ])
        expressions = {
            'moving-second': f'{bank}_line2 = 1.05 * {bank}_line1',
            'moving-first': f'{bank}_line1 = {bank}_line2 / 1.05',
            'constant-ratio': f'{bank}_ratio = 0.375',
            'disabled-ratio': f'{bank}_ratio = 0.375',
            'zero-ratio': f'{bank}_ratio = 0',
            'constant-second': f'{bank}_line2 = 1.6732',
            'fixed-input-second': f'{bank}_line2 = 1.6732 + 0.01 * fixed_adp',
            'constant-first': f'{bank}_line1 = 1.54',
            'fixed-input-first': f'{bank}_line1 = 1.54 + 0.01 * fixed_adp',
        }
        constraints.append(
            f'{bank}_relation "{expressions[relation]}" '
            + ('false' if relation == 'disabled-ratio' else 'true')
        )
    analysis = root / 'analysis/analysis.edi'
    analysis.write_text(
        analysis.read_text() + '\nloop_\n_alias.id\n'
        '_alias.parameter_unique_name\n'
        + '\n'.join(aliases)
        + '\n\nloop_\n_constraint.id\n_constraint.expression\n'
        '_constraint.enabled\n' + '\n'.join(constraints) + '\n'
    )
    return GRAPHS[key][0]


def relation_geometry(relation):
    line1, line2 = 1.54, 1.6732
    if relation == 'moving-second':
        line2 = 1.05 * line1
    if relation == 'moving-first':
        line1 = line2 / 1.05
    # d lambda / d t along the homogeneous free-master dilation; fixed inputs have zero slope.
    slopes = (
        (0.0, line2)
        if relation in {'constant-first', 'fixed-input-first'}
        else (line1, line2)
        if relation.startswith('moving')
        else (line1, 0.0)
    )
    ratio = 0.0 if relation in {'disabled-ratio', 'zero-ratio'} else 0.375
    return (line1, line2), slopes, ratio


ZERO_BOUNDARY_RELATIONS = (
    'wavelength-driven',
    'cell-driven',
    'chained-wavelength',
    'constant-zero',
    'stationary-wavelength',
    'stationary-cell',
    'disabled-wavelength',
    'free-ratio',
    'compensated-wavelength',
    'compensated-cell',
)
IDLE_SOURCES = (
    'unlinked',
    'disabled',
    'active-connected',
    'active-foreign',
    'active-fixed-bank',
    'unlinked-fixed',
)


def append_relations(root, aliases, constraints):
    path = root / 'analysis/analysis.edi'
    path.write_text(
        path.read_text()
        + '\nloop_\n_alias.id\n_alias.parameter_unique_name\n'
        + '\n'.join(aliases)
        + '\n\nloop_\n_constraint.id\n_constraint.expression\n_constraint.enabled\n'
        + '\n'.join(constraints)
        + '\n'
    )


def write_zero_boundary(root, key, relation, *, reverse=False):
    mode, _ = write(root, key, 'inactive', reverse=reverse)
    aliases = ['active_a alpha.cell.length_a']
    constraints = []
    for bank in GRAPHS[key][2]:
        aliases.extend([
            f'{bank}_line1 {bank}.instrument.setup_wavelength',
            f'{bank}_line2 {bank}.instrument.setup_wavelength_2',
            f'{bank}_ratio {bank}.instrument.setup_wavelength_2_to_1_ratio',
        ])
        source = f'{bank}_line1 - 1.54'
        if relation in {'cell-driven', 'stationary-cell', 'compensated-cell'}:
            source = 'active_a - 2.2'
        if relation == 'chained-wavelength':
            constraints.append(f'{bank}_line_relation "{bank}_line2 = 1.6732 + ({source})" true')
            source = f'{bank}_line2 - 1.6732'
        expression = f'0.25 * ({source})'
        if relation == 'constant-zero':
            expression = '0'
        elif relation.startswith('stationary'):
            expression = f'0.25 * ({source}) * ({source})'
        elif relation.startswith('compensated'):
            expression += f' - ({bank}_line2 - 1.6732)'
        if relation != 'free-ratio':
            constraints.append(
                f'{bank}_ratio_relation "{bank}_ratio = {expression}" '
                + ('false' if relation == 'disabled-wavelength' else 'true')
            )
        set_boundary_independent(root, bank, relation)
    append_relations(root, aliases, constraints)
    return mode


def set_boundary_independent(root, bank, relation):
    for path in (root / 'experiments').glob('*.edi'):
        text = path.read_text()
        if text.splitlines()[0] != f'data_{bank}':
            continue
        if relation.startswith('compensated'):
            text = text.replace(
                '_instrument.setup_wavelength_2 1.6732',
                '_instrument.setup_wavelength_2 1.6732()',
            )
        elif relation == 'free-ratio':
            text = text.replace(
                '_instrument.setup_wavelength_2_to_1_ratio 0',
                '_instrument.setup_wavelength_2_to_1_ratio 0()',
            )
        path.write_text(text)


def zero_boundary_slopes(relation):
    master_slope = 2.2 if relation.endswith('cell') or relation == 'cell-driven' else 1.54
    ratio_slope = 0.25 * master_slope
    if relation not in {'wavelength-driven', 'cell-driven', 'chained-wavelength'}:
        ratio_slope = 0.0
    compensator_slope = 0.25 * master_slope if relation.startswith('compensated') else 0.0
    return ratio_slope, compensator_slope


def write_idle_source(root, key, source, *, reverse=False):
    mode, _ = write(root, key, 'fixed-second', reverse=reverse)
    gamma = (root / 'structures/beta.edi').read_text().replace('data_beta', 'data_gamma')
    if source == 'unlinked-fixed':
        gamma = gamma.replace('_cell.length_a 3.3()', '_cell.length_a 3.3')
    (root / 'structures/gamma.edi').write_text(gamma)
    anchor_bank = GRAPHS[key][2][0]
    if source in {'disabled', 'active-connected'}:
        for path in (root / 'experiments').glob('*.edi'):
            text = path.read_text()
            if text.splitlines()[0] == f'data_{anchor_bank}':
                text = text.replace(
                    '\n\nloop_\n_data.two_theta',
                    '\ngamma 1.125() '
                    + ('true' if source == 'active-connected' else 'false')
                    + '\n\nloop_\n_data.two_theta',
                )
                path.write_text(text)
    elif source in {'active-foreign', 'active-fixed-bank'}:
        first = next((root / 'experiments').glob('*.edi'))
        text = first.read_text()
        prefix = text[: text.index('loop_')]
        prefix = prefix.replace(prefix.splitlines()[0], 'data_r')
        prefix = (
            '\n'.join(
                line
                for line in prefix.splitlines()
                if not line.startswith((
                    '_instrument.setup_wavelength_2 ',
                    '_instrument.setup_wavelength_2_to_1_ratio ',
                ))
            )
            + '\n'
        )
        if source == 'active-fixed-bank':
            prefix = prefix.replace(
                '_instrument.setup_wavelength 1.54()', '_instrument.setup_wavelength 1.54'
            )
        suffix = (
            '\n'.join(
                line
                for line in text[text.index('loop_\n_data.two_theta') :].splitlines()
                if not line.startswith((
                    '_instrument.setup_wavelength_2 ',
                    '_instrument.setup_wavelength_2_to_1_ratio ',
                ))
            )
            + '\n'
        )
        (root / 'experiments/02-r.edi').write_text(
            prefix + 'loop_\n_linked_structure.structure_id\n_linked_structure.scale\n'
            '_linked_structure.enabled\ngamma 1.125() true\n\n' + suffix
        )
        mode = 'joint'
        path = root / 'analysis/analysis.edi'
        path.write_text(
            path.read_text().replace('_fitting_mode.type single', '_fitting_mode.type joint')
        )
    append_relations(
        root,
        [
            'source_a gamma.cell.length_a',
            f'anchor_line2 {anchor_bank}.instrument.setup_wavelength_2',
        ],
        ['source_relation "anchor_line2 = 0.5 * source_a" true'],
    )
    return mode


def idle_source_is_solved(source):
    return source in {'active-connected', 'active-foreign', 'active-fixed-bank'}


def idle_source_admits(source):
    return not idle_source_is_solved(source) or source == 'active-fixed-bank'
