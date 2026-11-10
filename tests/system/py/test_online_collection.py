"""The collection contract comes from the design note and committed file bytes."""

import copy
import hashlib
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path

import edi
import pytest

from tests.integration.app.online_load_host import run_online_host

ROOT = Path(__file__).resolve().parents[3]
COLLECTION = ROOT / 'tests/fixtures/online_sources/easydiffraction'


@pytest.fixture(scope='module')
def online_host(tmp_path_factory):
    with run_online_host(
        tmp_path_factory.mktemp('collection-host'),
        load_groups_only=True,
        offline_http=True,
        failure_entries=False,
    ) as host:
        yield host


@pytest.mark.parametrize('entry_id', ['lbco', 'lbco-hrpt', 'lbco-hrpt-xye'])
def test_same_index_entry_in_app_cli_python(online_host, entry_id):
    expected = next(
        row
        for row in json.loads((COLLECTION / 'index.json').read_text())['entries']
        if row['id'] == entry_id
    )
    actual = edi.load_collection(COLLECTION).find(entry_id)
    answer = subprocess.run(
        [sys.executable, '-m', 'edi', 'collection', '--source', str(COLLECTION), 'find', entry_id],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert answer.returncode == 0, 'The CLI must find the same committed collection id'
    cli = json.loads(answer.stdout)
    for key, value in expected.items():
        assert actual[key] == value and cli[key] == value, (
            'App, CLI and Python metadata must equal the independently authored index'
        )
    online_host.check('collection_entry', entry_id)


def test_examples_loads_collection_archive(online_host):
    online_host.check('collection_examples')


@pytest.mark.parametrize('route', ['search', 'download', 'index'])
@pytest.mark.parametrize(
    'response', [*map(str, range(500, 600)), 'error-401', 'error-499', 'error-102', 'error-199']
)
def test_outage_class_offers_alternative(online_host, route, response):
    online_host.check('outage_class', route + '-' + response)


@pytest.mark.parametrize('generated', [False, True])
def test_fixture_index_matches_documented_schema_and_files(tmp_path, generated):
    # edi-online-data-collection.md, Schema edi-data-index/1; independent of the generator.
    collection = COLLECTION
    if generated:
        shutil.copytree(COLLECTION, tmp_path / 'collection')
        collection = tmp_path / 'collection'
        (collection / 'index.json').unlink()
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / 'tools/data/build_collection.py'),
                'index',
                str(collection),
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        assert result.returncode == 0, 'The generator must index the independent fixture files'
    document = json.loads((collection / 'index.json').read_text())
    assert document['schema'] == 'edi-data-index/1', (
        'The collection uses the documented schema version'
    )
    ids = set()
    kinds = set()
    for entry in document['entries']:
        assert entry['id'] and entry['id'] not in ids, 'Collection ids must be nonempty and unique'
        ids.add(entry['id'])
        kinds.add(entry['kind'])
        assert entry['kind'] in {'structure', 'experiment', 'data', 'project'}, (
            'Only the four documented entry kinds are accepted'
        )
        assert entry['files'], 'Every entry must supply at least one file'
        if 'cell' in entry:
            assert len(entry['cell']) == 6 and all(math.isfinite(x) for x in entry['cell']), (
                'A documented cell has six finite numbers'
            )
        for file in entry['files']:
            path = Path(file['path'])
            assert not path.is_absolute() and '..' not in path.parts, (
                'Collection files stay under their static mirror root'
            )
            payload = (collection / path).read_bytes()
            assert file['bytes'] == len(payload), (
                'The mirror size is independently measured from the stored file'
            )
            assert file['sha256'] == hashlib.sha256(payload).hexdigest(), (
                'The mirror hash is independently computed from the stored file'
            )
    assert kinds == {'structure', 'experiment', 'data', 'project'}, (
        'The shared fixture exercises all documented kinds'
    )


def invalid_document(case):
    doc = copy.deepcopy(json.loads((COLLECTION / 'index.json').read_text()))
    entry = doc['entries'][0]
    if case.startswith('bytes:'):
        entry['files'][0]['bytes'] = json.loads(case.split(':', 1)[1])
    elif case == 'schema':
        doc['schema'] = 'edi-data-index/999'
    elif case == 'kind':
        entry['kind'] = 'unknown'
    elif case == 'duplicate':
        doc['entries'].append(copy.deepcopy(entry))
    elif case == 'absolute':
        entry['files'][0]['path'] = '/escaped.cif'
    elif case == 'parent':
        entry['files'][0]['path'] = '../escaped.cif'
    elif case == 'cell-short':
        entry['cell'] = [1, 2, 3]
    elif case == 'cell-type':
        entry['cell'] = [1, 2, 3, 90, 90, 'bad']
    elif case == 'no-files':
        entry['files'] = []
    return json.dumps(doc)


@pytest.mark.parametrize(
    'case',
    [
        'bytes:1e30',
        'bytes:1e100',
        'bytes:9223372036854775808',
        'bytes:9007199254740994',  # Regression pin for the chosen 2**53 size ceiling.
        'bytes:-1',
        'bytes:12.5',
        'schema',
        'kind',
        'duplicate',
        'absolute',
        'parent',
        'cell-short',
        'cell-type',
        'no-files',
    ],
)
def test_malformed_index_is_refused_cleanly(case, tmp_path, online_host):
    online_host.check('malformed_index', case)
    text = invalid_document(case)
    with pytest.raises((ValueError, RuntimeError)):
        edi.load_collection(text)
    (tmp_path / 'index.json').write_text(text)
    result = subprocess.run(
        [sys.executable, '-m', 'edi', 'collection', '--source', str(tmp_path), 'list'],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode > 0, (
        'Malformed remote indexes must fail cleanly without a signal or success'
    )
    assert result.stderr and not result.stdout, (
        'A refused index must report a reason and publish no partial entries'
    )


@pytest.mark.parametrize('size', [0, 12, 9007199254740992])
def test_representable_index_size_remains_exact(size):
    document = json.loads((COLLECTION / 'index.json').read_text())
    document['entries'][0]['files'][0]['bytes'] = size
    entry = edi.load_collection(json.dumps(document)).find('lbco')
    assert entry['files'][0]['bytes'] == size, (
        'Representable whole file sizes must survive the shared reader exactly'
    )
