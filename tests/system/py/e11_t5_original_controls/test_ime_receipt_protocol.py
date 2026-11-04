"""Synthetic observer controls using immutable actual90; no whole recording positive."""

import hashlib
import json
import os
from pathlib import Path

import pytest

from . import test_current_original as controller


def _sample():
    folder = Path(os.environ['EDI_E11_ORIGINAL90_READONLY'])
    assert folder.is_absolute(), 'Actual90 custody input must be explicit and absolute'
    raw = (folder / 'qml-warning-events.jsonl').read_bytes()
    effects = (folder / 'original-composer-null-owner-effects.json').read_bytes()
    assert hashlib.sha256(raw).hexdigest() == (
        '6ef01a8b1ef067460a681dcf676037b381a77b1808a12ec3514d563e68bcea09'
    ), 'Use the immutable original90 native receipt, never current/post output'
    assert hashlib.sha256(effects).hexdigest() == (
        '49c0048bd384769cb17daa6300e8ac4c4c87d31090c4144a6df42af34ff893f8'
    ), 'Use the exact failed original90 semantic evidence'
    lines = raw.splitlines(keepends=True)
    prefix = b''.join(lines[:-3])
    warnings = [json.loads(line) for line in lines[-3:-1]]
    facts = {
        'warning_before_hex': prefix.hex(),
        'ime_warning_capture_hex': b''.join(lines[:-1]).hex(),
        'ime_commands': [15, 17],
    }
    return facts, warnings, json.loads(effects)['preedit_stderr']


def _replace_warnings(facts, warnings):
    before = bytes.fromhex(facts['warning_before_hex'])
    facts['ime_warning_capture_hex'] = (
        before + ''.join(json.dumps(row) + '\n' for row in warnings).encode()
    ).hex()


def test_actual90_ime_slice_is_an_exact_observer_positive_only():
    facts, _warnings, stderr = _sample()
    controller.FROZEN._assert_original_ime_publications(facts, stderr)


@pytest.mark.parametrize(
    ('field', 'value'),
    [
        ('line', 624),
        ('line', 625),
        ('operation', 'evaluate'),
        ('command_sequence', '16'),
        ('url', 'qrc:/unrelated/Composer.qml'),
        ('object_available', True),
        ('object_name', 'forged.owner'),
        ('description', 'TypeError: unrelated failure'),
    ],
)
def test_ime_observer_refuses_cold_handler_unrelated_source_and_forged_owner(field, value):
    facts, warnings, stderr = _sample()
    warnings[0][field] = value
    _replace_warnings(facts, warnings)
    with pytest.raises(AssertionError):
        controller.FROZEN._assert_original_ime_publications(facts, stderr)


@pytest.mark.parametrize('escape', ['missing_first', 'missing_second', 'duplicate', 'truncated'])
def test_ime_observer_requires_both_actions_and_no_additional_publication(escape):
    facts, warnings, stderr = _sample()
    if escape == 'missing_first':
        warnings.pop(0)
    elif escape == 'missing_second':
        warnings.pop()
    elif escape == 'duplicate':
        warnings.append(dict(warnings[-1]))
    _replace_warnings(facts, warnings)
    if escape == 'truncated':
        facts['ime_warning_capture_hex'] = bytes.fromhex(facts['ime_warning_capture_hex'])[
            1:
        ].hex()
    with pytest.raises(AssertionError):
        controller.FROZEN._assert_original_ime_publications(facts, stderr)


@pytest.mark.parametrize('escape', ['missing_line', 'extra_line', 'prefix'])
def test_ime_observer_requires_exact_separate_stderr_counterparts(escape):
    facts, _warnings, stderr = _sample()
    if escape == 'missing_line':
        stderr = stderr.splitlines(keepends=True)[0]
    elif escape == 'extra_line':
        stderr += 'TypeError: unrelated independent coding failure\n'
    else:
        stderr = 'unreviewed prefix: ' + stderr
    with pytest.raises(AssertionError):
        controller.FROZEN._assert_original_ime_publications(facts, stderr)
