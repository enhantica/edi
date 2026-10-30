"""Strict original-QML error receipts for separately owned intentional-error hosts.

No permissive contract is shipped: exact expected warnings require original
source attribution and independent review before a passing error gate is wired.
"""
from __future__ import annotations

import collections
import json
import re
import sys
import traceback as traceback_module

_SIGNATURE = ('phase', 'operation', 'url', 'line', 'column', 'description',
              'message_type', 'object_available', 'object_name')
_CODING = re.compile(r'ReferenceError|TypeError|Unable to assign \[undefined\]|'
                     r'Cannot assign to non-existent property|Detected function .*Connections')


def _signature(event):
    return tuple(event[key] for key in _SIGNATURE)


def assess_qml_contract(events, scopes, contract, stderr):
    """Return every discrepancy; no global warning/type/error substring exemption."""
    problems = []
    if not events or events[0].get('event') != 'capture_started' \
            or events[-1].get('event') != 'capture_finished':
        return ['Complete native start/finish warning receipt is required']
    if events[0].get('format') != 1 or events[0].get('stderr_enabled') is not True:
        problems.append('Original Qt stderr emission must remain enabled')
    warnings = events[1:-1]
    if any(row.get('event') != 'warning' or row.get('ordinal') != index
           for index, row in enumerate(warnings)):
        problems.append('Warning receipt event sequence must be complete and ordered')
    if events[-1].get('failed') is not False or events[-1].get('events') != len(warnings):
        problems.append('Native warning capture must finish without a lost receipt')
    if not contract or contract.get('format') != 1 or not contract.get('expected'):
        problems.append('Original expected-error contract is unqualified; recording alone never passes')
        return problems
    expected = collections.Counter()
    for row in contract['expected']:
        if type(row.get('count')) is not int or row['count'] <= 0 or not isinstance(row.get('step'), str):
            problems.append('Every exact expected warning needs a positive count and explicit step')
            continue
        if set(row.get('warning', {})) != set(_SIGNATURE):
            problems.append('Every expected warning needs the complete source/owner signature without wildcards')
            continue
        expected[(row['step'], _signature(row['warning']))] += row['count']
    observed = collections.Counter()
    rendered = collections.Counter()
    for warning in warnings:
        if not all(key in warning for key in _SIGNATURE):
            problems.append('Warning receipt lacks required source/owner fields')
            continue
        if warning['phase'] != 'command':
            problems.append('Unscoped startup/between-command/teardown warning: ' + repr(warning))
            continue
        sequence = warning.get('command_sequence')
        if not isinstance(sequence, str) or not sequence.isdecimal():
            problems.append('Warning has no exact native command sequence')
            continue
        sequence = int(sequence)
        matching = [row['step'] for row in scopes if row['first'] <= sequence <= row['last']]
        if len(matching) != 1:
            problems.append('Warning belongs to no unique intentional operation: ' + repr(warning))
            continue
        observed[(matching[0], _signature(warning))] += 1
        if _CODING.search(warning.get('rendered', '')):
            rendered[warning['rendered']] += 1
    if observed != expected:
        problems.append('Exact expected/observed warning counts differ: ' + repr((expected, observed)))
    # Accept only an exact rendered line; no logging-prefix grammar is elected.
    # Console/unreceipted/extra coding errors cannot pass as an expected warning.
    for line in stderr.splitlines():
        if not _CODING.search(line):
            continue
        matches = [text for text, count in rendered.items() if count > 0 and line == text]
        if len(matches) != 1:
            problems.append('Unreceipted or ambiguous coding-error stderr: ' + line)
        else:
            rendered[matches[0]] -= 1
    if any(rendered.values()):
        problems.append('Structured coding warnings lack their original stderr counterparts')
    return problems


def _safe_repr(value):
    try:
        return repr(value)
    except BaseException:
        return '<unprintable ' + type(value).__name__ + '>'


def _error_fact(stage, error):
    try:
        trace = ''.join(traceback_module.format_exception(type(error), error, error.__traceback__))
    except BaseException:
        trace = '<traceback unavailable; exception representation follows>'
    return {'stage': stage, 'type': type(error).__module__ + '.' + type(error).__qualname__,
            'representation': _safe_repr(error), 'traceback': trace}


class IntentionalQmlHost:
    """Own an existing MainActor separately; never weaken main_actor teardown."""
    def __init__(self, actor, contract, *, recording_original=False):
        self.actor = actor
        self.contract = contract
        self.recording_original = recording_original
        self.scopes = []
        self._finished = False
        self._last_facts = None

    def step(self, label, action):
        """Wrap only existing caller actions; no extra app command/event turn."""
        if not isinstance(label, str) or not label or any(row['step'] == label for row in self.scopes):
            raise ValueError('Intentional operation labels must be unique nonempty strings')
        first = self.actor._command_sequence + 1
        try:
            return action(self.actor)
        finally:
            self.scopes.append({'step': label, 'first': first, 'last': self.actor._command_sequence})

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception, traceback):
        try:
            self._finish(body_exception=exception)
        except BaseException as secondary:
            if exception_type is None:
                raise
            # Backstop for an unexpected finalizer failure, including a repeated finish.
            # The exact semantic body exception still leaves the with statement as primary.
            try:
                facts = self._last_facts or self._initial_facts(exception)
                facts['body_failed'] = True
                facts['primary_error'] = _error_fact('semantic_body', exception)
                self._record_failure(facts, 'unexpected_finalizer', secondary)
                self._persist(facts, exception)
            except BaseException as persistence_error:
                note = 'Intentional QML finalizer could not persist secondary facts: ' + _safe_repr(
                    (self._last_facts, _error_fact('emergency_persistence', persistence_error)))
                self._attach_note(exception, note)
        return False

    def finish(self):
        return self._finish()

    def _initial_facts(self, body_exception):
        return {'format': 1, 'events': None, 'raw_warning_log': None, 'raw_warning_log_hex': None,
                'scopes': self.scopes,
                'contract': self.contract, 'problems': [], 'secondary_errors': [],
                'recording_original': self.recording_original, 'host_exit': None,
                'stderr': None, 'stderr_hex': None, 'body_failed': body_exception is not None,
                'primary_error': _error_fact('semantic_body', body_exception)
                    if body_exception is not None else None,
                'assessment_completed': False, 'receipt_path': None}

    @staticmethod
    def _record_failure(facts, stage, error):
        failure = _error_fact(stage, error)
        facts['secondary_errors'].append(failure)
        facts['problems'].append(stage + ' failed: ' + failure['representation'])

    @staticmethod
    def _attach_note(error, note):
        if error is not None:
            try:
                BaseException.add_note(error, note)
            except BaseException:
                # The complete facts are also emitted to the enclosing runner's stderr below.
                pass

    def _persist(self, facts, body_exception):
        """Retain every obtainable fact; unavailable storage is always a gate failure."""
        folder = self.actor.folder
        destinations = [folder / 'intentional-qml-contract-assessment.json',
                        folder / 'intentional-qml-contract-secondary.json',
                        folder.parent / (folder.name + '-intentional-qml-contract-secondary.json')]
        for destination in destinations:
            facts['receipt_path'] = str(destination)
            try:
                text = json.dumps(facts, indent=2)
            except BaseException as error:
                self._record_failure(facts, 'assessment_serialization', error)
                # Do not accept a malformed/non-JSON contract. Preserve raw capture and
                # printable representations when the ordinary full receipt cannot serialize.
                fallback = {
                    'format': 1, 'body_failed': facts['body_failed'],
                    'primary_error': facts['primary_error'],
                    'secondary_errors': facts['secondary_errors'], 'problems': facts['problems'],
                    'raw_warning_log': facts['raw_warning_log'],
                    'raw_warning_log_hex': facts['raw_warning_log_hex'],
                    'stderr': facts['stderr'], 'stderr_hex': facts['stderr_hex'],
                    'recording_original': facts['recording_original'],
                    'events_repr': _safe_repr(facts.get('events')),
                    'scopes_repr': _safe_repr(facts.get('scopes')),
                    'contract_repr': _safe_repr(facts.get('contract')),
                    'host_exit_repr': _safe_repr(facts.get('host_exit')),
                    'events': None, 'scopes': None, 'contract': None, 'host_exit': None,
                    'assessment_completed': False, 'receipt_path': str(destination),
                }
                facts.clear()
                facts.update(fallback)
                text = json.dumps(facts, indent=2)
            try:
                destination.write_text(text)
            except BaseException as error:
                self._record_failure(facts, 'assessment_persistence', error)
                continue
            return str(destination)
        facts['receipt_path'] = None
        note = 'No file receipt could be persisted for intentional QML assessment: ' + json.dumps(facts)
        self._attach_note(body_exception, note)
        try:
            sys.stderr.write(note + '\n')
            sys.stderr.flush()
        except BaseException as error:
            self._record_failure(facts, 'secondary_stderr', error)
            self._attach_note(body_exception, _safe_repr(facts))
        return None

    def _finish(self, *, body_exception=None):
        if self._finished:
            raise RuntimeError('An intentional-error host has one terminal assessment')
        self._finished = True
        facts = self._initial_facts(body_exception)
        self._last_facts = facts

        def attempt(stage, action):
            try:
                return True, action()
            except BaseException as error:
                self._record_failure(facts, stage, error)
                return False, None

        # Failure in one collection step cannot prevent the other raw facts being retained.
        attempt('host_close', self.actor.close)
        got_log, raw_bytes = attempt('warning_capture_read', lambda: (
            self.actor.folder / 'qml-warning-events.jsonl').read_bytes())
        parsed = got_log
        if got_log:
            facts['raw_warning_log_hex'] = raw_bytes.hex()
            decoded, raw = attempt('warning_capture_decode', lambda: raw_bytes.decode('utf-8'))
            if not decoded:
                parsed = False
                raw = raw_bytes.decode('utf-8', errors='replace')
            facts['raw_warning_log'] = raw
            facts['events'] = []
            for index, line in enumerate(raw.splitlines(), start=1):
                ok, event = attempt('warning_json_line_' + str(index), lambda line=line: json.loads(line))
                if ok:
                    facts['events'].append(event)
                    if not isinstance(event, dict):
                        self._record_failure(facts, 'warning_event_schema',
                                             ValueError('Every warning receipt event must be an object'))
                        parsed = False
                else:
                    parsed = False
        got_stderr, stderr_bytes = attempt('stderr_read', lambda: (
            self.actor.folder / 'host.stderr').read_bytes())
        if got_stderr:
            facts['stderr_hex'] = stderr_bytes.hex()
            stderr = stderr_bytes.decode('utf-8', errors='replace')
            facts['stderr'] = stderr
        if parsed and got_stderr:
            assessed, problems = attempt('contract_assessment', lambda: assess_qml_contract(
                facts['events'], self.scopes, self.contract, stderr))
            if assessed:
                if isinstance(problems, list) and all(isinstance(item, str) for item in problems):
                    facts['problems'].extend(problems)
                    facts['assessment_completed'] = True
                else:
                    self._record_failure(facts, 'assessment_result_schema',
                                         TypeError('Assessment must return a list of problem strings'))
        if self.recording_original:
            facts['problems'].append('Original warning-recording stage is diagnostic and cannot qualify a passing gate')
        got_exit, host_exit = attempt('host_exit_read', lambda: self.actor.process.returncode)
        if got_exit:
            facts['host_exit'] = host_exit
        if not got_exit or host_exit != 0:
            facts['problems'].append('Original owned host did not exit normally')
        self._persist(facts, body_exception)
        if facts['problems'] and body_exception is not None:
            self._attach_note(body_exception, 'Intentional QML secondary failures: '
                              + _safe_repr(facts['problems']) + '; receipt: '
                              + _safe_repr(facts['receipt_path']))
        if facts['problems'] and body_exception is None:
            failure = AssertionError('Intentional QML contract failed; see receipt path and secondary evidence: '
                                     + _safe_repr(facts['problems']))
            self._attach_note(failure, 'Receipt path: ' + _safe_repr(facts['receipt_path']))
            if facts['receipt_path'] is None:
                self._attach_note(failure, 'No file receipt; complete obtainable facts: ' + _safe_repr(facts))
            raise failure
        return facts
