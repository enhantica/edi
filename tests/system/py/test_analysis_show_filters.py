"""Exercise Analysis view choices through real controls and their production proxy."""

import os
import re
import subprocess
import sys
from pathlib import Path

import edi
import pytest

ROOT = Path(__file__).resolve().parents[3]
CASES = [
    'test_defaults_and_grid',
    *(
        f'test_every_combination:{fixture}-{first}'
        for fixture in ('triclinic', 'cubic-constraint')
        for first in (0, 4, 8, 12)
    ),
    'test_view_model_intersections_and_reset',
    'test_labels_follow_context_and_free_override',
    'test_preferences_survive_a_fresh_engine_and_another_project',
    'test_view_choices_preserve_project_bytes_and_flags',
]


@pytest.mark.parametrize('case', CASES)
def test_analysis_reason_group_view(case):
    runner = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assert runner.is_file(), 'Analysis show-filter acceptance requires the built production host'
    result = subprocess.run(
        [
            str(runner),
            '-input',
            str(ROOT / 'tests/unit/app/tst_analysis_show_filters.qml'),
            'AnalysisShowFilters::' + case,
            '-o',
            '-,txt',
        ],
        cwd=ROOT,
        env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen', 'QT_QUICK_BACKEND': 'software'},
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0, (
        'Analysis Settings must select the requested rule groups and preserve user/project state: '
        + output
    )
    assert 'PASS' in output and '0 failed' in output, (
        'The selected show-filter actor completes its assertions in the real Qt host'
    )


def user_settings(root, enabled):
    store = root / 'EasyScience/EasyDiffraction.ini'
    store.parent.mkdir(parents=True)
    store.write_text(
        '[Analysis]\n'
        + ''.join(
            f'{key}={str(enabled).lower()}\n'
            for key in (
                'showNotMeasured',
                'showBySymmetry',
                'showByConstraint',
                'showFixedSettings',
            )
        )
    )
    return {**os.environ, 'XDG_CONFIG_HOME': str(root)}


def test_python_keeps_inputs_hidden_by_every_app_group(tmp_path, monkeypatch):
    environment = user_settings(tmp_path / 'user', False)
    monkeypatch.setenv('XDG_CONFIG_HOME', environment['XDG_CONFIG_HOME'])
    project = edi.Project.load(ROOT / 'tests/fixtures/fittability/projects/cubic-constrained')
    cell = project.structure.cell
    assert [
        getattr(cell, name).value
        for name in (
            'length_a',
            'length_b',
            'length_c',
            'angle_alpha',
            'angle_beta',
            'angle_gamma',
        )
    ] == [4.1, 4.1, 4.1, 90, 90, 90], (
        'Python retains every independent and symmetry-held cell input when app groups are off'
    )
    assert project.structure.atom_sites['Ni'].adp_iso.value == 0.41, (
        'Python retains the explicitly constrained input and its stored value '
        'independently of app visibility'
    )
    assert project.experiments['bank'].extinction.crystal_radius.value == 0.12, (
        'Python retains descriptor values when Setup values is hidden in the app'
    )


def test_cli_calculation_ignores_all_four_app_view_choices(tmp_path):
    results = []
    for enabled in (False, True):
        completed = subprocess.run(
            [
                sys.executable,
                '-m',
                'edi',
                'calc',
                str(ROOT / 'tests/fixtures/fittability/projects/powder'),
                '--dry',
            ],
            cwd=ROOT,
            env=user_settings(tmp_path / str(enabled), enabled),
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
        assert completed.returncode == 0, (
            'The real CLI calculates the complete input regardless of the app view groups: '
            + completed.stderr
        )
        assert len(re.findall(r'^elapsed_ms=[0-9.]+$', completed.stdout, re.MULTILINE)) == 1, (
            'CLI invariance normalizes exactly the declared calculation duration'
        )
        results.append(
            re.sub(
                r'^elapsed_ms=[0-9.]+$', 'elapsed_ms=<CLOCK>', completed.stdout, flags=re.MULTILINE
            )
        )
    assert results[0] == results[1] and 'n_points=6\n' in results[0], (
        'CLI view choices preserve every deterministic output field '
        'and all six authored observations'
    )
