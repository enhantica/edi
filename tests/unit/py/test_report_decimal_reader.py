"""Reader decimal scaling against correctly rounded decimal conversion."""

import json
import re
from pathlib import Path

import edi as engine
import pytest

ROOT = Path(__file__).resolve().parents[3]
REFERENCE = json.loads((ROOT / 'tests/fixtures/report_units/reference.json').read_text())


def structure(token):
    text = "data_decimal\n_edi.schema_version 3\n_space_group_name_H-M_alt 'P 1'\n"
    text += f'_cell_length_a {token}\n'
    text += '_cell_length_b 5\n_cell_length_c 6\n'
    text += '_cell_angle_alpha 90\n_cell_angle_beta 90\n_cell_angle_gamma 90\n'
    text += (
        'loop_\n_atom_site_label\n_atom_site_type_symbol\n'
        '_atom_site_fract_x\n_atom_site_fract_y\n_atom_site_fract_z\n'
        '_atom_site_occupancy\n_atom_site_B_iso_or_equiv\n'
        '_atom_site.wyckoff_letter\nNa1 Na 0.1 0.2 0.3 1 0.5 a\n'
    )
    return engine.StructureFactory.from_cif_str(text)


@pytest.mark.parametrize(('decimals', 'digits', 'expected'), REFERENCE['readers'])
def test_integer_su_decimal_scaling_keeps_representable_subnormals(decimals, digits, expected):
    token = '5.' + '0' * decimals + '(' + digits + ')'
    if expected is None and digits:
        with pytest.raises(ValueError, match=re.escape(token)) as error:
            structure(token)
        assert token in str(error.value), (
            'Underflow refusal must name the complete offending token'
        )
        return
    parameter = structure(token).cell.length_a
    wanted = None if expected is None else float(expected)
    assert parameter.uncertainty == wanted, (
        'Every integer bracket must equal correctly rounded digits times its last-decimal place, '
        'including nonzero subnormals, engaged zero and absent uncertainty'
    )
    assert parameter.free is True, 'An explicit bracket retains the free-parameter state'


@pytest.mark.parametrize(
    ('token', 'expected'), [('383.2(1.2)', 1.2), ('5(0)', 0.0), ('5()', None)]
)
def test_absolute_and_empty_brackets_keep_their_grammar(token, expected):
    parameter = structure(token).cell.length_a
    assert parameter.uncertainty == expected, (
        'Absolute decimal brackets and engaged-zero versus empty '
        'brackets must retain their meanings'
    )
