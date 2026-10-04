"""gate 3: committed pre-move API witnesses remain byte-identical.

No T7 exception is named after review 3, including edi's moved-from project gate.
The inventory comes from the frozen tree, so deleting a witness cannot hide it.
"""

import hashlib
import json
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


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
    for name, contents in blobs.items():
        path = root / name
        assert path.is_file(), ' I20 the storage move cannot remove a frozen API witness: ' + name
        assert path.read_bytes() == contents, (
            ' I20 every frozen API witness and helper stays byte-identical: ' + name
        )


def test_pre_move_api_witnesses_and_helpers_stay_byte_unchanged():
    require_frozen(ROOT, frozen_blobs())


@pytest.mark.parametrize('damage', ['edit', 'delete', 'rename'])
def test_frozen_gate_cannot_lose_a_witness_by_discovering_only_live_files(tmp_path, damage):
    # Use the real main-tree inventory, not a second list reconstructed from live files.
    blobs = frozen_blobs()
    for name, contents in blobs.items():
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
