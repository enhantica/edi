"""Exercise project-owned appearance with real controls and the actual 3D renderer."""

import os
from pathlib import Path

import pytest

from tests.fixtures.fast_chart_redraws.rendering import capture

ROOT = Path(__file__).resolve().parents[3]
CASES = [
    'test_existing_toolbar_switches_have_the_same_full_extra_settings',
    'test_atom_view_toolbar_and_extra_share_saved_state',
    'test_polyhedra_toolbar_and_extra_change_actual_geometry_visibility',
    'test_polyhedra_colour_and_opacity_affect_the_actual_3d_render',
    'test_polyhedra_settings_survive_reload_and_do_not_leak_to_another_project',
]


@pytest.mark.parametrize('case', CASES)
def test_real_structure_appearance_completion(case):
    binary = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assert binary.is_file(), 'Structure appearance acceptance requires the current native Qt host'
    status, output = capture([
        binary,
        '-input',
        ROOT / 'tests/unit/app/tst_structure_appearance_completion.qml',
        'StructureAppearanceCompletion::' + case,
    ])
    assert 'Could not find the following test functions' not in output, (
        'The requested appearance function exists before product behavior is judged'
    )
    assert status == 0, (
        'The real Structure appearance satisfies the persistence and rendering contract: ' + output
    )
    assert case + '()' in output and '0 failed' in output, (
        'The requested appearance function reaches its actual native assertions'
    )
    assert 'SKIP' not in output, 'Every actual appearance contract executes with real graphics'
