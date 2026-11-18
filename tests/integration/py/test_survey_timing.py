# SPDX-License-Identifier: BSD-3-Clause
"""Survey invitation and cross-bar timing from the approved feedback rules."""

import json
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
DAY = 24 * 60 * 60 * 1000
NOW = int(datetime(2026, 5, 19, 8, 12, 23, tzinfo=UTC).timestamp() * 1000)


def state(**changes):
    return {
        'sessions': 5,
        'firstSession': NOW - 14 * DAY,
        'disabled': False,
        'stopped': False,
        'lastShown': None,
        'sessionsAtShown': 0,
        'usefulWork': True,
        'idle': 60_000,
        'fitting': False,
        'tutorial': False,
        'likesDue': False,
        'barShown': False,
        'otherShown': None,
        **changes,
    }


def invoke(calls):
    request = {'module': str(ROOT / 'app/feedback/Likes.js'), 'calls': calls}
    run = subprocess.run(
        ['node', str(ROOT / 'tests/fixtures/feedback_contract/driver.cjs')],
        input=json.dumps(request),
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert run.returncode == 0, 'Survey invitations: the injected-clock policy executes offline'
    outcome = json.loads(run.stdout)
    assert 'error' not in outcome, (
        'Survey invitations: production exposes the clock policy used by the survey bar'
    )
    return outcome['result']


def case(name, expected, **changes):
    return pytest.param(changes, expected, id=name)


@pytest.mark.parametrize(
    ('changes', 'expected'),
    [
        case('first-boundaries', True),
        case('too-few-sessions', False, sessions=4),
        case('just-before-two-weeks', False, firstSession=NOW - 14 * DAY + 1),
        case('just-before-idle-minute', False, idle=59_999),
        case('fresh-user-input', False, idle=0),
        case('startup-is-not-useful-work', False, usefulWork=False),
        case('fit-in-progress', False, fitting=True),
        case('tutorial-in-progress', False, tutorial=True),
        case('preference-off', False, disabled=True),
        case(
            'permanently-stopped',
            False,
            stopped=True,
            sessions=100,
            firstSession=NOW - 365 * DAY,
            lastShown=NOW - 300 * DAY,
            sessionsAtShown=5,
        ),
        case('same-session-other-bar', False, barShown=True),
        case('same-session-even-after-week', False, barShown=True, otherShown=NOW - 8 * DAY),
        case('other-bar-just-before-week', False, otherShown=NOW - 7 * DAY + 1),
        case('other-bar-at-week', True, otherShown=NOW - 7 * DAY),
        case('other-bar-in-future', False, otherShown=NOW + 1),
        case('likes-go-first', False, likesDue=True),
        case(
            'defer-at-both-boundaries',
            True,
            sessions=7,
            firstSession=NOW - 60 * DAY,
            lastShown=NOW - 30 * DAY,
            sessionsAtShown=5,
        ),
        case(
            'defer-just-before-thirty-days',
            False,
            sessions=7,
            firstSession=NOW - 60 * DAY,
            lastShown=NOW - 30 * DAY + 1,
            sessionsAtShown=5,
        ),
        case(
            'defer-only-one-new-session',
            False,
            sessions=6,
            firstSession=NOW - 60 * DAY,
            lastShown=NOW - 40 * DAY,
            sessionsAtShown=5,
        ),
        case(
            'defer-many-sessions-not-enough-days',
            False,
            sessions=50,
            firstSession=NOW - 60 * DAY,
            lastShown=NOW - 29 * DAY,
            sessionsAtShown=5,
        ),
        case(
            'defer-many-days-no-new-session',
            False,
            sessions=5,
            firstSession=NOW - 365 * DAY,
            lastShown=NOW - 300 * DAY,
            sessionsAtShown=5,
        ),
        case(
            'stopped-never-reappears-with-age',
            False,
            stopped=True,
            sessions=1000,
            firstSession=NOW - 1000 * DAY,
            lastShown=NOW - 900 * DAY,
            sessionsAtShown=5,
        ),
        case(
            'disabled-never-reappears-with-age',
            False,
            disabled=True,
            sessions=1000,
            firstSession=NOW - 1000 * DAY,
            lastShown=NOW - 900 * DAY,
            sessionsAtShown=5,
        ),
    ],
)
def test_survey_offer_requires_useful_work_idle_and_persisted_history(changes, expected):
    result = invoke([{'operation': 'surveyEligible', 'args': [state(**changes), NOW]}])
    assert result == [expected], (
        'Survey invitations: five sessions over fourteen days and one idle minute are required; '
        'deferral requires thirty days and two more sessions, stop is permanent, '
        'and bar spacing applies'
    )


def test_survey_rechecks_current_activity_and_likes_priority_before_showing():
    changes = [
        {},
        {'idle': 0},
        {'fitting': True},
        {'tutorial': True},
        {'barShown': True},
        {'likesDue': True},
        {},
    ]
    result = invoke([
        {'operation': 'surveyEligible', 'args': [state(**change), NOW]} for change in changes
    ])
    assert result == [True, False, False, False, False, False, True], (
        'Survey invitations: a previously eligible offer is rechecked after input, fit, tutorial '
        'or another bar and never retains a cached permission to show'
    )


def test_survey_uses_the_injected_clock_for_first_use_and_deferral():
    first = state(firstSession=NOW)
    later = NOW + int(timedelta(days=14).total_seconds() * 1000)
    deferred = state(sessions=7, firstSession=NOW - 60 * DAY, lastShown=NOW, sessionsAtShown=5)
    result = invoke([
        {'operation': 'surveyEligible', 'args': [first, later - 1]},
        {'operation': 'surveyEligible', 'args': [first, later]},
        {'operation': 'surveyEligible', 'args': [deferred, NOW + 30 * DAY - 1]},
        {'operation': 'surveyEligible', 'args': [deferred, NOW + 30 * DAY]},
    ])
    assert result == [False, True, False, True], (
        'Survey invitations: first-use and deferral boundaries use the injected UTC clock'
    )


@pytest.mark.parametrize(
    ('changes', 'expected'),
    [
        case('no-other-bar', True),
        case('survey-already-shown-this-session', False, barShown=True),
        case('survey-just-before-week', False, otherShown=NOW - 7 * DAY + 1),
        case('survey-at-week', True, otherShown=NOW - 7 * DAY),
        case('survey-in-future', False, otherShown=NOW + 1),
        case('likes-win-when-both-due', True, surveyDue=True),
    ],
)
def test_likes_also_respects_session_exclusion_and_seven_day_spacing(changes, expected):
    history = {
        'sessions': 5,
        'firstSession': NOW - 14 * DAY,
        'lastPrompt': None,
        'fitSucceeded': True,
        'fitting': False,
        'tutorial': False,
        'disabled': False,
        'barShown': False,
        'otherShown': None,
        **changes,
    }
    assert invoke([{'operation': 'eligible', 'args': [history, NOW]}]) == [expected], (
        'Feedback prompts: likes goes first when both qualify but respects a survey already '
        'shown in this session and the seven-day separation'
    )
