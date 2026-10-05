"""Agreement with the owner-supplied two-phase FullProf run."""

import json
from pathlib import Path

import edi
import numpy as np
import pytest

from tests.fixtures.multiphase import fullprof

ROOT = Path(__file__).resolve().parents[3]


def test_fullprof_reference_retains_every_non_asymmetry_parameter_and_occupancy():
    ref = fullprof.reference()
    assert len(ref['parameters']) == 52, (
        'All fitted FullProf parameters except the four inexact asymmetry coefficients '
        'need expectations'
    )
    assert ref['parameters']['Al2O3.Al1.adp_iso'] == [-0.143, 0.301], (
        'The negative-Biso treatment uses the re-fitted summary and its own uncertainty'
    )
    provenance = (fullprof.HOME / 'PROVENANCE.md').read_text()
    assert 'Owner-supplied' in provenance, (
        'YAP agreement must identify the owner-supplied reference origin'
    )
    for digest in ref['digests'].values():
        assert digest in provenance, (
            'Each external FullProf artifact must retain its recorded digest'
        )
    wyckoff = json.loads((ROOT / 'tests/fixtures/c34_t25_fullprof/wyckoff.json').read_text())[
        'groups'
    ]
    pcr = (fullprof.HOME / 'yap_3k.pcr').read_text()
    sections = pcr.split('!Atom')[1:]
    for (_phase, sites), part, group in zip(
        fullprof.SITES.items(), sections, ('Pbnm', 'R-3c:H'), strict=True
    ):
        table = wyckoff[group]
        for site, (letter, multiplicity) in sites.items():
            entry = next(row for row in table['wyckoff'] if row['letter'] == letter)
            assert entry['multiplicity'] == multiplicity, (
                'Every phase site needs the independent cctbx multiplicity'
            )
            row = next(
                line.split()
                for line in part.splitlines()
                if line.split() and line.split()[0] == site
            )
            occupancy = float(row[6]) * table['general'] / multiplicity
            assert occupancy == pytest.approx(1, abs=1.1e-5), (
                'FullProf occupancy must be undone site by site before engine loading'
            )


def test_yalo3_single_phase_control_calculates_from_the_external_structure(tmp_path):
    p = edi.Project.load(fullprof.write_control(tmp_path / 'control'))
    p.analysis.calculate()
    values = np.asarray(p.experiments[0].data.intensity_calc)
    assert values.size > 100 and np.isfinite(values).all() and np.any(values > 0), (
        'The independent YAlO3-only control must calculate a real finite diffraction pattern'
    )
    assert p.structure.cell.length_a.value == 5.17242, (
        'The YAlO3 control uses the re-fitted external unit cell'
    )
    assert all(site.occupancy.value == 1 for site in p.structure.atom_sites), (
        'The YAlO3 control loads physical site occupancy after undoing FullProf multiplicities'
    )
