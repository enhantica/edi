"The historical byte adaptation admits only the independently derived uncertainty spellings."

import pytest

from tests.fixtures.saved_spelling.reference import decode, historical_spelling, spelling
from tests.system.py.test_c13_t12_compatibility import comparison_records, delimiter_only


@pytest.mark.parametrize(
    ('value', 'su', 'expected'),
    [
        ('1.54249', '0.01532', '1.542(16)'),
        ('2.16352', '0.00481', '2.164(5)'),
        ('0.4637', '0.0196', '0.46(2)'),
        ('54912', '1234', '54900(1300)'),
        ('0', '0.0123', '0.000(13)'),
        ('-0.02134', '0.00151', '-0.0213(16)'),
        ('0', '1', '0.0(10)'),
        ('3.0', '0', '3(0)'),
        ('1.5', '0', '1.5(0)'),
        ('3.88', '0.000429614028128419', '3.8800(5)'),
    ],
)
def test_saved_spelling_matches_independent_iucr_examples(value, su, expected):
    assert spelling(value, su) == expected, (
        'The expected saved token follows the stated IUCr ceiling and value rounding'
    )


def test_saved_spelling_preserves_fixed_values_literals_comments_and_other_files():
    old = (
        b'_cell.length_a 0.23091065335098124(0.00783695876908294987)\n'
        b'_cell.length_b 3.141592653589793\n_cell.length_c 1.5()\n_cell.angle_gamma 1.5(0)\n'
        b'_unowned.text "1.54249(0.01532)"\n# keep 1.54249(0.01532)\n'
    )
    expected = (
        b'_cell.length_a 0.231(8)\n'
        b'_cell.length_b 3.141592653589793\n_cell.length_c 1.5()\n_cell.angle_gamma 1.5(0)\n'
        b'_unowned.text "1.54249(0.01532)"\n# keep 1.54249(0.01532)\n'
    )
    assert historical_spelling('structures/sample.edi', old) == expected, (
        'Only an actual positive-uncertainty model token changes spelling'
    )
    assert historical_spelling('analysis/analysis.edi', old) == old, (
        'The saved-spelling adaptation leaves analysis bytes and all other files intact'
    )
    assert decode('0.290(3)') == (0.29, 0.003), (
        'The independent decoder restores integer-bracket uncertainty at its stated decimal place'
    )


@pytest.mark.parametrize(
    'change',
    ['missing-rule', 'wrong-rule', 'duplicate-rule', 'comment', 'fixed-value', 'uncertainty'],
)
def test_historical_comparison_still_rejects_unapproved_byte_changes(tmp_path, change):
    old = b'_metadata.name sample\n\n# preserved\n'
    expected = historical_spelling('project.edi', old)
    mutations = {
        'missing-rule': old,
        'wrong-rule': expected.replace(b'iucr_19', b'iucr_99'),
        'duplicate-rule': expected + b'_su_format.rule iucr_19\n',
        'comment': expected.replace(b'# preserved', b'# changed'),
        'fixed-value': expected + b'_unowned.value 7.25\n',
        'uncertainty': expected + b'_metadata.name 1.542(17)\n',
    }
    a, b = comparison_records('project.edi', old, mutations[change], tmp_path)
    assert a != b, 'The actual historical comparison retains every unapproved byte change'
    assert not delimiter_only(a.decode(), b.decode()), (
        'An unapproved metadata or rule change is never an identity-delimiter change'
    )


@pytest.mark.parametrize('change', ['value', 'su', 'fixed'])
def test_model_comparison_rejects_changes_beyond_the_derived_spelling(tmp_path, change):
    old = b'_cell.length_a 1.54249(0.01532)\n_cell.length_b 3.141592653589793\n'
    (tmp_path / 'structures').mkdir()
    (tmp_path / 'structures/sample.edi').write_bytes(old)
    expected = historical_spelling('structures/sample.edi', old)
    candidate = expected.replace(
        *{
            'value': (b'1.542(16)', b'1.543(16)'),
            'su': (b'1.542(16)', b'1.542(17)'),
            'fixed': (b'3.141592653589793', b'3.14'),
        }[change]
    )
    a, b = comparison_records('structures/sample.edi', old, candidate, tmp_path)
    assert a != b, (
        'The actual historical comparison rejects a changed value, uncertainty or fixed token'
    )
    assert not delimiter_only(a.decode(), b.decode()), (
        'A changed physical value is never an admitted identity-delimiter change'
    )
