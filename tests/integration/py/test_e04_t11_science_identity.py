"""Old catalogue coordinates stay immutable beside independently declared identity."""

import copy
import hashlib
import json
import math
from pathlib import Path

import gemmi
import pytest

from tests.fixtures.table_display.metadata_bytes import pre_catalogue_bytes
from tests.fixtures.web_parallel import science_identity as bridge
from tests.fixtures.web_parallel.numeric import compare_scientific

ROOT = Path(__file__).resolve().parents[3]
CAPTURES = ROOT / 'tests/fixtures/e04_t11_wasm/catalogue_scientific'


def assert_declared_source(project, expected):
    """Same existing catalogue lineage, never the older first-bank token reversal."""
    digest = hashlib.sha256()
    for path in sorted(project.rglob('*')):
        if path.is_file():
            digest.update(path.relative_to(project).as_posix().encode() + b'\0')
            digest.update(pre_catalogue_bytes(path))
    assert digest.hexdigest() == expected, 'Independent declared science input changed'


def declarations(project, documents, expected):
    """Independent existing Gemmi reader; no product resolver/formatter imports."""
    assert_declared_source(project, expected)
    blocks, banks = {}, {}
    for document in documents:
        if document == 'analysis/analysis.edi':
            # Edi's analysis record has no data_ header; parse its single nameless
            # scope in an observer-only wrapper, never infer a bank from its path.
            gemmi.cif.read_string(
                'data_science_observer\n' + (project / document).read_text()
            ).sole_block()
            blocks[document] = ''
            continue
        block = gemmi.cif.read_file(str(project / document)).sole_block()
        blocks[document] = block.name
        if document.startswith('experiments/'):
            banks[document] = (
                block.name,
                tuple(block.find_values('_linked_structure.structure_id')),
            )
    return blocks, banks


def category_reordered(scientific):
    result = {}
    for document, rows in scientific.items():
        categories = {}
        for row in rows:
            categories.setdefault(row[0].partition('.')[0], []).append(list(row))
        result[document] = [row for group in reversed(list(categories.values())) for row in group]
    return result


def capture(case):
    native_path = CAPTURES / f'{case}-native.json'
    conditioning_path = CAPTURES / f'{case}-conditioning.json'
    raw_path = CAPTURES / f'{case}-conditioning-raw.json'
    original = {path: path.read_bytes() for path in (native_path, conditioning_path, raw_path)}
    fixture = json.loads(original[native_path])
    conditioning = json.loads(original[conditioning_path])
    raw = json.loads(original[raw_path])
    assert hashlib.sha256(original[raw_path]).hexdigest() == conditioning['raw_capture_sha256'], (
        'This boundary requires hashlib.sha256(original[raw_path]).hexdigest() == '
        "conditioning['raw_capture_sha256']"
    )
    return fixture, conditioning, raw, original


def assert_domains(fixture, conditioning, blocks):
    mapping = bridge.conditioning_semantics(fixture['scientific'], conditioning, blocks)
    assert set(mapping) == {tuple(binding[:3]) for binding in conditioning['bindings']}, (
        'This boundary requires set(mapping) == {tuple(binding[:3]) for binding in '
        "conditioning['bindings']}"
    )
    domains = bridge.frozen_domains(fixture, blocks)
    raw_coordinates = {tuple(binding[:3]) for binding in fixture['native_precision_bindings']}
    assert {
        key for key, domain in domains.items() if domain == 'native-raw-parameter'
    } == raw_coordinates, (
        'This boundary requires {key for key, domain in domains.items() if domain == '
        "'native-raw-parameter'} == raw_coordinates"
    )
    assert any(domain == 'historical-written' for domain in domains.values()), (
        "This boundary requires any((domain == 'historical-written' for domain in "
        'domains.values()))'
    )


def assert_omitted(raw, banks, index):
    anchors = bridge.omitted_raw_parameters(raw, banks)
    expected_labels = {
        label
        for label in raw['labels']
        if label.rsplit('.', 1)[-1] == 'scale' or label.rsplit('.', 1)[-1].startswith('calib_')
    }
    assert anchors.keys() == expected_labels, (
        'This boundary requires anchors.keys() == expected_labels'
    )
    assert anchors, 'This boundary requires anchors'
    assert all(anchor.key not in index.cells for anchor in anchors.values()), (
        'Old scientific whitelist omitted these raw-anchored roles; do not pretend it covered them'
    )
    for label, anchor in anchors.items():
        assert raw['labels'][anchor.column] == label, (
            "This boundary requires raw['labels'][anchor.column] == label"
        )
        assert anchor.value == raw['values'][anchor.column], (
            "This boundary requires anchor.value == raw['values'][anchor.column]"
        )
        assert anchor.uncertainty == math.sqrt(
            raw['covariance'][anchor.column * len(raw['labels']) + anchor.column]
        ), (
            'This boundary requires anchor.uncertainty == '
            "math.sqrt(raw['covariance'][anchor.column * len(raw['labels']) + "
            'anchor.column])'
        )


@pytest.mark.parametrize('case', ['lbco', 'ncaf'])
def test_frozen_catalogue_coordinates_domains_and_omitted_raw_storage(case):
    fixture, conditioning, raw, original = capture(case)
    scientific = fixture['scientific']
    blocks, banks = declarations(ROOT / fixture['project'], scientific, fixture['project_sha256'])
    frozen_before = copy.deepcopy([fixture, conditioning, raw])
    assert_domains(fixture, conditioning, blocks)
    reordered = category_reordered(scientific)
    aligned = bridge.align_to_frozen(
        reordered, scientific, actual_blocks=blocks, frozen_blocks=blocks
    )
    assert aligned == scientific, (
        'Required: frozen catalogue coordinates domains and omitted raw storage.'
    )
    # Existing bounds and OLD-coordinate conditioning authentication, unchanged.
    assert compare_scientific(aligned, scientific, conditioning=conditioning), (
        'Required: frozen catalogue coordinates domains and omitted raw storage.'
    )
    assert_omitted(raw, banks, bridge.semantic_index(scientific, blocks))
    assert [fixture, conditioning, raw] == frozen_before, (
        'Required: frozen catalogue coordinates domains and omitted raw storage.'
    )
    assert all(path.read_bytes() == data for path, data in original.items()), (
        'Required: frozen catalogue coordinates domains and omitted raw storage.'
    )


def test_declared_input_change_refuses_before_storage_can_be_retargeted(tmp_path):
    project = tmp_path / 'owned-input'
    experiment = project / 'experiments/bank.edi'
    experiment.parent.mkdir(parents=True)
    original = b'data_bank\nloop_\n_data.two_theta\n_data.intensity_meas\n10 100\n'
    experiment.write_bytes(original)
    expected = hashlib.sha256(b'experiments/bank.edi\0' + original).hexdigest()
    assert_declared_source(project, expected)
    experiment.write_bytes(original.replace(b'10 100', b'10 101'))
    with pytest.raises(AssertionError, match='Independent declared science input changed'):
        assert_declared_source(project, expected)
