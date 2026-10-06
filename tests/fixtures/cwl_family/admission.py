"""Declared slot groups from the profile-family contract; no engine introspection."""

from tests.fixtures.cwl_family import profiles

GROUPS = {
    'lorentz': (('broad_lorentz_x', 'broad_lorentz_y'), (4, 5)),
    'mixing': (('mixing_eta_0', 'mixing_eta_1'), (2, 3)),
    'fcj': (('asym_fcj_1', 'asym_fcj_2'), (5,)),
    'beba': (
        ('asym_beba_a0', 'asym_beba_b0', 'asym_beba_a1', 'asym_beba_b1', 'asym_beba_limit'),
        (3,),
    ),
}
CASES = [
    (token, group)
    for i, token in enumerate(profiles.TOKENS)
    for group, (_, owners) in GROUPS.items()
    if i not in owners
]
DECLARATIONS = [(token, group, field) for token, group in CASES for field in GROUPS[group][0]]
FIELDS = tuple(field for fields, _ in GROUPS.values() for field in fields)


def owned_fields(token):
    index = profiles.TOKENS.index(token)
    return tuple(
        field for fields, owners in GROUPS.values() if index in owners for field in fields
    )


def classic(text):
    return (
        text
        .replace('_experiment_type.', '_easydiffraction_experiment_type.')
        .replace('_peak.', '_easydiffraction_peak.')
        .replace('_instrument.setup_wavelength', '_diffrn_radiation_wavelength.value')
        .replace('_instrument.calib_twotheta_offset', '_pd_calib.2theta_offset')
    )


def declaration(field, shape, *, classic_field=False):
    tag = ('_easydiffraction_peak.' if classic_field else '_peak.') + field
    if shape.endswith('scalar'):
        return f'\n{tag} .031\n'
    if shape.endswith('mixed'):
        return f'\nloop_\n{tag}\n_foreign_probe.label\n.031 observed\n'
    return f'\nloop_\n{tag}\n.031\n'
