"""Collection metadata and formula search follow the owner records, independently."""

import copy
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import edi
import pytest

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / 'tests/fixtures/online_popup_contract'
FORMULA = 'Ba0.5 Co La0.5 O3'
ELEMENTS = ['Ba', 'Co', 'La', 'O']
REFERENCE = {
    'authors': 'Smith; Jones',
    'journal': 'Phys. Rev. B',
    'volume': '40',
    'firstpage': '34',
    'year': '2026',
    'doi': '10.5555/edi.fixture.2026.34',
}


def base_document():
    return {
        'schema': 'edi-data-index/1',
        'entries': [
            {
                'id': 'witness',
                'kind': 'structure',
                'name': 'Independent P1 occupancy witness',
                'formula': FORMULA,
                'elements': ELEMENTS,
                'files': [{'path': 'structures/witness.cif', 'format': 'cif'}],
            }
        ],
    }


@pytest.mark.parametrize('present', [False, True])
@pytest.mark.parametrize('interface', ['python', 'cli'])
def test_optional_publication_fields_survive_index_reads(tmp_path, present, interface):
    value = base_document()
    if present:
        value['entries'][0].update(REFERENCE)
    (tmp_path / 'index.json').write_text(json.dumps(value))
    if interface == 'python':
        entry = edi.load_collection(tmp_path).find('witness')
    else:
        result = subprocess.run(
            [
                sys.executable,
                '-m',
                'edi',
                'collection',
                '--source',
                str(tmp_path),
                'find',
                'witness',
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, (
            'Optional reference metadata must remain readable by the CLI'
        )
        entry = json.loads(result.stdout)
    assert entry['id'] == 'witness', (
        'An entry remains readable with or without publication metadata'
    )
    if present:
        assert {key: entry.get(key) for key in REFERENCE} == REFERENCE, (
            'Every optional publication field survives the shared reader and Python/CLI mapping'
        )
    else:
        assert all(entry.get(key) in {None, ''} for key in REFERENCE), (
            'An entry without publication metadata leaves the reference fields empty'
        )


@pytest.mark.parametrize('kind', ['structure', 'experiment', 'data', 'project'])
@pytest.mark.parametrize('query', ['LaCoO3', 'La Co O3', 'O3 Co La'])
def test_collection_formula_matches_elements_and_ranks_exact_first(kind, query):
    collection = edi.load_collection((FIXTURE / 'formula_index.json').read_text())
    found = collection.search(kind, formula=query)
    assert [entry['id'] for entry in found] == [kind + '-zzz-exact', kind + '-aaa-substituted'], (
        'Formula search ignores amounts and excludes missing elements; '
        'exact Hill matches come first'
    )


def producer():
    spec = importlib.util.spec_from_file_location(
        'independent_collection_producer', ROOT / 'tools/data/build_collection.py'
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope='module')
def generated(tmp_path_factory):
    root = tmp_path_factory.mktemp('formula-corpus')
    outputs = {}
    for declaration in (False, True):
        case = root / str(declaration)
        project = case / 'examples/witness/project'
        shutil.copytree(ROOT / 'docs/user/cli/pd-neut-cwl_lbco-hrpt/project', project)
        text = (FIXTURE / 'occupancy.cif').read_text()
        if declaration:
            text += "\n_chemical_formula_sum 'La Co O3'\n"
        tutorials = case / 'tutorials'
        tutorials.mkdir()
        (tutorials / 'lbco.cif').write_text(text)
        (tutorials / 'hrpt.xye').write_text('21.5 117.25 0.75\n22.75 131.75 1.25\n')
        metadata = case / 'metadata.json'
        metadata.write_text(
            json.dumps({
                'examples': {
                    'witness': {
                        'samples': ['This name is not the sample formula'],
                        'values': {'probe': ['neutron']},
                    }
                }
            })
        )
        module = producer()
        module.EXAMPLES = case / 'examples'
        module.METADATA = metadata
        module.TUTORIAL_FILES = tutorials
        output = case / 'collection'
        assert module.populate(output) == 0, (
            'The actual producer accepts the independent input corpus'
        )
        assert module.index(output) == 0, (
            'The actual producer indexes every independently supplied kind'
        )
        outputs[declaration] = (output, json.loads((output / 'index.json').read_text()))
    return outputs


@pytest.mark.parametrize('declared', [False, True], ids=['occupancies', 'formula-sum'])
@pytest.mark.parametrize('kind', ['structure', 'experiment', 'data', 'project'])
def test_every_generated_kind_carries_its_sample_formula_and_elements(generated, declared, kind):
    _, value = generated[declared]
    rows = [entry for entry in value['entries'] if entry['kind'] == kind]
    assert rows, 'The producer corpus actually exercises every owner-declared collection kind'
    assert all(
        entry.get('formula')
        == ('Co La O3' if declared and entry['id'].startswith('tutorial-') else FORMULA)
        and entry.get('elements')
        == (['Co', 'La', 'O'] if declared and entry['id'].startswith('tutorial-') else ELEMENTS)
        for entry in rows
    ), 'Every entry derives formula and elements from sample files rather than its display name'


def check(folder):
    return subprocess.run(
        [sys.executable, str(ROOT / 'tools/data/build_collection.py'), 'check', str(folder)],
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize('missing', ['formula', 'elements', 'both'])
def test_check_refuses_missing_composition_when_files_define_a_structure(tmp_path, missing):
    target = tmp_path / 'structures/witness.cif'
    target.parent.mkdir()
    target.write_bytes((FIXTURE / 'occupancy.cif').read_bytes())
    value = base_document()
    file = value['entries'][0]['files'][0]
    file.update(
        sha256=hashlib.sha256(target.read_bytes()).hexdigest(), bytes=target.stat().st_size
    )
    index = tmp_path / 'index.json'
    index.write_text(json.dumps(value))
    assert check(tmp_path).returncode == 0, (
        'The independently complete composition is a valid check control'
    )
    damaged = copy.deepcopy(value)
    for field in ('formula', 'elements') if missing == 'both' else (missing,):
        damaged['entries'][0].pop(field)
    index.write_text(json.dumps(damaged))
    result = check(tmp_path)
    assert result.returncode != 0 and 'Traceback' not in result.stderr, (
        'Check cleanly refuses absent formula or elements when the entry files define a structure'
    )


@pytest.mark.parametrize('present', [False, True])
def test_reference_sidecars_survive_the_actual_index_generator(tmp_path, present):
    file = tmp_path / 'structures/witness.cif'
    file.parent.mkdir()
    shutil.copyfile(FIXTURE / 'occupancy.cif', file)
    metadata = {'id': 'witness', 'formula': FORMULA, 'elements': ELEMENTS}
    if present:
        metadata.update(REFERENCE)
    file.with_name(file.name + '.meta.json').write_text(json.dumps(metadata))
    assert producer().index(tmp_path) == 0, (
        'The actual generator accepts optional publication metadata'
    )
    entry = json.loads((tmp_path / 'index.json').read_text())['entries'][0]
    expected = REFERENCE if present else dict.fromkeys(REFERENCE)
    assert {key: entry.get(key) for key in REFERENCE} == expected, (
        'Index generation retains optional reference fields and leaves absent metadata empty'
    )
    assert check(tmp_path).returncode == 0, 'The generated optional-reference index remains valid'


def test_committed_collection_fixture_carries_composition_for_every_kind():
    value = json.loads(
        (ROOT / 'tests/fixtures/online_sources/easydiffraction/index.json').read_text()
    )
    assert {entry['kind'] for entry in value['entries']} == {
        'structure',
        'experiment',
        'data',
        'project',
    }, 'The committed composition witness actually covers all four collection kinds'
    assert all(
        entry.get('formula') == FORMULA and entry.get('elements') == ELEMENTS
        for entry in value['entries']
    ), 'Every LBCO fixture entry carries the sample formula and Hill-ordered elements'
