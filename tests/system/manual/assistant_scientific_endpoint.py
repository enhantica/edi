"""Check recorded assistant endpoints against ADR-0017 §17 and ADR-0020 §9."""

from __future__ import annotations

import argparse
import json
from copy import deepcopy
from pathlib import Path


def latest_fit_lifecycle(history):
    """Read actual adopted-fit and applied-Undo events from ordered native history."""
    if not isinstance(history, list):
        raise TypeError('Endpoint history must be an ordered array')
    last_fit = None
    last_undo = None
    for index, row in enumerate(history):
        if not isinstance(row, dict):
            raise TypeError('Every recorded history row requires an object')
        payload = row.get('payload')
        if payload is None:
            continue
        if not isinstance(payload, dict):
            raise TypeError('A recorded history payload must be an object or null')
        outcome = payload.get('nativeOutcome')
        if row.get('status') != 'completed' or not isinstance(outcome, dict):
            continue
        if payload.get('tool') == 'run_fit' and outcome.get('adopted') is True:
            last_fit = (index, row.get('id'))
        if payload.get('tool') == 'undo_fit' and outcome.get('applied') is True:
            last_undo = (index, row.get('id'))
    return last_fit, last_undo


def assess_endpoint(observation, history):
    """Require a real final fit without treating documented Undo clearing as a bug."""
    if not isinstance(observation, dict):
        raise TypeError('Endpoint observations require a result object')
    findings = []
    if (
        observation.get('completed_observation') is not True
        or observation.get('attention_required')
        or observation.get('driver_deadline_reached')
        or observation.get('exception_class')
    ):
        findings.append('provider_or_observation_incomplete')
    if observation.get('report_page_before_driver_view') is not True:
        findings.append('requested_report_not_shown')
    last_fit, last_undo = latest_fit_lifecycle(history)
    if last_fit is None:
        findings.append('no_adopted_final_fit')
    undone = last_undo is not None and (last_fit is None or last_undo[0] > last_fit[0])
    if undone:
        findings.append('final_fit_required_after_rejected_trial_undo')
    fit = observation.get('fit')
    rows = fit.get('results') if isinstance(fit, dict) else None
    if not isinstance(rows, int) or isinstance(rows, bool) or rows <= 0:
        findings.append('current_final_fit_result_missing')
    if isinstance(fit, dict) and fit.get('running') is True:
        findings.append('final_fit_still_running')
    return {
        'passed': not findings,
        'findings': findings,
        'last_adopted_fit_row': last_fit[1] if last_fit else None,
        'last_applied_undo_row': last_undo[1] if last_undo else None,
        'documented_undo_cleared_result': undone and rows == 0,
        'current_result_rows': rows,
    }


def check_documented_controls():
    """Exercise authored lifecycle examples, without pretending to supply fit data."""
    observation = {
        'completed_observation': True,
        'report_page_before_driver_view': True,
        'fit': {'results': 4, 'running': False},
    }
    fitted = {
        'id': 'accepted-fit',
        'status': 'completed',
        'payload': {'tool': 'run_fit', 'nativeOutcome': {'adopted': True}},
    }
    undone = {
        'id': 'rejected-trial-undo',
        'status': 'completed',
        'payload': {'tool': 'undo_fit', 'nativeOutcome': {'applied': True}},
    }
    assert assess_endpoint(observation, [fitted])['passed'], (
        'An adopted final fit with current results satisfies the documented endpoint'
    )
    assert not assess_endpoint(observation, [fitted, undone])['passed'], (
        'A positive stale row count cannot resurrect a fit after its successful Undo'
    )
    cleared = deepcopy(observation)
    cleared['fit']['results'] = 0
    result = assess_endpoint(cleared, [fitted, undone])
    assert result['documented_undo_cleared_result'] and not result['passed'], (
        'Documented Undo clearing is distinguished from an accepted scientific endpoint'
    )
    final_fit = deepcopy(fitted)
    final_fit['id'] = 'final-accepted-fit'
    assert assess_endpoint(observation, [fitted, undone, final_fit])['passed'], (
        'A genuine later adopted fit can establish the final accepted endpoint'
    )
    final_fit['payload']['nativeOutcome']['adopted'] = False
    assert not assess_endpoint(observation, [fitted, undone, final_fit])['passed'], (
        'An unadopted later fit cannot qualify an endpoint after the rejected trial'
    )
    saved = {
        'id': 'save',
        'status': 'completed',
        'payload': {'tool': 'save_project', 'nativeOutcome': {'saved': True}},
    }
    assert not assess_endpoint(cleared, [fitted, undone, saved])['passed'], (
        'A genuine Save cannot manufacture the missing final fit provenance'
    )
    assert not assess_endpoint(observation, [])['passed'], (
        'Current result rows require their actual adopted fit in the recorded history'
    )
    incomplete = deepcopy(observation)
    incomplete['completed_observation'] = False
    incomplete['report_page_before_driver_view'] = False
    assert not assess_endpoint(incomplete, [fitted])['passed'], (
        'Final fit evidence never replaces provider completion and the requested report'
    )


def main():
    """Read existing matrix observations without running a provider or changing evidence."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('case_directories', nargs='+', type=Path)
    args = parser.parse_args()
    check_documented_controls()
    failed = False
    for directory in args.case_directories:
        try:
            observation = json.loads((directory / 'RESULT.json').read_text())
            history = json.loads((directory / 'final-canonical-history.json').read_text())
            result = assess_endpoint(observation, history)
        except (OSError, ValueError, TypeError) as error:
            result = {'passed': False, 'findings': ['unreadable_endpoint'], 'error': str(error)}
        print(json.dumps({'case': str(directory), **result}))
        failed = failed or not result['passed']
    return int(failed)


if __name__ == '__main__':
    raise SystemExit(main())
