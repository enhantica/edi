"""red-first gates for edi consuming crysta's general structural Jacobian."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / 'tests/fixtures/c09_t12_silicon_fit'
ORACLE_PATH = FIXTURE / 'oracle.json'
ORACLE_SOURCE = FIXTURE / 'direct_crysta_oracle.cpp'
SILICON_STRUCTURE = ROOT / 'tests/fixtures/c12_t3_space_group_code/si_origin_2.edi'


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _oracle() -> dict[str, Any]:
    return json.loads(ORACLE_PATH.read_text(encoding='utf-8'))


def test_c09_t12_round_trip_fixture_is_locked_to_independent_biso_reference() -> None:
    oracle = _oracle()
    assert oracle['schema'] == 1
    assert oracle['provenance'] == {
        'crysta_commit': '296e3ff2f17e9302c56141f80c7d279205a5eac6',
        'generator': 'direct_crysta_oracle.cpp',
        'generator_sha256': _sha256(ORACLE_SOURCE),
        'role': "crysta round-trip oracle, independent of edi's fit path",
        'independent_reference': {
            'engine': 'easydiffraction v0.19.1+dev12',
            'commit': '39ada82c8aef8b4657c4ae8c68e888668db0f38e',
            'project': 'refine-si-sepd',
            'saved_b_iso': '0.5315(43) A^2',
        },
    }, ' oracle provenance must stay anchored to merged crysta history'
    assert oracle['silicon'] == {
        'space_group': 'F d -3 m',
        'coord_system_code': '2',
        'cell_a_angstrom': 5.431,
        'site': ['Si1', 'Si', 'a', 0.125, 0.125, 0.125],
        'target_b_iso_angstrom2': 0.5315,
        'neutron_b_c_fm': 4.1491,
        'structure_sha256': _sha256(SILICON_STRUCTURE),
    }
    assert len(oracle['grid']) == len(oracle['observed']) == 257
    assert all(value >= 0.0 for value in oracle['observed'])
    assert any(value > 0.0 for value in oracle['observed'])
