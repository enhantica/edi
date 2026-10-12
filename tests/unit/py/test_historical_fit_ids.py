import pytest

from tests.fixtures.loop_parameter_ids.historical_fit_ids import historical_fit_ids

HEADER = (
    b'loop_\n_fit_parameter.id\n_fit_parameter.start_value\n'
    b'_fit_parameter.start_uncertainty\n_fit_parameter.start_tied\n'
)
OLD_ROWS = b'bank.background[0] 12.5 0.125 .\nbank.scale 3.25 0.25 .\n'
NEW_ROWS = b'bank.background.ramp 12.5 0.125 .\nbank.phase.scale 3.25 0.25 .\n'


@pytest.fixture
def source(tmp_path):
    (tmp_path / 'experiments').mkdir()
    (tmp_path / 'experiments/bank.edi').write_text(
        'data_bank\nloop_\n_background.id\n_background.position\n_background.intensity\n'
        'ramp 24.875 12.5\n\nloop_\n_linked_structure.structure_id\n'
        '_linked_structure.scale\nphase 3.25\n'
    )
    (tmp_path / 'analysis').mkdir()
    (tmp_path / 'analysis/analysis.edi').write_bytes(HEADER + OLD_ROWS)
    return tmp_path


def test_historical_fit_key_projection_preserves_every_other_byte(source):
    assert historical_fit_ids(source, HEADER + NEW_ROWS) == HEADER + OLD_ROWS, (
        'The declared input row ids must reverse only fit-state key cells'
    )


@pytest.mark.parametrize('damage', ['value', 'uncertainty', 'tied'])
def test_historical_fit_key_projection_cannot_hide_scientific_changes(source, damage):
    before, after = {
        'value': (b'12.5', b'12.625'),
        'uncertainty': (b'0.125', b'0.25'),
        'tied': (b' .', b' linked'),
    }[damage]
    damaged = HEADER + NEW_ROWS.replace(before, after, 1)
    assert historical_fit_ids(source, damaged) == (HEADER + OLD_ROWS).replace(before, after, 1), (
        'Every scientific mutation must survive projection so the retained hash can reject it'
    )
    assert historical_fit_ids(source, damaged) != HEADER + OLD_ROWS, (
        'A historical key projection must never regenerate a correct scientific value'
    )


@pytest.mark.parametrize('damage', ['wrong-id', 'missing', 'extra', 'row-order'])
def test_historical_fit_key_projection_requires_complete_ordered_identity(source, damage):
    first, second = NEW_ROWS.splitlines(keepends=True)
    damaged = {
        'wrong-id': NEW_ROWS.replace(b'ramp', b'unknown'),
        'missing': first,
        'extra': NEW_ROWS + second,
        'row-order': second + first,
    }[damage]
    with pytest.raises(AssertionError, match='Saved fit-state'):
        historical_fit_ids(source, HEADER + damaged)


def test_current_input_keeps_the_same_historical_fit_key_oracle(source):
    (source / 'analysis/analysis.edi').write_bytes(HEADER + NEW_ROWS)
    assert historical_fit_ids(source, HEADER + NEW_ROWS) == HEADER + OLD_ROWS, (
        'Migrating a committed input must retain every numeric byte of its old fit-key witness'
    )
