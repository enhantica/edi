""": cross-CLI byte parity excludes only validated elapsed fit seconds."""

from __future__ import annotations

from pathlib import Path

import pytest

from conftest import project_tree_parts

FIELDS = {
    'result_kind': 'deterministic',
    'success': 'true',
    'message': 'Done',
    'iterations': '1',
    'reduced_chi_square': '1.25',
    'objective_name': 'chi_square',
    'objective_value': '125',
    'n_data_points': '103',
    'n_parameters': '44',
    'n_free_parameters': '3',
    'degrees_of_freedom': '100',
    'covariance_available': 'true',
    'exit_reason': 'Done',
    'prof_wr_factor': '0.125',
    'profile_function': 'pseudo_voigt',
    'background_function': 'points',
}


def _tree(root: Path, timing: bytes) -> Path:
    (root / 'analysis').mkdir(parents=True)
    (root / 'project.edi').write_bytes(b'data_project\n')
    fields = ''.join(f'_fit_result.{key} {value}\n' for key, value in FIELDS.items()).encode()
    (root / 'analysis/analysis.edi').write_bytes(fields + timing)
    return root


def test_only_elapsed_seconds_are_normalized(tmp_path: Path) -> None:
    left = _tree(tmp_path / 'left', b'_fit_result.fitting_time 0.179\n')
    right = _tree(tmp_path / 'right', b'_fit_result.fitting_time 0.202\n')
    assert project_tree_parts(left) != project_tree_parts(right), (
        ' unnormalized saved trees must retain actual elapsed fit seconds'
    )
    assert project_tree_parts(left, normalize_fit_time=True) == project_tree_parts(
        right, normalize_fit_time=True
    ), ' cross-CLI parity masks only the independent fits elapsed seconds'
    expected = (
        (left / 'analysis/analysis.edi')
        .read_bytes()
        .replace(
            b'_fit_result.fitting_time 0.179\n',
            b'_fit_result.fitting_time <NORMALIZED-WALL-CLOCK>\n',
        )
    )
    assert (
        project_tree_parts(left, normalize_fit_time=True)[0]['analysis/analysis.edi'] == expected
    ), ' normalization preserves every other byte including fit tag and newline'
    path = right / 'analysis/analysis.edi'
    original = path.read_bytes()
    for line in (
        b'_fit_result.fitting_time 0.202  \n',
        b'_fit_result.fitting_time\t0.202\n',
        b'_fit_result.fitting_time 0.202\r\n',
    ):
        path.write_bytes(original.replace(b'_fit_result.fitting_time 0.202\n', line))
        assert project_tree_parts(left, normalize_fit_time=True) != project_tree_parts(
            right, normalize_fit_time=True
        ), ' elapsed-time normalization preserves separator, trailing spaces and newline'
    path.write_bytes(original)
    assert (left / 'analysis/analysis.edi').read_bytes().endswith(b'0.179\n'), (
        ' comparison normalization never rewrites the saved input'
    )


def test_every_other_result_field_and_path_stays_compared(tmp_path: Path) -> None:
    left = _tree(tmp_path / 'left', b'_fit_result.fitting_time 0.179\n')
    right = _tree(tmp_path / 'right', b'_fit_result.fitting_time 0.202\n')
    path = right / 'analysis/analysis.edi'
    original = path.read_bytes()
    for field, value in FIELDS.items():
        line = f'_fit_result.{field} {value}\n'.encode()
        for replacement in (b'', line + line, f'_fit_result.{field} changed\n'.encode()):
            path.write_bytes(original.replace(line, replacement))
            assert project_tree_parts(left, normalize_fit_time=True) != project_tree_parts(
                right, normalize_fit_time=True
            ), ' modifying any non-time result field breaks byte parity'
    path.write_bytes(original)
    extra = right / 'analysis/extra.edi'
    extra.write_bytes(b'data_extra\n')
    assert project_tree_parts(left, normalize_fit_time=True) != project_tree_parts(
        right, normalize_fit_time=True
    ), ' cross-CLI normalization keeps the complete saved path set compared'


@pytest.mark.parametrize(
    'timing',
    [b'', b'0', b'-1', b'nan', b'inf', b'?', b'0.1\n_fit_result.fitting_time 0.2'],
    ids=['missing', 'zero', 'negative', 'nan', 'infinite', 'invalid', 'duplicate'],
)
def test_missing_duplicate_or_invalid_elapsed_seconds_refuse(
    tmp_path: Path, timing: bytes
) -> None:
    line = b'_fit_result.fitting_time ' + timing + b'\n' if timing else b''
    root = _tree(tmp_path / 'project', line)
    with pytest.raises((AssertionError, ValueError)):
        project_tree_parts(root, normalize_fit_time=True)
