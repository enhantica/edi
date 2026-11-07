# SPDX-License-Identifier: BSD-3-Clause
"""Check assistant test defaults and About-style links in native Qt."""

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
CASES = [
    'freshAssistantTestsUseTheRequestedModelAndKeepExplicitChoices',
    'downloadLinkUsesTheAboutLinkStyleInBothThemes',
]


@pytest.mark.parametrize('case', CASES)
def test_native_assistant_presentation_contract(case):
    suffix = '.exe' if os.name == 'nt' else ''
    executable = ROOT / f'build/app/assistant-ui-probe/assistant_independent_lock{suffix}'
    result = subprocess.run(
        [str(executable), case],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
        env={
            **os.environ,
            'QT_QPA_PLATFORM': os.environ.get('QT_QPA_PLATFORM', 'offscreen'),
            'QT_QUICK_BACKEND': 'software',
        },
    )
    assert result.returncode == 0 and '0 failed' in result.stdout, (
        'The native assistant presentation contract must hold: '
        + case
        + '\n'
        + result.stdout
        + result.stderr
    )
