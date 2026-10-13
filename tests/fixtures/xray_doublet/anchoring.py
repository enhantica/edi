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
