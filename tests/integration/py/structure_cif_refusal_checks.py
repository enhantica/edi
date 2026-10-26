"""Every deferred CIF entrance reports the same plain reason."""

import pytest


def reason(message):
    assert message.count('Reading CIF files is not supported yet') == 1, (
        'Each main-unsupported CIF entrance gives the shared plain refusal reason once: ' + message
    )


def main_values(structure):
    assert [getattr(structure.cell, 'length_' + axis).value for axis in 'abc'] == pytest.approx([
        5.1234,
        6.2345,
        7.3456,
    ]), 'Main already imports all three nontrivial CIF cell lengths'
    assert len(structure.atom_sites) == 1, 'Main already imports the authored CIF atom row'
    site = structure.atom_sites[0]
    assert [getattr(site, 'fract_' + axis).value for axis in 'xyz'] == pytest.approx([
        0.173,
        0.281,
        0.397,
    ]), 'Main already imports the CIF fractional coordinates without changing convention'
    assert site.occupancy.value == pytest.approx(0.63), (
        'Main already imports the non-unit CIF occupancy'
    )
    assert site.adp_iso.value == pytest.approx(0.47), (
        'Main already imports the declared isotropic B value in its original convention'
    )
