"""Feedback wire fields and redaction from the independently declared feedback service contract."""

import json
import os
import subprocess
from pathlib import Path

import pytest

from tests.fixtures.onboarding.build_native import require_native

ROOT = Path(__file__).resolve().parents[3]
SOURCE = Path(os.environ.get('EDI_ONBOARDING_SOURCE_ROOT', ROOT))
MODULE = SOURCE / 'app/feedback/Payload.js'


@pytest.fixture(scope='module')
def payload_binary():
    assert MODULE.is_file(), (
        'The feedback form shares an executable payload builder with its preview'
    )
    return require_native(SOURCE, ROOT / 'build/onboarding-native', 'payload_probe')


def invoke(binary, tmp_path, **changes):
    request = {
        'module': str(MODULE),
        'kind': 'question',
        'text': 'A question from user-a at /synthetic-home/user-a/project',
        'include': True,
        'app': {
            'version': '8.7.6',
            'system': 'OS for user-a',
            'nested': {'folder': '/synthetic-home/user-a/cache'},
        },
        'log': '09:41:26.262  /synthetic-home/user-a/project  user=user-a',
        'home': '/synthetic-home/user-a',
        'user': 'user-a',
        'endpoint': 'https://feedback.example.invalid/feedback',
        'status': 201,
        **changes,
    }
    path = tmp_path / 'payload-request.json'
    path.write_text(json.dumps(request))
    run = subprocess.run(
        [str(binary), str(path)], capture_output=True, text=True, check=False, timeout=10
    )
    assert run.returncode == 0, (
        'The production payload helper executes in Qt without any network: ' + run.stderr
    )
    return request, json.loads(run.stdout)


@pytest.mark.parametrize('kind', ['feedback', 'question', 'problem', 'idea'])
def test_each_feedback_kind_uses_the_declared_wire_payload(payload_binary, tmp_path, kind):
    request, result = invoke(payload_binary, tmp_path, kind=kind)
    assert 'payload' in result, 'Every supported feedback kind builds its declared payload'
    payload = result['payload']
    assert payload['kind'] == kind, (
        'All four human-facing feedback kinds retain their feedback service tokens'
    )
    assert set(payload) == {'kind', 'text', 'app', 'log'}, (
        'Included feedback uses exactly the declared wire fields'
    )
    assert payload['app']['version'] == '8.7.6', (
        'An included version is preserved rather than regenerated'
    )
    assert payload['text'] == 'A question from ~ at ~/project', (
        'Redaction preserves the text around user-name and home-folder occurrences'
    )
    assert result['requests'] == [{'url': request['endpoint'], 'payload': payload}], (
        'The injected transport receives the exact preview payload at the configured endpoint'
    )


def test_redaction_reaches_all_nested_fields_and_the_log(payload_binary, tmp_path):
    _, result = invoke(payload_binary, tmp_path)
    encoded = json.dumps(result['payload'])
    assert '/synthetic-home/user-a' not in encoded and 'user-a' not in encoded, (
        'Neither home nor user name survives in text, nested app metadata or the log'
    )
    assert result['payload']['app']['nested']['folder'] == '~/cache', (
        'Nested metadata is redacted without losing its field structure'
    )
    assert result['payload']['log'] == '09:41:26.262  ~/project  user=~', (
        'Every occurrence in the attached log is redacted while other bytes retain their meaning'
    )


def test_unticked_attachment_excludes_app_details_and_log(payload_binary, tmp_path):
    _, result = invoke(payload_binary, tmp_path, include=False)
    payload = result['payload']
    assert not payload.get('app') and not payload.get('log'), (
        'Unticking attachment sends neither version and system metadata nor the log'
    )
    assert payload['kind'] == 'question' and payload['text'] == 'A question from ~ at ~/project', (
        'Unticking diagnostics retains the selected kind and the redacted user text'
    )


@pytest.mark.parametrize('status', [201, 400, 429])
def test_injected_endpoint_returns_each_declared_response(payload_binary, tmp_path, status):
    _, result = invoke(payload_binary, tmp_path, status=status)
    assert result['status'] == status, (
        'The feedback client preserves success, invalid-request and rate-limit outcomes'
    )
    assert len(result['requests']) == 1, (
        'A response never silently repeats the feedback submission'
    )


def test_empty_endpoint_never_calls_transport(payload_binary, tmp_path):
    _, result = invoke(payload_binary, tmp_path, endpoint='')
    assert result['requests'] == [], 'Unconfigured feedback cannot submit any request'


@pytest.mark.parametrize('kind', ['praise', 'thanks'])
def test_retired_kinds_are_no_longer_feedback_kinds(payload_binary, tmp_path, kind):
    _, result = invoke(payload_binary, tmp_path, kind=kind)
    assert result.get('error'), (
        'Retired praise and thanks tokens are rejected instead of submitted or aliased'
    )
    assert not result.get('requests') and 'payload' not in result, (
        'A retired feedback kind creates neither a wire payload nor a transport request'
    )
