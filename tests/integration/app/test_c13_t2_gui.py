"""Exercise the committed C13-T2 owner decisions through the production Qt host."""

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
BOUNDARIES = (
    'test_separate_adp_table_and_isotropic_controls',
    'test_each_declared_adp_type_has_the_required_editor_state',
    'test_atom_filter_recovers_from_red_and_commits_element',
    'test_space_group_name_and_number_choose_new_default',
    'test_invalid_number_is_red_and_unapplied',
    'test_minimizer_is_two_rows_of_two',
    'test_atom_icon_colours_follow_structure_palette_in_both_tables',
    'test_adp_view_uses_probability_in_atom_scale_position',
)


@pytest.fixture(scope='module')
def gui_run():
    binary = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assert binary.is_file(), 'C13-T2 GUI: app-build must supply the real Qt test runner'
    return subprocess.run(
        [str(binary), '-input', str(ROOT / 'tests/unit/app/tst_c13_t2_gui.qml'), '-o', '-,txt'],
        env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen', 'QT_QUICK_BACKEND': 'software'},
        capture_output=True,
        text=True,
        timeout=90,
        check=False,
    )


def test_gui_owner_decisions_pass_in_the_production_host(gui_run):
    output = gui_run.stdout + gui_run.stderr
    assert gui_run.returncode == 0, 'C13-T2 GUI: every owner boundary must pass: ' + output


@pytest.mark.parametrize('boundary', BOUNDARIES)
def test_each_gui_boundary_actually_executes(gui_run, boundary):
    output = gui_run.stdout + gui_run.stderr
    assert f'PASS   : edi_app::C13T2Gui::{boundary}()' in output, (
        'C13-T2 GUI: each owner decision must execute in the real host: ' + boundary + output
    )
