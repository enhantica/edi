"""Visible unit tests for lib/edi/verification.py ().

Correctness values obey the independent-reference rule: every expected number here is a
hand-computed closed form over small literal fixtures, never a value produced by the code under
test or by edi/crysta.
"""

import edi
import numpy as np
import pytest
from edi import verification as verify

# --- literal FullProf-format fixtures (hand-written, hand-computed expectations) -----------

IGOR_PRF = """IGOR
WAVES     TOF,       Iobs,   Icalc,  Diff
BEGIN
    1000.000       10.00       12.00       -2.00
    1005.000       20.00       21.00       -1.00
    1010.000       30.00       33.00       -3.00
END
"""

TABBED_PRF = """ Some banner line
 2Theta   Yobs    Ycal    Yobs-Ycal   Backg
 10.0     5.0     6.0     -1.0        1.0
 10.5     7.0     7.5     -0.5        1.0
 (  1  1  1 )  reflection marker row 111 222 333 444
 11.0     9.0     8.0      1.0        1.0
"""

TWO_COLUMN_BAC = """!  Background of: case
 1000.0   2.0
 1010.0   4.0
"""

# Header + flat-array layout: min=1000, step=5, max=1010 -> grid 1000,1005,1010.
ARRAY_BAC = """ 1000.0  5.0  1010.0  Background of: case
 2.0 3.0
 4.0
"""


def _write_project(tmp_path, files):
    root = tmp_path / 'knowledge' / 'verification' / 'fullprof' / 'case'
    root.mkdir(parents=True)
    for name, text in files.items():
        (root / name).write_text(text, encoding='utf-8')
    return tmp_path


def test_igor_prf_parses_x_and_icalc_columns(tmp_path, monkeypatch):
    monkeypatch.chdir(_write_project(tmp_path, {'case.prf': IGOR_PRF, 'case.bac': TWO_COLUMN_BAC}))
    # zero_shift 0: background interpolates from (1000, 2) / (1010, 4) -> 2, 3, 4 on the grid.
    x, y = verify.load_fullprof_calc_profile('case', 'case.prf', 'case.bac', 0.0)
    assert x.tolist() == [1000.0, 1005.0, 1010.0]
    assert y.tolist() == [10.0, 18.0, 29.0]  # Icalc (12, 21, 33) minus background (2, 3, 4)


def test_bac_zero_shift_realigns_axis_before_subtraction(tmp_path, monkeypatch):
    monkeypatch.chdir(_write_project(tmp_path, {'case.prf': IGOR_PRF, 'case.bac': TWO_COLUMN_BAC}))
    # zero_shift +5 moves the .bac grid to 1005/1015: interpolated bg = 2, 2, 3 on the profile
    # grid (left edge clamps).
    _, y = verify.load_fullprof_calc_profile('case', 'case.prf', 'case.bac', 5.0)
    assert y.tolist() == [10.0, 19.0, 30.0]


def test_array_layout_bac_reconstructs_grid_from_header(tmp_path, monkeypatch):
    monkeypatch.chdir(_write_project(tmp_path, {'case.prf': IGOR_PRF, 'case.bac': ARRAY_BAC}))
    # Flat-array values 2,3,4 on the reconstructed grid 1000,1005,1010 (step from the header).
    _, y = verify.load_fullprof_calc_profile('case', 'case.prf', 'case.bac', 0.0)
    assert y.tolist() == [10.0, 18.0, 29.0]


def test_tabbed_prf_skips_reflection_marker_rows(tmp_path, monkeypatch):
    monkeypatch.chdir(
        _write_project(tmp_path, {'case.prf': TABBED_PRF, 'case.bac': TWO_COLUMN_BAC})
    )
    x, y = verify.load_fullprof_calc_profile('case', 'case.prf', 'case.bac', 0.0)
    assert x.tolist() == [10.0, 10.5, 11.0]
    # Ycal column (6.0, 7.5, 8.0) minus interpolated bg (clamped left edge of the 1000-grid: 2.0).
    assert y.tolist() == [4.0, 5.5, 6.0]


def test_empty_prf_fails_closed(tmp_path, monkeypatch):
    monkeypatch.chdir(
        _write_project(tmp_path, {'case.prf': 'IGOR\nBEGIN\nEND\n', 'case.bac': TWO_COLUMN_BAC})
    )
    with pytest.raises(ValueError, match='no calculated-profile data rows'):
        verify.load_fullprof_calc_profile('case', 'case.prf', 'case.bac', 0.0)


def test_fullprof_version_reads_the_sum_banner(tmp_path, monkeypatch):
    banner = ' **** PROGRAM FullProf.2k (Version 8.40 - Feb2026-ILL JRC) ****\n'
    monkeypatch.chdir(_write_project(tmp_path, {'case.sum': banner}))
    assert verify.fullprof_version('case', 'case.sum') == '8.40'
    assert verify.fullprof_label('case', 'case.sum') == 'FullProf 8.40'


def test_fullprof_version_fails_closed_without_banner(tmp_path, monkeypatch):
    monkeypatch.chdir(_write_project(tmp_path, {'case.sum': 'no banner here\n'}))
    with pytest.raises(ValueError, match='no FullProf version banner'):
        verify.fullprof_version('case', 'case.sum')


# --- closeness metrics: hand-computed closed forms ------------------------------------------


def test_identical_patterns_score_perfectly():
    ref = np.array([1.0, 2.0, 3.0])
    m = verify.pattern_closeness(ref, ref.copy())
    assert m.profile_difference_percent == 0.0
    assert m.max_deviation_percent == 0.0
    assert m.intensity_ratio == 1.0
    assert m.correlation == pytest.approx(1.0)


def test_doubled_candidate_metrics_match_closed_forms():
    ref = np.array([1.0, 2.0, 3.0])
    m = verify.pattern_closeness(ref, 2.0 * ref)
    # diff = -ref: RMS(diff)/RMS(ref) = 1 -> 100 %; max|diff|/max|ref| = 3/3 -> 100 %.
    assert m.profile_difference_percent == pytest.approx(100.0)
    assert m.max_deviation_percent == pytest.approx(100.0)
    assert m.intensity_ratio == pytest.approx(2.0)
    assert m.correlation == pytest.approx(1.0)


def test_length_mismatch_fails_closed():
    with pytest.raises(ValueError, match='same length'):
        verify.pattern_closeness(np.ones(3), np.ones(4))


def test_default_tolerances_match_the_reference_values():
    t = verify.AgreementTolerances()
    assert t.max_profile_difference_percent == 2.5
    assert t.max_deviation_percent == 6.0
    assert (t.min_intensity_ratio, t.max_intensity_ratio) == (0.99, 1.01)
    assert t.min_correlation == 0.999


# --- assert_patterns_agree: the two-sided contract -------------------------------------------

AGREEING = ('agreeing', np.array([1.0, 2.0, 3.0]), np.array([1.0, 2.0, 3.0]))
DISAGREEING = ('disagreeing', np.array([1.0, 2.0, 3.0]), np.array([2.0, 4.0, 6.0]))


def test_agreeing_pair_passes_the_default_gate(capsys):
    assert verify.assert_patterns_agree([AGREEING]) is True
    out = capsys.readouterr().out
    assert 'Profile diff (%)' in out
    assert '❌' not in out


def test_disagreeing_pair_fails_the_default_gate():
    with pytest.raises(AssertionError, match='disagreeing'):
        verify.assert_patterns_agree([DISAGREEING])


def test_known_discrepancy_requires_a_reason():
    with pytest.raises(ValueError, match='reason'):
        verify.assert_patterns_agree([DISAGREEING], known_discrepancy=True)


def test_known_discrepancy_passes_while_the_disagreement_persists(capsys):
    assert (
        verify.assert_patterns_agree(
            [DISAGREEING], known_discrepancy=True, reason='documented gap'
        )
        is True
    )
    assert 'documented gap' in capsys.readouterr().out


def test_known_discrepancy_fails_when_a_comparison_starts_agreeing():
    with pytest.raises(AssertionError, match='now agree within tolerance'):
        verify.assert_patterns_agree([AGREEING], known_discrepancy=True, reason='documented gap')


def test_closeness_annotation_marks_failures_in_red():
    metrics = verify.pattern_closeness(np.array([1.0, 2.0, 3.0]), np.array([2.0, 4.0, 6.0]))
    lines = verify.closeness_annotation(metrics)
    assert len(lines) == 4
    assert any('❌' in line and 'rgb(214, 39, 40)' in line for line in lines)
    assert any(line.startswith('✅ Shape correlation') for line in lines)


# --- experiment seeding and restriction over the real binding --------------------------------


def _tof_experiment():
    return edi.ExperimentFactory.from_dict({
        'instrument': {
            'calib_d_to_tof_offset': 0.0,
            'calib_d_to_tof_linear': 7000.0,
            'calib_d_to_tof_quadratic': 0.0,
        },
        'linked_structure': {'scale': 1.0},
    })


def test_set_reference_as_measured_seeds_grid_observed_and_unit_sigma():
    experiment = _tof_experiment()
    verify.set_reference_as_measured(experiment, [1.0, 2.0, 3.0], [4.0, 5.0, 6.0])
    assert list(experiment.data.axis()) == [1.0, 2.0, 3.0]
    assert list(experiment.data.intensity_meas) == [4.0, 5.0, 6.0]
    assert list(experiment.data.intensity_meas_su) == [1.0, 1.0, 1.0]


def test_restrict_to_included_masks_excluded_regions():
    experiment = _tof_experiment()
    verify.set_reference_as_measured(
        experiment, [1000.0, 2000.0, 3000.0, 4000.0], [1.0, 2.0, 3.0, 4.0]
    )
    experiment.excluded_regions = [(0.0, 1500.0), (3500.0, 9000.0)]
    restricted = verify.restrict_to_included(experiment, np.array([1.0, 2.0, 3.0, 4.0]))
    assert restricted.tolist() == [2.0, 3.0]
    # Already-restricted arrays and the no-exclusion case pass through unchanged.
    assert verify.restrict_to_included(experiment, restricted).tolist() == [2.0, 3.0]
    experiment.excluded_regions = []
    full = verify.restrict_to_included(experiment, np.array([1.0, 2.0, 3.0, 4.0]))
    assert full.tolist() == [1.0, 2.0, 3.0, 4.0]


# --- candidate labels -------------------------------------------------------------------------


def test_engine_label_carries_edi_and_crysta_identities():
    label = verify.engine_label('crysta')
    assert label.startswith('edi ')
    assert '(crysta ' in label
    noted = verify.engine_label('crysta', note='refined')
    assert noted.endswith(', refined)')


def test_engine_label_rejects_unknown_engines():
    with pytest.raises(ValueError, match='Unknown engine'):
        verify.engine_label('cryspy')
