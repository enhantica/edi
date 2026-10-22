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
    return subprocess.run(
        [
            str(runner),
            '-input',
            str(ROOT / 'tests/unit/app/tst_single_crystal_views.qml'),
            '-o',
            '-,txt',
        ],
        cwd=ROOT,
        env={
            **os.environ,
            'EDI_ACCEPTANCE_REFERENCE': str(ROOT / 'tests/fixtures/single_crystal'),
        },
        capture_output=True,
        text=True,
        check=False,
        timeout=180,
    )


@pytest.mark.parametrize('project', PROJECTS)
@pytest.mark.parametrize('theme', ['light', 'dark'])
@pytest.mark.parametrize('page', ['experiment', 'analysis'])
def test_real_single_crystal_chart_table_and_sidebar(app_result, project, theme, page):
    output = app_result.stdout + app_result.stderr
    assert app_result.returncode == 0, (
        'Every real app case and cleanup must complete successfully: ' + output
    )
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
    assert app_result.returncode == 0, (
        'Every real app case and cleanup must complete successfully: ' + output
    )
    assert (
        'PASS   : edi_app::SingleCrystalViews::test_powder_view_unchanged'
        f'({theme}-{page})' in output
    ), 'The real powder chart and sidebar must remain unchanged in each theme: ' + output
