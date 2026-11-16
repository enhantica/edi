"""Adding source metadata preserves every original reference and regression byte."""

import copy
import hashlib
import json
import re
import shutil
import zipfile
from pathlib import Path

import pytest
import yaml

from tests.fixtures.metadata_transition import pin_sources as source

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize('name', sorted(source.rows()))
def test_pin_annotation_retains_its_exact_committed_source_document(name, monkeypatch):
    row = source.rows()[name]
    data = (ROOT / name).read_bytes()
    with zipfile.ZipFile(source.HERE / 'pin-sources.zip') as archive:
        before = archive.read(row['before_sha256'])
    assert source.previous_bytes(name, data) == before, (
        'Pin annotation retains its exact committed source document.'
    )
    metadata = json.loads(data)['source']['pins']
    assert metadata == row['metadata'], (
        'Pin annotation retains its exact committed source document.'
    )
    assert metadata['kind'] == 'committed-document', (
        'Pin annotation retains its exact committed source document.'
    )
    assert re.fullmatch(r'[0-9a-f]{40}', metadata['commit']), (
        'Pin annotation retains its exact committed source document.'
    )
    assert metadata['record_sha256'] == hashlib.sha256(before).hexdigest(), (
        'Pin annotation retains its exact committed source document.'
    )
    assert metadata['reason'] and 'no fit rerun' in metadata['reason'], (
        'Pin annotation retains its exact committed source document.'
    )
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


@pytest.mark.parametrize('damage', ['missing', 'empty', 'commit', 'reason', 'values'])
def test_real_case_checker_refuses_incomplete_pin_provenance(tmp_path, damage):
    from tools.checks import case_records  # noqa: PLC0415 - exercise the real producer/checker

    case = 'pd-neut-cwl_lbco-hrpt'
    folder = tmp_path / 'docs/user/cli' / case
    shutil.copytree(ROOT / 'docs/user/cli' / case, folder)
    registry = yaml.safe_load((ROOT / 'docs/user/cli/projects.yml').read_text())
    registry['projects'] = [row for row in registry['projects'] if row['id'] == case]
    (folder.parent / 'projects.yml').write_text(yaml.safe_dump(registry))
    vocabulary = tmp_path / 'app/examples'
    vocabulary.mkdir(parents=True)
    for name in ('metadata.json', 'tags.json'):
        shutil.copyfile(ROOT / 'app/examples' / name, vocabulary / name)
    metadata = json.loads((vocabulary / 'metadata.json').read_text())
    metadata['examples'] = {case: metadata['examples'][case]}
    (vocabulary / 'metadata.json').write_text(json.dumps(metadata))
    assert not any(
        'regression pin provenance' in item for item in case_records.problems(tmp_path)
    ), 'Real case checker refuses incomplete pin provenance.'
    path = folder / 'expected.json'
    expected = json.loads(path.read_text())
    if damage == 'missing':
        del expected['source']['pins']
    elif damage == 'empty':
        expected['source']['pins'] = {}
    elif damage in {'commit', 'reason'}:
        expected['source']['pins'][damage] = ''
    else:
        for quantity in expected['quantities'].values():
            if quantity.get('kind') == 'regression-pin':
                quantity['kind'] = 'reference'
    path.write_text(json.dumps(expected))
    assert f'{case}: has no complete regression pin provenance' in case_records.problems(
        tmp_path
    ), 'Real case checker refuses incomplete pin provenance.'
