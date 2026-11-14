"""Saved-byte projections validate declared stop choices before historical comparison."""

import pytest

from tests.fixtures.metadata_transition.task_inputs import saved_analysis


@pytest.mark.parametrize(
    'choice', ['chi_square_change', 'shift_su', 'chi_square_change shift_su', '']
)
def test_saved_stop_set_projection_retains_every_other_byte(tmp_path, choice):
    folder = tmp_path / 'analysis'
    folder.mkdir()
    line = f'_minimizer.stop_rules "{choice}"\n'.encode()
    (folder / 'analysis.edi').write_bytes(line)
    remaining = b'_edi.schema_version 3\n_minimizer.max_iterations 1000\n'
    assert saved_analysis(line + remaining, tmp_path) == remaining


@pytest.mark.parametrize(
    'damage',
    ['changed', 'duplicate-save', 'duplicate-input', 'mixed', 'unknown', 'repeated-choice'],
)
def test_saved_stop_set_projection_refuses_changed_or_ambiguous_choices(tmp_path, damage):
    folder = tmp_path / 'analysis'
    folder.mkdir()
    line = b'_minimizer.stop_rules "chi_square_change"\n'
    source = line
    saved = line
    if damage == 'changed':
        saved = b'_minimizer.stop_rules "shift_su"\n'
    elif damage == 'duplicate-save':
        saved *= 2
    elif damage == 'duplicate-input':
        source *= 2
    elif damage == 'mixed':
        source += b'_minimizer.stop_rule chi_square\n'
    elif damage == 'unknown':
        source = saved = b'_minimizer.stop_rules "unknown"\n'
    elif damage == 'repeated-choice':
        source = saved = b'_minimizer.stop_rules "chi_square_change chi_square_change"\n'
    (folder / 'analysis.edi').write_bytes(source)
    with pytest.raises(AssertionError):
        saved_analysis(saved, tmp_path)
