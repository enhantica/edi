"""Documented JSON types, portable paths and exact file-byte invariants."""

import copy
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import edi
import pytest

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / 'tests/fixtures/online_sources/easydiffraction'
PAYLOAD = (SOURCE / 'structures/lbco.cif').read_bytes()


def document():
    return {
        'schema': 'edi-data-index/1',
        'entries': [
            {
                'id': 'witness',
                'kind': 'structure',
                'name': 'Independent witness',
                'files': [
                    {
                        'path': 'structures/witness.cif',
                        'format': 'cif',
                        'sha256': hashlib.sha256(PAYLOAD).hexdigest(),
                        'bytes': len(PAYLOAD),
                    }
                ],
            }
        ],
    }


def checked(tmp_path, value, path='structures/witness.cif'):
    root = tmp_path / 'collection'
    root.mkdir(exist_ok=True)
    file = root / path
    if file.resolve().is_relative_to(tmp_path.resolve()):
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(PAYLOAD)
    (root / 'index.json').write_text(json.dumps(value))
    return subprocess.run(
        [sys.executable, str(ROOT / 'tools/data/build_collection.py'), 'check', str(root)],
        text=True,
        capture_output=True,
        timeout=10,
        check=False,
    )


STRING_FIELDS = (
    'id',
    'kind',
    'name',
    'description',
    'formula',
    'space_group',
    'radiation',
    'technique',
    'instrument',
    'facility',
    'source',
)
CASES = [
    *(f'{key}:{kind}' for key in STRING_FIELDS for kind in ('number', 'array')),
    'missing-entries',
    'entries-object',
    'entry-array',
    'missing-id',
    'missing-kind',
    'missing-files',
    'files-object',
    'file-array',
    'missing-path',
    'missing-format',
    'format-number',
    'path-number',
    'sha256-number',
    'sha256-invalid',
    'bytes-string',
    'bytes-bool',
    'bytes-fraction',
    'elements-object',
    'element-number',
    'element-invalid',
    'cell-object',
    'cell-string',
    'cell-bool',
    'cell-nonfinite',
    'formula-partial',
]


MISSING = object()


def malformed(case):
    value = document()
    if ':' in case:
        key, kind = case.split(':')
        value['entries'][0][key] = 7 if kind == 'number' else []
        return value
    entry = ('entries', 0)
    file = (*entry, 'files', 0)
    changes = {
        'missing-entries': (('entries',), MISSING),
        'entries-object': (('entries',), {}),
        'entry-array': (('entries',), [[]]),
        'missing-id': ((*entry, 'id'), MISSING),
        'missing-kind': ((*entry, 'kind'), MISSING),
        'missing-files': ((*entry, 'files'), MISSING),
        'files-object': ((*entry, 'files'), {}),
        'file-array': ((*entry, 'files'), [[]]),
        'missing-path': ((*file, 'path'), MISSING),
        'missing-format': ((*file, 'format'), MISSING),
        'format-number': ((*file, 'format'), 7),
        'path-number': ((*file, 'path'), 7),
        'sha256-number': ((*file, 'sha256'), 7),
        'sha256-invalid': ((*file, 'sha256'), 'not-a-digest'),
        'bytes-string': ((*file, 'bytes'), str(len(PAYLOAD))),
        'bytes-bool': ((*file, 'bytes'), True),
        'bytes-fraction': ((*file, 'bytes'), 12.5),
        'elements-object': ((*entry, 'elements'), {}),
        'element-number': ((*entry, 'elements'), [7]),
        'element-invalid': ((*entry, 'elements'), ['not-an-element']),
        'cell-object': ((*entry, 'cell'), {}),
        'cell-string': ((*entry, 'cell'), [3.77, 3.77, 3.77, 90, 90, 'bad']),
        'cell-bool': ((*entry, 'cell'), [3.77, 3.77, 3.77, 90, 90, True]),
        'cell-nonfinite': ((*entry, 'cell'), [3.77, 3.77, 3.77, 90, 90, float('inf')]),
        'formula-partial': ((*entry, 'formula'), 'C1.2.3'),
    }
    path, replacement = changes[case]
    target = value
    for part in path[:-1]:
        target = target[part]
    if replacement is MISSING:
        del target[path[-1]]
    else:
        target[path[-1]] = copy.deepcopy(replacement)
    return value


@pytest.mark.parametrize('case', CASES)
def test_checker_and_shared_reader_refuse_invalid_schema(tmp_path, case):
    value = malformed(case)
    errors = []
    try:
        edi.load_collection(json.dumps(value))
    except (ValueError, RuntimeError):
        pass
    else:
        errors.append('reader accepted')
    result = checked(tmp_path, value)
    if result.returncode == 0:
        errors.append('check accepted')
    if 'Traceback' in result.stderr:
        errors.append('check raised instead of clean refusal')
    assert not errors, (
        'Every malformed documented field must be refused cleanly by reader and check: '
        + repr(errors)
    )


BAD_PATHS = [
    'C:/outside.cif',
    r'C:\outside.cif',
    r'..\outside.cif',
    r'structures\..\outside.cif',
    '../outside.cif',
    '/outside.cif',
    'structures/../../outside.cif',
    'file:outside.cif',
    'https:outside.cif',
    '//host/outside.cif',
    '%2e%2e/outside.cif',
    'structures/%2E%2E/outside.cif',
    'structures/%2foutside.cif',
    'structures/%5coutside.cif',
    'structures/..%2foutside.cif',
    '%252e%252e/outside.cif',
]


@pytest.mark.parametrize('path', BAD_PATHS)
def test_portable_path_is_refused_before_actual_fetch(tmp_path, monkeypatch, path):
    value = document()
    file = value['entries'][0]['files'][0]
    file['path'] = path
    file.pop('sha256')
    file.pop('bytes')
    requests = []

    def read(path):
        url = path.as_posix()
        requests.append(url)
        return json.dumps(value).encode() if url.endswith('/index.json') else PAYLOAD

    monkeypatch.setattr(Path, 'read_bytes', read)
    refused = False
    try:
        edi.load_collection('/injected-collection').fetch('witness', tmp_path / 'output')
    except (ValueError, RuntimeError):
        refused = True
    assert refused and requests == ['/injected-collection/index.json'], (
        'A portable-path violation must be refused before any file transport or output write'
    )
    assert not (tmp_path / 'output').exists(), 'An escaping collection path must publish no output'


@pytest.mark.parametrize('path', BAD_PATHS)
def test_generator_check_refuses_existing_escaping_paths(tmp_path, path):
    value = document()
    value['entries'][0]['files'][0]['path'] = path
    result = checked(tmp_path, value, path)
    assert result.returncode != 0 and 'Traceback' not in result.stderr, (
        'The distributable collection check must refuse portable path escapes cleanly'
    )


@pytest.mark.parametrize('path', ['structures/nested/witness.cif', 'nested/witness.cif'])
def test_valid_nested_relative_path_remains_usable(tmp_path, path):
    value = document()
    value['entries'][0]['files'][0]['path'] = path
    assert edi.load_collection(json.dumps(value)).find('witness')['files'][0]['path'] == path, (
        'Valid nested relative URL paths must retain their spelling'
    )
    assert checked(tmp_path, value, path).returncode == 0, (
        'The checker must accept valid nested paths'
    )


@pytest.mark.parametrize('interface', ['python', 'cli'])
@pytest.mark.parametrize('kind', ['structure', 'experiment', 'data', 'project'])
@pytest.mark.parametrize('claim', ['digest', 'size', 'absent'])
def test_python_and_cli_verify_exact_download_bytes(tmp_path, kind, claim, interface):
    root = tmp_path / 'collection'
    shutil.copytree(SOURCE, root)
    value = json.loads((root / 'index.json').read_text())
    entry = next(e for e in value['entries'] if e['kind'] == kind)
    file = entry['files'][0]
    if claim == 'digest':
        file['sha256'] = '0' * 64
    elif claim == 'size':
        file['bytes'] = len((root / file['path']).read_bytes()) + 1
    else:
        file.pop('sha256', None)
        file.pop('bytes', None)
    (root / 'index.json').write_text(json.dumps(value))
    collection = edi.load_collection(root)
    python_into = tmp_path / 'python-output'
    cli_into = tmp_path / 'cli-output'
    if interface == 'python':
        if claim == 'absent':
            fetched = collection.fetch(entry['id'], python_into)
            assert fetched.read_bytes() == (root / file['path']).read_bytes(), (
                'Absent optional claims preserve exact ordinary downloads'
            )
        else:
            with pytest.raises((ValueError, RuntimeError)):
                collection.fetch(entry['id'], python_into)
            assert not python_into.exists(), 'A refused Python download must publish no file'
        return
    result = subprocess.run(
        [
            sys.executable,
            '-m',
            'edi',
            'collection',
            '--source',
            str(root),
            'fetch',
            entry['id'],
            '--into',
            str(cli_into),
        ],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert (result.returncode == 0) == (claim == 'absent'), (
        'CLI fetch must enforce the same exact-byte claims as Python'
    )
    if claim != 'absent':
        assert not cli_into.exists(), 'A refused CLI download must publish no file'


@pytest.mark.parametrize(
    ('formula', 'expected'),
    [
        ('H2 C O', 'C H2 O'),
        ('O3 Ba0.5 Co La0.5', 'Ba0.5 Co La0.5 O3'),
        ('C1.25 H2.5', 'C1.25 H2.5'),
    ],
)
def test_valid_fractional_formula_has_defined_hill_order(formula, expected):
    value = document()
    value['entries'][0]['formula'] = formula
    assert edi.load_collection(json.dumps(value)).find('witness')['formula'] == expected, (
        'Hill notation orders C then H then other symbols and consumes each valid decimal count'
    )


@pytest.mark.parametrize('interface', ['index-python', 'search-python', 'cli'])
@pytest.mark.parametrize('formula', ['C1.2.3', 'C..2', 'C2..', 'C0.5.25H2'])
def test_formula_count_requires_complete_numeric_token(formula, interface, tmp_path):
    value = document()
    value['entries'][0]['formula'] = formula
    if interface == 'index-python':
        with pytest.raises((ValueError, RuntimeError)):
            edi.load_collection(json.dumps(value))
    elif interface == 'search-python':
        value['entries'][0]['formula'] = 'C1.2'
        with pytest.raises((ValueError, RuntimeError)):
            edi.load_collection(json.dumps(value)).search('structure', formula=formula)
    else:
        (tmp_path / 'index.json').write_text(json.dumps(value))
        result = subprocess.run(
            [sys.executable, '-m', 'edi', 'collection', '--source', str(tmp_path), 'list'],
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
        )
        assert result.returncode > 0 and not result.stdout, (
            'CLI index reads must refuse every partially consumed decimal count '
            'without publishing entries'
        )


@pytest.fixture(scope='module')
def populated_collection(tmp_path_factory):
    root = tmp_path_factory.mktemp('populated-index')
    for action in ('populate', 'index'):
        result = subprocess.run(
            [sys.executable, str(ROOT / 'tools/data/build_collection.py'), action, str(root)],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        assert result.returncode == 0, (
            'The visible collection producer must build its normal saved-project corpus'
        )
    return root


def test_populated_output_is_accepted_by_reader_and_check(populated_collection):
    root = populated_collection
    expected = json.loads((root / 'index.json').read_text())['entries']
    actual = edi.load_collection(root).entries
    assert [e['id'] for e in actual] == [e['id'] for e in expected], (
        'The reader must preserve every id in the normally populated collection'
    )
    result = subprocess.run(
        [sys.executable, str(ROOT / 'tools/data/build_collection.py'), 'check', str(root)],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, 'The distributable check must accept its valid populated output'
