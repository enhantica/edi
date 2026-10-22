"""Observe single-crystal values in the production chart and rendered table."""

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
PROJECTS = (
    'sc-neut-cwl_pr2nio4_basic',
    'sc-neut-cwl_tbti_basic',
    'sc-neut-cwl_tbti_anisotropic-adp',
    'sc-neut-cwl_tbti_isotropic-extinction',
    'sc-neut-tof_taurine_basic',
)


@pytest.fixture(scope='module')
def app_result():
    runner = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assert runner.is_file(), 'The single-crystal app gate requires the real production Qt runner'
    app_env = ROOT / '.pixi/envs/app'
    environment = {
        **os.environ,
        'CONDA_PREFIX': str(app_env),
        'PATH': str(app_env / 'bin') + os.pathsep + os.environ.get('PATH', ''),
        'EDI_ACCEPTANCE_REFERENCE': str(ROOT / 'tests/fixtures/single_crystal'),
    }
    environment.pop('QT_QUICK_BACKEND', None)
    environment.pop('QT_QPA_PLATFORM', None)
    return subprocess.run(
        [
            'bash',
            '-c',
            (
                'source tools/ci/app-platform.sh; '
                'app_capture_platform single-crystal-acceptance || exit 1; "$@"'
            ),
            'single-crystal-acceptance',
            str(runner),
            '-input',
            str(ROOT / 'tests/unit/app/tst_single_crystal_views.qml'),
            '-o',
            '-,txt',
        ],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=300,
    )


@pytest.mark.parametrize('project', PROJECTS)
@pytest.mark.parametrize('theme', ['light', 'dark'])
@pytest.mark.parametrize('page', ['experiment', 'analysis'])
def test_real_single_crystal_chart_table_and_sidebar(app_result, project, theme, page):
    output = app_result.stdout + app_result.stderr
    assert app_result.returncode >= 0 and all(
        f'PASS   : edi_app::SingleCrystalViews::{phase}()' in output
        for phase in ['initTestCase', 'cleanupTestCase']
    ), 'Every real app case and cleanup must complete successfully: ' + output
    assert (
        'PASS   : edi_app::SingleCrystalViews::test_chart_table_and_sidebar'
        f'({project}-{theme}-{page})' in output
    ), (
        'Each project must execute chart, rendered table and sidebar checks in both themes: '
        + output
    )


@pytest.mark.parametrize('theme', ['light', 'dark'])
@pytest.mark.parametrize('page', ['experiment', 'analysis'])
def test_real_powder_view_retains_the_regression_pin(app_result, theme, page):
    output = app_result.stdout + app_result.stderr
    assert app_result.returncode >= 0 and all(
        f'PASS   : edi_app::SingleCrystalViews::{phase}()' in output
        for phase in ['initTestCase', 'cleanupTestCase']
    ), 'Every real app case and cleanup must complete successfully: ' + output
    assert (
        'PASS   : edi_app::SingleCrystalViews::test_powder_view_unchanged'
        f'({theme}-{page})' in output
    ), 'The real powder chart and sidebar must remain unchanged in each theme: ' + output


@pytest.mark.parametrize('theme', ['light', 'dark'])
@pytest.mark.parametrize('page', ['experiment', 'analysis'])
@pytest.mark.parametrize(
    'case',
    [
        'toolbar_quantity_and_memory',
        'reflection_hover_and_shared_toggle',
    ],
)
def test_real_chart_toolbar_conversion_memory_and_hover(app_result, theme, page, case):
    output = app_result.stdout + app_result.stderr
    assert app_result.returncode >= 0 and all(
        f'PASS   : edi_app::SingleCrystalViews::{phase}()' in output
        for phase in ['initTestCase', 'cleanupTestCase']
    ), 'The single-crystal chart host must complete without a crash: ' + output
    assert f'PASS   : edi_app::SingleCrystalViews::test_{case}({theme}-{page})' in output, (
        'The real toolbar and pointer must execute the selected quantity or tooltip witness: '
        + output
    )


@pytest.mark.parametrize('theme', ['light', 'dark'])
@pytest.mark.parametrize(
    'case',
    [
        'calculation_after_edits_and_extinction_labels',
        'fit_lowers_objective_and_reports_single_crystal_factors',
        'result_structure_names_are_complete',
    ],
)
def test_real_single_crystal_calculation_fit_and_results(app_result, theme, case):
    output = app_result.stdout + app_result.stderr
    assert app_result.returncode >= 0 and all(
        f'PASS   : edi_app::SingleCrystalViews::{phase}()' in output
        for phase in ['initTestCase', 'cleanupTestCase']
    ), 'The single-crystal fit host must complete without a crash: ' + output
    assert f'PASS   : edi_app::SingleCrystalViews::test_{case}({theme})' in output, (
        'The app must calculate after edits and execute the independent fit and results witness: '
        + output
    )
