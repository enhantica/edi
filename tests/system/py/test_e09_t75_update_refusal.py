"""Review-13 F1: field pagination and successful retry observation."""

from __future__ import annotations

import json
import subprocess

import pytest

from tests.system.py.test_e09_t75_sdk_update import update, update_probe


def test_admitted_field_pagination_changes_the_requested_page(tmp_path):
    command = (
        'gh api repos/enhantica/edi/pulls -X GET --raw-field per_page=1 --raw-field page=1; '
        'gh api repos/enhantica/edi/pulls -X GET --raw-field per_page=1 --raw-field page=2'
    )
    runs, *_ = update(tmp_path, workflow_override=update_probe(command))
    result = runs[-1]
    if result.returncode:
        assert (tmp_path / 'unsupported-commands.jsonl').is_file(), (
            ' F1a a narrowed field-pagination route must persist its refusal'
        )
        return
    first, second = [json.loads(line) for line in result.stdout.splitlines()]
    assert len(first) == 1, ' F1a the supported first-page control must return its planted PR'
    assert second == [], ' F1a the same admitted request fields must select the empty second page'


def test_successful_updater_retry_cannot_erase_a_transport_refusal(tmp_path, monkeypatch):
    control = tmp_path / 'control'
    control.mkdir()
    runs, state, *_ = update(control, defect='lost-dispatch')
    assert runs[-1].returncode == 0, ' F1c the ordinary interrupted-dispatch retry must recover'
    assert state['dispatched'], ' F1c recovery control must cross the dispatch boundary'
    subject = tmp_path / 'subject'
    subject.mkdir()
    real_run = subprocess.run
    injected = []

    def run(argv, **kwargs):
        if 'tools/ci/crysta_sdk_update.py' in argv and (subject / 'state.json').exists():
            data = json.loads((subject / 'state.json').read_text())
            if data['defect'] is None and data['pushed']:
                argv = [
                    'bash',
                    '-c',
                    'gh api repos/enhantica/edi/pulls --unknown-format || true; exec "$@"',
                    'retry-fixture',
                    *argv,
                ]
                injected.append(True)
        return real_run(argv, **kwargs)

    monkeypatch.setattr(subprocess, 'run', run)
    with pytest.raises(AssertionError, match='unsupported command form'):
        update(subject, defect='lost-dispatch')
    assert injected, ' F1c the swallowed operation must occur inside the successful retry'
