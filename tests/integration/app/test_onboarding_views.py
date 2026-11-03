"""Exercise onboarding controls through the production Qt Quick Test host."""

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
CASES = [
    ('tst_recent_projects_height.qml', 'RecentProjectsHeight', 'status_header_is_empty'),
    (
        'tst_recent_projects_height.qml',
        'RecentProjectsHeight',
        'recent_table_grows_when_sidebar_grows',
    ),
    ('tst_onboarding_home.qml', 'OnboardingHome', 'six_links_have_icons_and_two_columns'),
    (
        'tst_onboarding_home.qml',
        'OnboardingHome',
        'public_documentation_destinations:documentation',
    ),
    ('tst_onboarding_home.qml', 'OnboardingHome', 'public_documentation_destinations:changes'),
    ('tst_onboarding_home.qml', 'OnboardingHome', 'citation_popup_offers_text_and_bibtex'),
    (
        'tst_onboarding_home.qml',
        'OnboardingHome',
        'citation_clipboard_uses_the_shared_placeholder',
    ),
]


@pytest.mark.parametrize(('actor', 'suite', 'case'), CASES, ids=[case for _, _, case in CASES])
def test_production_onboarding_control(actor, suite, case):
    runner = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assert runner.is_file(), 'Onboarding acceptance requires the production Qt Quick Test host'
    result = subprocess.run(
        [
            str(runner),
            '-input',
            str(ROOT / 'tests/unit/app' / actor),
            '-o',
            '-,txt',
            f'{suite}::test_{case}',
        ],
        env={
            **os.environ,
            'QT_QPA_PLATFORM': 'offscreen',
            'QT_QUICK_BACKEND': 'software',
        },
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0, 'The real onboarding control meets its requirement: ' + output
    function, _, tag = case.partition(':')
    receipt = f'::{suite}::test_{function}({tag})'
    assert receipt in output and '0 failed' in output, (
        'Every requested onboarding actor must actually execute its exact case: ' + output
    )
    assert not any(line.startswith('SKIP') for line in output.splitlines()), (
        'Onboarding acceptance cannot replace a required production case with a skip'
    )
