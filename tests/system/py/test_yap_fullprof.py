"""Agreement with the owner-supplied two-phase FullProf run."""

import json
import shutil
from pathlib import Path

import edi
import numpy as np
import pytest

from tests.fixtures.multiphase import fullprof

ROOT = Path(__file__).resolve().parents[3]
PROJECT = ROOT / 'docs/user/cli/pd-neut-cwl_yap-spodi_3k/project'


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


def test_delivered_yap_project_has_both_phases_and_physical_occupancies():
    assert PROJECT.is_dir(), 'The first multiphase CLI project must be delivered'
    p = edi.Project.load(PROJECT)
    assert set(p.structures.keys()) == set(fullprof.SITES), (
        'The delivered YAP project must carry both named FullProf phases'
    )
    for name in fullprof.SITES:
        assert all(
            site.occupancy.value == pytest.approx(1, abs=1.1e-5)
            for site in p.structures[name].atom_sites
        ), (
            'Each delivered phase must carry physical site occupancies, '
            'never FullProf normalized occupancies'
        )
    assert p.structures['Al2O3'].atom_sites['Al1'].adp_iso.value < 0, (
        'The admitted negative Al1 Biso must not be silently clamped'
    )


def test_yap_fit_agrees_with_every_other_fullprof_parameter_and_rwp(tmp_path):
    assert PROJECT.is_dir(), 'The independent YAP agreement gate needs the delivered CLI project'
    target = tmp_path / 'project'
    shutil.copytree(PROJECT, target)
    p = edi.Project.load(target)
    assert len(p.free_parameters) == 56, 'The YAP fit must retain all 56 declared free parameters'
    result = p.fit()
    actual = fullprof.actual_values(p)
    for key, (value, su) in fullprof.reference()['parameters'].items():
        assert abs(actual[key] - value) <= su, (
            'Every non-asymmetry fitted parameter must agree within its own '
            'FullProf standard uncertainty'
        )
    assert abs(result.rwp / fullprof.reference()['rwp'] - 1) <= 0.05, (
        'Fitted YAP Rwp must agree within five percent relative to FullProf'
    )
    saved = tmp_path / 'saved'
    p.save_as(saved)
    reopened = edi.Project.load(saved)
    assert fullprof.actual_values(reopened) == actual, (
        'Both fitted phase models must roundtrip without changing their values'
    )


def test_verification_page_executes_the_owner_reference_comparison():
    page = ROOT / 'docs/dev/verification/pd-neut-cwl_YAP_multiphase.py'
    assert page.is_file(), 'YAP needs its own executable verification artifact'
    text = page.read_text()
    assert all(
        word in text.lower() for word in ('fullprof', 'owner', 'asymmetry', 'uncertaint')
    ), 'The page must name the external origin and the inexact-asymmetry fallback rule'
    assert 'pytest.skip' not in text and 'pytest.xfail' not in text, (
        'The independent agreement page must execute its comparisons'
    )
