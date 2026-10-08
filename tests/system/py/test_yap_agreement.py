"""Agreement with the unchanged owner-supplied YAP FullProf model."""

from pathlib import Path

import edi
import pytest

from tests.fixtures.multiphase import fullprof
from tests.fixtures.multiphase.support import stage_delivered_corpus_project

ROOT = Path(__file__).resolve().parents[3]
PROJECT = ROOT / 'docs/user/cli/pd-neut-cwl_yap-spodi_3k/project'


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
    al1 = next(site for site in p.structures['Al2O3'].atom_sites if site.id == 'Al1')
    assert al1.adp_iso.value < 0, 'The admitted negative Al1 Biso must not be silently clamped'


def test_yap_fit_agrees_with_every_other_fullprof_parameter_and_rwp(tmp_path):
    assert PROJECT.is_dir(), 'The independent YAP agreement gate needs the delivered CLI project'
    target = stage_delivered_corpus_project(PROJECT, 'yap-spodi-3k', tmp_path / 'project')
    p = edi.Project.load(target)
    assert len(p.free_parameters) == 56, 'The full YAP fit must retain 56 declared free parameters'
    result = p.fit()
    assert abs(result.rwp / fullprof.reference()['rwp'] - 1) <= 0.05, (
        'The full YAP model Rwp must agree within five percent relative to FullProf 4.08 percent'
    )
    full_actual = fullprof.actual_values(p)
    saved = tmp_path / 'saved'
    p.save_as(saved)
    reopened = edi.Project.load(saved)
    assert fullprof.actual_values(reopened) == full_actual, (
        'Both fitted phase models must roundtrip without changing their values'
    )
    p = edi.Project.load(target)
    for name in ('asym_beba_a0', 'asym_beba_b0', 'asym_beba_a1', 'asym_beba_b1'):
        parameter = getattr(p.experiments[0].peak, name)
        parameter.value = 0
        parameter.free = False
    assert len(p.free_parameters) == 52, (
        'Fixing the four asymmetry coefficients must leave exactly 52 independent fitted values'
    )
    p.fit()
    actual = fullprof.actual_values(p, asymmetry_off=True)
    reference = fullprof.reference(asymmetry_off=True)
    assert len(actual) == len(reference['parameters']) == 52, (
        'The asymmetry-off comparison must cover every independent free value'
    )
    for key, (value, su) in reference['parameters'].items():
        assert abs(actual[key] - value) <= su, (
            'Every asymmetry-off fitted value must agree within its own FullProf uncertainty: '
            + key
        )


def test_verification_page_executes_the_owner_reference_comparison():
    page = ROOT / 'docs/dev/verification/pd-neut-cwl_YAP_multiphase.py'
    assert page.is_file(), 'YAP needs its own executable verification artifact'
    text = page.read_text()
    assert all(
        word in text.lower()
        for word in ('fullprof', 'owner-supplied', 'asymmetry', 'fallback', 'inexact')
    ), 'The page must name the external origin and the inexact-asymmetry fallback rule'
    assert 'pytest.skip' not in text and 'pytest.xfail' not in text, (
        'The independent agreement page must execute its comparisons'
    )


def test_yap_project_reproduces_the_external_instrument_and_profile_settings():
    assert PROJECT.is_dir(), 'YAP settings require the delivered owner-reference project'
    project = edi.Project.load(PROJECT)
    experiment = project.experiments[0]
    assert experiment.peak.asym_beba_limit.value == 160, (
        'The YAP model must retain the FullProf asymmetry limit in degrees'
    )
    assert experiment.absorption.mu_r.value == pytest.approx(0.0221, abs=0, rel=0), (
        'The YAP model must reproduce the nonzero FullProf absorption setting'
    )
    assert len(experiment.background) == 25, (
        'The YAP model must retain every external interpolated background point'
    )
    assert len(experiment.excluded_regions) == 2, (
        'The YAP model must retain both external excluded regions'
    )
