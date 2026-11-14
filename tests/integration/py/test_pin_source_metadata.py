"""Adding source metadata preserves every original reference and regression byte."""

import copy
import hashlib
import json
import re
import zipfile
from pathlib import Path

import pytest

from tests.fixtures.metadata_transition import pin_sources as source

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize('name', sorted(source.rows()))
def test_pin_annotation_retains_its_exact_committed_source_document(name, monkeypatch):
    row = source.rows()[name]
    data = (ROOT / name).read_bytes()
    with zipfile.ZipFile(source.HERE / 'pin-sources.zip') as archive:
        before = archive.read(row['before_sha256'])
    assert source.previous_bytes(name, data) == before
    metadata = json.loads(data)['source']['pins']
    assert metadata == row['metadata']
    assert metadata['kind'] == 'committed-document'
    assert re.fullmatch(r'[0-9a-f]{40}', metadata['commit'])
    assert metadata['record_sha256'] == hashlib.sha256(before).hexdigest()
    assert metadata['reason'] and 'no fit rerun' in metadata['reason']
    for damaged in (data[:-1], data + b'\n', data.replace(b'"commit"', b'"foreign"', 1)):
        with pytest.raises(AssertionError, match='every committed source byte'):
            source.previous_bytes(name, damaged)
    document = json.loads(data)
    quantities = document.get('calc', document)['quantities']
    for field in ('value', 'kind', 'tol_abs', 'tol_rel'):
        altered = copy.deepcopy(document)
        altered.get('calc', altered)['quantities'][next(iter(quantities))][field] = 'foreign'
        raw = (json.dumps(altered, indent=2, ensure_ascii=False) + '\n').encode()
        rows = {**source.rows(), name: {**row, 'after_sha256': hashlib.sha256(raw).hexdigest()}}
        with monkeypatch.context() as patch:
            patch.setattr(source, 'rows', lambda rows=rows: rows)
            with pytest.raises(AssertionError):
                source.previous_bytes(name, raw)
