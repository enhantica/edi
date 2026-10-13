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
