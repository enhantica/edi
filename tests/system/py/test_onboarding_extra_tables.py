"""One live LBCO table census, shared by its independent presentation checks."""

import os
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope='module')
def extra_table_observation():
    # One real window/project lifetime avoids loading LBCO for empty Extra tabs.
    # The complete native cost is recorded once by the module-fixture cost bank.
    runner = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assert runner.is_file(), 'The Extra-table census requires the real Qt app host'
    result = subprocess.run(
        [
            str(runner),
            '-input',
            str(ROOT / 'tests/unit/app/tst_onboarding_extra_tables.qml'),
            '-o',
            '-,txt',
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
        env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen', 'QT_QUICK_BACKEND': 'software'},
    )
    return result.stdout + result.stderr


@pytest.mark.parametrize(
    'case',
    [
        *[
            f'every_extra_table_sizes_columns_from_content:{page}'
            for page in ('structure', 'project', 'experiment', 'analysis', 'report')
        ],
        'numeric_cells_follow_atom_sites_and_cartesian_zero',
        'scattering_lengths_explains_standard_values_without_overrides',
    ],
)
def test_extra_table_in_the_real_application(extra_table_observation, case):
    function, _, tag = case.partition(':')
    selector = f'OnboardingExtraTables::test_{function}({tag})'
    assert not re.search(
        r'^(?:FAIL!|SKIP)\s*:.*::(?:initTestCase|cleanupTestCase)\(',
        extra_table_observation,
        re.MULTILINE,
    ), (
        'The shared real LBCO host starts and ends without a setup/teardown failure: '
        + extra_table_observation
    )
    assert re.search(
        r'^PASS\s*:.*' + re.escape(selector) + r'\s*$', extra_table_observation, re.MULTILINE
    ), (
        'The actual Extra-table observation satisfies its scoped presentation requirement: '
        + selector
        + '\n'
        + extra_table_observation
    )
