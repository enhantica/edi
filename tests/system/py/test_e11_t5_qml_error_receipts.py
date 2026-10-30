"""Synthetic receipt-parser controls; these never claim original Qt outcomes."""

import copy
import json
from pathlib import Path
from types import SimpleNamespace

import e11_t5_original_qml_error_contract as receipts
import pytest
from e11_t5_original_qml_error_contract import assess_qml_contract


def _sample():
    warning = {
        'event': 'warning',
        'ordinal': 0,
        'phase': 'command',
        'command_sequence': '7',
        'operation': 'manual_text',
        'url': 'qrc:/original/AssistantComposer.qml',
        'line': 623,
        'column': 17,
        'description': 'TypeError: independent expected callback failure',
        'message_type': 1,
        'object_available': True,
        'object_name': 'assistant.composer',
        'rendered': 'qrc:/original/AssistantComposer.qml:623:17: '
        'TypeError: independent expected callback failure',
    }
    signature = {
        key: warning[key]
        for key in (
            'phase',
            'operation',
            'url',
            'line',
            'column',
            'description',
            'message_type',
            'object_available',
            'object_name',
        )
    }
    events = [
        {'event': 'capture_started', 'format': 1, 'stderr_enabled': True},
        warning,
        {'event': 'capture_finished', 'events': 1, 'failed': False},
    ]
    scopes = [{'step': 'intentional-original-operation', 'first': 7, 'last': 7}]
    contract = {
        'format': 1,
        'expected': [{'step': scopes[0]['step'], 'warning': signature, 'count': 1}],
    }
    return events, scopes, contract, warning['rendered'] + '\n'


def test_exact_required_warning_passes_only_complete_receipt():
    assert assess_qml_contract(*_sample()) == []


@pytest.mark.parametrize(
    ('field', 'value'),
    [
        ('phase', 'between_commands'),
        ('operation', 'inspect'),
        ('url', 'qrc:/unrelated/Other.qml'),
        ('line', 17),
        ('column', 2),
        ('description', 'TypeError: unrelated coding bug'),
        ('object_available', False),
        ('object_name', 'unrelated.component'),
    ],
)
def test_wrong_step_source_or_owner_is_not_an_expected_error(field, value):
    events, scopes, contract, stderr = _sample()
    events[1][field] = value
    assert assess_qml_contract(events, scopes, contract, stderr)


@pytest.mark.parametrize(
    'escape',
    [
        'missing_required',
        'extra_warning',
        'lost_footer',
        'stderr_muted',
        'capture_failure',
        'ordinal_gap',
        'missing_contract',
        'extra_stderr',
    ],
)
def test_receipt_completeness_and_unrelated_failure_escapes_refuse(escape):
    events, scopes, contract, stderr = _sample()
    if escape == 'missing_required':
        events.pop(1)
        events[-1]['events'] = 0
        stderr = ''
    elif escape == 'extra_warning':
        duplicate = copy.deepcopy(events[1])
        duplicate['ordinal'] = 1
        events.insert(2, duplicate)
        events[-1]['events'] = 2
        stderr += stderr
    elif escape == 'lost_footer':
        events.pop()
    elif escape == 'stderr_muted':
        events[0]['stderr_enabled'] = False
    elif escape == 'capture_failure':
        events[-1]['failed'] = True
    elif escape == 'ordinal_gap':
        events[1]['ordinal'] = 2
    elif escape == 'missing_contract':
        contract = None
    elif escape == 'extra_stderr':
        stderr += 'TypeError: independent unrelated QML failure\n'
    assert assess_qml_contract(events, scopes, contract, stderr)


@pytest.mark.parametrize(
    'prefix',
    [
        'TypeError: unrelated failure; ',
        'ReferenceError: unrelated; ',
        'qml: ',
        '[unreviewed logging prefix] ',
        ' ',
    ],
)
def test_unreviewed_or_coding_error_prefix_cannot_consume_expected_warning(prefix):
    events, scopes, contract, stderr = _sample()
    assert assess_qml_contract(events, scopes, contract, prefix + stderr)


@pytest.mark.parametrize(
    'line',
    [
        '{expected}; TypeError: second unrelated failure',
        'TypeError: first unrelated failure; {expected}',
        '{expected} {expected}',
    ],
)
def test_multiple_errors_on_one_line_never_count_as_one_expected_counterpart(line):
    events, scopes, contract, stderr = _sample()
    actual = line.format(expected=stderr.rstrip('\n')) + '\n'
    assert assess_qml_contract(events, scopes, contract, actual)


def _suffix_pair():
    events, scopes, contract, stderr = _sample()
    short = copy.deepcopy(events[1])
    short.update({
        'ordinal': 1,
        'url': '',
        'line': -1,
        'column': -1,
        'rendered': short['description'],
    })
    events.insert(2, short)
    events[-1]['events'] = 2
    signature = {key: short[key] for key in contract['expected'][0]['warning']}
    contract['expected'].append({'step': scopes[0]['step'], 'warning': signature, 'count': 1})
    return events, scopes, contract, stderr, short['rendered'] + '\n'


def test_suffix_overlap_requires_two_separate_exact_stderr_counterparts():
    events, scopes, contract, long_line, short_line = _suffix_pair()
    assert assess_qml_contract(events, scopes, contract, long_line)
    assert assess_qml_contract(events, scopes, contract, short_line)
    assert assess_qml_contract(events, scopes, contract, long_line + short_line) == []


class _SyntheticActor:
    """Protocol control only; this is never an original Qt/application observation."""

    def __init__(self, folder):
        self.folder = folder
        self.process = SimpleNamespace(returncode=0)
        self._command_sequence = 7
        self.close_calls = 0

    def close(self):
        self.close_calls += 1


def _owned_sample(tmp_path):
    events, scopes, contract, stderr = _sample()
    folder = tmp_path / 'synthetic-actor'
    folder.mkdir()
    (folder / 'qml-warning-events.jsonl').write_text(
        ''.join(json.dumps(event) + '\n' for event in events)
    )
    (folder / 'host.stderr').write_text(stderr)
    actor = _SyntheticActor(folder)
    host = receipts.IntentionalQmlHost(actor, contract)
    host.scopes = scopes
    return actor, host


def _break_finish(actor, host, monkeypatch, defect):
    if defect == 'missing_capture':
        (actor.folder / 'qml-warning-events.jsonl').unlink()
    elif defect == 'partial_capture':
        path = actor.folder / 'qml-warning-events.jsonl'
        path.write_text(path.read_text() + '{truncated')
    elif defect == 'invalid_capture_utf8':
        path = actor.folder / 'qml-warning-events.jsonl'
        path.write_bytes(path.read_bytes() + b'\xce')
    elif defect == 'event_schema':
        path = actor.folder / 'qml-warning-events.jsonl'
        lines = path.read_text().splitlines()
        lines[1] = '42'
        path.write_text('\n'.join(lines) + '\n')
    elif defect == 'missing_stderr':
        (actor.folder / 'host.stderr').unlink()
    elif defect == 'close_error':

        def broken_close():
            actor.close_calls += 1
            raise OSError('independent close sentinel')

        monkeypatch.setattr(actor, 'close', broken_close)
    elif defect == 'assessment_error':

        def broken_assessor(*_args):
            raise RuntimeError('independent assessment sentinel')

        monkeypatch.setattr(receipts, 'assess_qml_contract', broken_assessor)
    elif defect == 'assessment_schema':
        monkeypatch.setattr(
            receipts, 'assess_qml_contract', lambda *_args: {'not': 'problem-list'}
        )
    elif defect == 'serialization_error':
        host.contract['non_json_control'] = object()
    elif defect in {'persistence_error', 'all_persistence_errors', 'all_evidence_sinks_error'}:
        original = Path.write_text

        def broken_write(path, *args, **kwargs):
            targeted = path.name == 'intentional-qml-contract-assessment.json'
            if defect in {'all_persistence_errors', 'all_evidence_sinks_error'}:
                targeted = 'intentional-qml-contract' in path.name
            if targeted:
                raise OSError('independent persistence sentinel')
            return original(path, *args, **kwargs)

        monkeypatch.setattr(Path, 'write_text', broken_write)
        if defect == 'all_evidence_sinks_error':

            class BrokenStderr:
                @staticmethod
                def write(_text):
                    raise OSError('independent runner-stderr sentinel')

                @staticmethod
                def flush():
                    raise OSError('independent runner-flush sentinel')

            monkeypatch.setattr(receipts.sys, 'stderr', BrokenStderr())
    else:
        raise AssertionError('Unrecognized synthetic finalization defect: ' + defect)


def _assert_exception_identity(caught, primary, body_failed):
    if body_failed:
        assert caught.value is primary, 'A finalizer failure cannot replace the semantic exception'
    else:
        assert caught.value is not primary
        assert 'Intentional QML contract failed' in str(caught.value)


def _assert_assessment_identity(actor, facts, body_failed, primary):
    assert facts['body_failed'] is body_failed
    assert facts['problems'], 'Evidence loss never becomes an empty successful warning list'
    assert facts['secondary_errors']
    assert actor.close_calls == 1
    if body_failed:
        assert facts['primary_error']['representation'] == repr(primary)
    else:
        assert facts['primary_error'] is None


def _assert_capture_facts(actor, facts, defect):
    if defect != 'missing_capture':
        assert facts['raw_warning_log'], (
            'Retain raw capture even when parse/schema/assessment fails'
        )
        assert (
            bytes.fromhex(facts['raw_warning_log_hex'])
            == (actor.folder / 'qml-warning-events.jsonl').read_bytes()
        )
    else:
        assert facts['raw_warning_log'] is None
        assert facts['raw_warning_log_hex'] is None
    if defect != 'missing_stderr':
        assert facts['stderr'], 'Other collection failures cannot prevent obtaining stderr'
        assert bytes.fromhex(facts['stderr_hex']) == (actor.folder / 'host.stderr').read_bytes()
    else:
        assert facts['stderr'] is None


def _assert_persistence(facts, body_failed, defect, caught, capsys, primary):
    if defect in {'all_persistence_errors', 'all_evidence_sinks_error'}:
        assert facts['receipt_path'] is None
        if defect == 'all_evidence_sinks_error':
            assert any(row['stage'] == 'secondary_stderr' for row in facts['secondary_errors'])
            notes = caught.value.__notes__
            assert any('raw_warning_log' in note for note in notes)
        else:
            assert 'No file receipt could be persisted' in capsys.readouterr().err
        if body_failed:
            assert any('No file receipt could be persisted' in note for note in primary.__notes__)
    else:
        saved = json.loads(Path(facts['receipt_path']).read_text(encoding='utf-8'))
        assert saved['secondary_errors'] == facts['secondary_errors']
        assert saved['raw_warning_log'] == facts['raw_warning_log']
        assert saved['raw_warning_log_hex'] == facts['raw_warning_log_hex']
        assert saved['stderr_hex'] == facts['stderr_hex']
        assert saved['stderr'] == facts['stderr']


def _run_owned(host, primary, body_failed):
    with host:
        if body_failed:
            raise primary


@pytest.mark.parametrize('body_kind', [None, 'assertion', 'runtime'])
@pytest.mark.parametrize(
    'defect',
    [
        'missing_capture',
        'partial_capture',
        'invalid_capture_utf8',
        'event_schema',
        'missing_stderr',
        'close_error',
        'assessment_error',
        'assessment_schema',
        'serialization_error',
        'persistence_error',
        'all_persistence_errors',
        'all_evidence_sinks_error',
    ],
)
def test_finalization_failure_retains_primary_and_every_available_secondary_fact(
    tmp_path, monkeypatch, capsys, body_kind, defect
):
    body_failed = body_kind is not None
    actor, host = _owned_sample(tmp_path)
    _break_finish(actor, host, monkeypatch, defect)
    primary_type = RuntimeError if body_kind == 'runtime' else AssertionError
    primary = primary_type('independent semantic body sentinel')
    expected_type = primary_type if body_failed else AssertionError
    with pytest.raises(expected_type) as caught:
        _run_owned(host, primary, body_failed)
    _assert_exception_identity(caught, primary, body_failed)
    facts = host._last_facts
    _assert_assessment_identity(actor, facts, body_failed, primary)
    _assert_capture_facts(actor, facts, defect)
    _assert_persistence(facts, body_failed, defect, caught, capsys, primary)


def test_clean_receipt_control_really_finalizes_and_persists(tmp_path):
    actor, host = _owned_sample(tmp_path)
    with host:
        pass
    assert actor.close_calls == 1
    assert host._last_facts['problems'] == []
    assert host._last_facts['assessment_completed'] is True
    assert (
        json.loads(Path(host._last_facts['receipt_path']).read_text(encoding='utf-8'))[
            'body_failed'
        ]
        is False
    )


def test_semantic_body_failure_remains_primary_even_when_receipt_is_clean(tmp_path):
    actor, host = _owned_sample(tmp_path)
    primary = AssertionError('clean-capture semantic sentinel')
    with pytest.raises(AssertionError) as caught, host:
        raise primary
    assert caught.value is primary
    assert actor.close_calls == 1
    assert host._last_facts['problems'] == []
    assert host._last_facts['body_failed'] is True
    saved = json.loads(Path(host._last_facts['receipt_path']).read_text(encoding='utf-8'))
    assert saved['primary_error']['representation'] == repr(primary)


@pytest.mark.parametrize('mode', ['recording', 'missing-contract'])
def test_recording_and_missing_contract_still_fail_with_complete_synthetic_capture(tmp_path, mode):
    actor, host = _owned_sample(tmp_path)
    if mode == 'missing-contract':
        host.contract = None
    else:
        host.recording_original = True
    with pytest.raises(AssertionError), host:
        pass
    assert actor.close_calls == 1
    expected = 'unqualified' if mode == 'missing-contract' else 'recording'
    assert any(expected in problem for problem in host._last_facts['problems'])
