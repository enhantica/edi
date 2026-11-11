"""The public absorption model exposes only its active cylinder coefficient."""

import json
from pathlib import Path

import edi

ROOT = Path(__file__).resolve().parents[3]


def test_removed_absorption_coefficient_has_no_public_member_or_parameter_entry():
    assert not hasattr(edi.CylinderHewatAbsorption, 'abscor2'), (
        'The removed second absorption coefficient must not exist in the public Python API'
    )
    surface = json.loads((ROOT / 'data/python-surface.json').read_text())['public']
    assert all('abscor2' not in row.get('members', []) for row in surface.values()), (
        'The Python surface and parameter list must contain no removed absorption coefficient'
    )
