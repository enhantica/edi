"""Lossless JSON capture boundaries; no Main/Qt/SDK operation is performed here."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import test_e11_t5_usage_account_original_controls as recorder


@pytest.mark.parametrize(
    'wire',
    [
        r'{"value":"plain"}',
        r'{"value":"\u03b2"}',
        r'{"value":"\ud801\udc28"}',
        r'{"value":"\ud83e\uddea"}',
        r'{"value":"\ud801"}',
        r'{"value":"\ud83e"}',
        r'{"value":"\udc00"}',
        r'{"\ud801":{"values":["A\ud83eB","C\udc00D","\ud801\udc28","\"\\\n\t\u0000"]}}',
    ],
    ids=['ascii', 'bmp', 'deseret', 'emoji', 'high-deseret', 'high-emoji', 'low', 'nested-mixed'],
)
def test_capture_preserves_parsed_json_value_and_strict_utf8_bytes(tmp_path, wire):
    value = json.loads(wire)
    saved = copy.deepcopy(value)
    assert recorder._retain(SimpleNamespace(folder=tmp_path), 'sample', value) is value
    text = (tmp_path / 'sample.json').read_bytes().decode('utf-8', errors='strict')
    assert json.loads(text) == saved
    assert value == saved


def test_capture_does_not_truncate_prior_receipt_when_serialization_refuses(tmp_path):
    path = tmp_path / 'sample.json'
    previous = b'{"previous":"actual receipt"}\n'
    path.write_bytes(previous)
    with pytest.raises(TypeError):
        recorder._retain(SimpleNamespace(folder=tmp_path), 'sample', {'unserializable': object()})
    assert path.read_bytes() == previous


def test_capture_propagates_actual_io_failure_without_synthetic_receipt(tmp_path):
    path = tmp_path / 'sample.json'
    path.mkdir()
    with pytest.raises(OSError, match=r'sample\.json'):
        recorder._retain(SimpleNamespace(folder=tmp_path), 'sample', {'valid': 'value'})
    assert path.is_dir() and list(path.iterdir()) == []


def test_capture_refuses_actual_short_write_and_preserves_partial_evidence(tmp_path, monkeypatch):
    original_write = Path.write_bytes

    writes = []

    def short_write(path, data):
        written = original_write(path, data[:5])
        writes.append({'requested': len(data), 'written': written, 'prefix': data[:5]})
        return written

    monkeypatch.setattr(Path, 'write_bytes', short_write)
    with pytest.raises(OSError, match='not fully written'):
        recorder._retain(SimpleNamespace(folder=tmp_path), 'sample', {'valid': 'value'})
    assert len(writes) == 1 and writes[0]['requested'] > writes[0]['written']
    assert writes[0]['written'] == 5
    assert (tmp_path / 'sample.json').read_bytes() == writes[0]['prefix']
