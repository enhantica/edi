# SPDX-License-Identifier: BSD-3-Clause
"""Feedback prompt eligibility with a synthetic clock and session history."""

import json
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
START = datetime(2026, 1, 1, tzinfo=UTC)


def milliseconds(value):
    return int(value.timestamp() * 1000)


@pytest.mark.parametrize(
    ('changes', 'days', 'expected'),
    [
        ({}, 7, True),
        ({}, 6.999, False),
        ({'sessions': 2}, 10, False),
        ({'sessions': 1}, 100, False),
        ({'fitSucceeded': False}, 10, False),
        ({'fitting': True}, 10, False),
        ({'tutorial': True}, 10, False),
        ({'disabled': True}, 100, False),
        ({'lastPrompt': milliseconds(START + timedelta(days=7))}, 8, False),
        ({'lastPrompt': milliseconds(START + timedelta(days=7))}, 50, False),
        # Jan 8 to Apr 8 is the independently specified three-calendar-month boundary.
        ({'lastPrompt': milliseconds(START + timedelta(days=7))}, 96.999, False),
        ({'lastPrompt': milliseconds(START + timedelta(days=7))}, 97, True),
        ({'lastPrompt': milliseconds(START + timedelta(days=7))}, 110, True),
    ],
)
def test_prompt_eligibility_uses_sessions_age_and_activity(changes, days, expected):
    module = ROOT / 'app/feedback/Likes.js'
    assert module.is_file(), 'ADR-0063: the likes prompt exposes its injectable clock policy'
    state = {
        'sessions': 3,
        'firstSession': milliseconds(START),
        'lastPrompt': None,
        'fitSucceeded': True,
        'fitting': False,
        'tutorial': False,
        'disabled': False,
        **changes,
    }
    request = {
        'module': str(module),
        'operation': 'eligible',
        'args': [state, milliseconds(START + timedelta(days=days))],
    }
    run = subprocess.run(
        ['node', str(ROOT / 'tests/fixtures/feedback_contract/driver.cjs')],
        input=json.dumps(request),
        text=True,
        capture_output=True,
        check=False,
        timeout=10,
    )
    assert run.returncode == 0, 'ADR-0063: eligibility runs with a synthetic clock and no network'
    result = json.loads(run.stdout)
    assert result.get('result') is expected, (
        'ADR-0063: prompt requires a successful fit, three sessions and seven days; '
        'active fitting, tutorials, opt-out and a recent prompt suppress it'
    )
