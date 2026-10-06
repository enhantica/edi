"""gate 3: preserve the frozen inventory and all original assertion code.

Only the exact structure-link fixture adaptation is permitted. The archive stays
unchanged; every other witness remains byte-identical, including moved-from gates.
"""

import hashlib
import importlib.util
import json
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


def expected_blobs(blobs):
    source = ROOT / 'tests/fixtures/c34_t28_baseline/api_witness_adaptation.py'
    spec = importlib.util.spec_from_file_location('witness_adaptation', source)
    adaptation = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adaptation)
    result = dict(blobs)
    result[adaptation.WITNESS] = adaptation.adapted_blob(blobs[adaptation.WITNESS])
    return result


def frozen_blobs():
    reference = ROOT / 'tests/fixtures/e04_t12_public_release/history'
    manifest = json.loads((reference / 'manifest.json').read_text())['api']
    assert manifest, 'the retained frozen API inventory must not be empty'
    with zipfile.ZipFile(reference / 'api.zip') as archive:
        assert set(archive.namelist()) == set(manifest), (
            'the frozen archive must contain its entire inventory'
        )
        blobs = {name: archive.read(name) for name in manifest}
    for name, data in blobs.items():
        assert hashlib.sha256(data).hexdigest() == manifest[name], (
            'each retained frozen API blob must match its independent pin'
        )
    return blobs


def require_frozen(root, blobs):
    for name, contents in expected_blobs(blobs).items():
        path = root / name
        assert path.is_file(), ' I20 the storage move cannot remove a frozen API witness: ' + name
        assert path.read_bytes() == contents, (
            ' I20 each frozen API witness matches its exact retained bytes or fixture adaptation: '
            + name
        )


def test_pre_move_api_witnesses_and_helpers_stay_byte_unchanged():
    require_frozen(ROOT, frozen_blobs())


@pytest.mark.parametrize('damage', ['edit', 'delete', 'rename'])
def test_frozen_gate_cannot_lose_a_witness_by_discovering_only_live_files(tmp_path, damage):
    # Use the real main-tree inventory, not a second list reconstructed from live files.
    blobs = frozen_blobs()
    for name, contents in expected_blobs(blobs).items():
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(contents)
    require_frozen(tmp_path, blobs)
    victim = tmp_path / next(iter(blobs))
    if damage == 'edit':
        victim.write_bytes(victim.read_bytes() + b'\n// changed API witness\n')
    elif damage == 'delete':
        victim.unlink()
    else:
        victim.rename(victim.with_name('renamed_witness.cpp'))
    with pytest.raises(AssertionError, match=r' I20.*frozen API witness'):
        require_frozen(tmp_path, blobs)


@pytest.mark.parametrize('damage', ['predicate', 'message', 'missing-link', 'wrong-link'])
def test_adapted_witness_preserves_assertions_and_its_own_structure_link(tmp_path, damage):
    blobs = frozen_blobs()
    for name, contents in expected_blobs(blobs).items():
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(contents)
    require_frozen(tmp_path, blobs)
    victim = tmp_path / 'tests/unit/cpp/test_c34_t27_geometry_edit_freshness.cpp'
    text = victim.read_text()
    changes = {
        'predicate': ('structure.geometry_current()', 'true'),
        'message': (' fixture stored geometry starts current', ' altered geometry starts current'),
        'missing-link': (
            (
                '    project.experiment().linked_structure().structure_id = '
                'project.structure().name;\n'
            ),
            '',
        ),
        'wrong-link': ('structure_id = project.structure().name', 'structure_id = "ncaf"'),
    }
    before, after = changes[damage]
    assert before in text, 'the escape attempt must reach the retained witness code'
    victim.write_text(text.replace(before, after, 1))
    with pytest.raises(AssertionError, match=r' I20.*frozen API witness'):
        require_frozen(tmp_path, blobs)


@pytest.mark.parametrize('damage', ['predicate', 'message'])
def test_adaptation_receipt_cannot_repin_changed_assertions(tmp_path, monkeypatch, damage):
    source = ROOT / 'tests/fixtures/c34_t28_baseline/api_witness_adaptation.py'
    spec = importlib.util.spec_from_file_location('witness_escape', source)
    adaptation = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adaptation)
    receipt = json.loads((source.parent / 'api_witness_adaptation.json').read_text())
    original = frozen_blobs()[adaptation.WITNESS]
    before, after = {
        'predicate': ('structure.geometry_current()', 'true'),
        'message': (' fixture stored geometry starts current', ' altered geometry starts current'),
    }[damage]
    first = receipt['replacements'][0]
    assert before in first['after'], 'the receipt escape reaches an original assertion'
    first['after'] = first['after'].replace(before, after, 1)
    changed = original.decode()
    for replacement in receipt['replacements']:
        changed = changed.replace(replacement['before'], replacement['after'], 1)
    receipt['adapted_sha256'] = hashlib.sha256(changed.encode()).hexdigest()
    (tmp_path / 'api_witness_adaptation.json').write_text(json.dumps(receipt))
    monkeypatch.setattr(adaptation, 'HERE', tmp_path)
    with pytest.raises(AssertionError, match='every original code token'):
        adaptation.adapted_blob(original)
