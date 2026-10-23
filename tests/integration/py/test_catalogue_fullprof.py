"""Same-start independent patterns and the durable external reference inventory."""

import hashlib
import json
import re
from pathlib import Path

import edi
import numpy as np
import pytest
from edi import verification

from tests.fixtures.example_catalogue.fullprof_profile import read_profile
from tests.integration.py.test_example_catalogue import SELECTED

ROOT = Path(__file__).resolve().parents[3]


def reference_home(case):
    home = 'verification' if case.endswith('_simulation') else 'fitting'
    return ROOT / f'knowledge/{home}/fullprof' / case


def reference(case):
    path = reference_home(case) / 'reference.json'
    assert path.is_file(), 'Each catalogue case needs its own independently calculated start'
    return json.loads(path.read_text())


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.mark.parametrize('case', SELECTED)
def test_fullprof_reference_binds_all_committed_start_inputs_and_outputs(case):
    home = reference_home(case)
    record = reference(case)
    assert record['program'] == 'FullProf' and record['same_start'], (
        'Reference provenance must name FullProf and the exact unmodified start'
    )
    project = ROOT / record['start_project']
    inputs = {str(p.relative_to(project)): sha256(p) for p in sorted(project.rglob('*.edi'))}
    assert record['project_sha256'] == inputs, (
        'Every structure, experiment, free flag and constraint must match the referenced start'
    )
    assert record['staging'] == 'none', 'A staged fit cannot claim agreement from the user start'
    pins = record['artifacts_sha256']
    assert 'start.pcr' in pins and any(p.endswith('.prf') for p in pins), (
        'A reference requires the committed calculation input and actual FullProf output'
    )
    for name, digest in pins.items():
        assert sha256(home / name) == digest, (
            'Every external output must retain its provenance pin'
        )
    provenance = home / 'PROVENANCE.md'
    assert provenance.is_file(), (
        'Every FullProf project needs a human-readable reproduction record'
    )
    assert 'fp2k' in provenance.read_text() and '8.40' in provenance.read_text(), (
        'The reference must identify the executable version and authoring invocation'
    )


@pytest.mark.parametrize('case', SELECTED)
def test_fullprof_fixed_start_agrees_before_fitting_can_absorb_a_mapping_error(case):
    record = reference(case)
    project = edi.Project.load(ROOT / record['start_project'])
    comparisons = []
    for index, bank in enumerate(record['banks'], 1):
        suffix = '' if len(record['banks']) == 1 else f'_{index}'
        path = reference_home(case) / f'start{suffix}.prf'
        assert path.is_file(), 'Every bank needs an all-fixed start profile from FullProf'
        x, expected = read_profile(path)
        assert len(x) > 10 and np.isfinite(expected).all(), (
            'The independent pattern must contain finite observations across its fitted range'
        )
        experiment = project.experiments[bank]
        verification.set_reference_as_measured(experiment, x, expected)
        project.calculate()
        actual = np.asarray(experiment.data.intensity_calc)
        assert actual.shape == expected.shape, 'The compared patterns must use the same grid'
        included = np.ones(len(x), dtype=bool)
        for low, high in experiment.excluded_regions:
            included &= (x < low) | (x > high)
        # FullProf's printed x precision can round the first included point into an exclusion.
        # Compare the intersection of the independently printed grid and the declared mask.
        assert included.any(), 'The compared grid must retain included observations'
        comparisons.append((bank, expected[included], actual[included]))
    verification.assert_patterns_agree(comparisons)


@pytest.mark.parametrize('case', [case for case in SELECTED if not case.endswith('_simulation')])
def test_measured_reference_has_a_fit_and_its_fitted_fixed_twin(case):
    record = reference(case)
    home = reference_home(case)
    twin = ROOT / 'knowledge/verification/fullprof' / case
    assert record['scope'] == ('template' if case.endswith('_scan') else 'fit'), (
        'A scan reference claims only its selected template, never the other scan files'
    )
    assert record['converged'], 'A finite converged external fit is required for a minimum claim'
    assert record['fit_output_complete'], 'An unsuccessful external fit leaves this case open'
    for name in ['fit.pcr', 'fit.new', 'fit.sum']:
        assert (home / name).is_file(), 'The fitting reference must retain its input and result'
    text = (home / 'fit.pcr').read_text()
    control = re.search(r'^!Ipr .+\n(.+)', text, re.MULTILINE)
    if control and 'Mat Pcr' in control[0]:
        assert control[1].split()[4] == '2', 'FullProf must preserve a separate fitted .new result'
    else:
        assert re.search(r'^!Mat Pcr.+\n\S+ 2 ', text, re.MULTILINE), (
            'Joint FullProf inputs must also retain their fitted .new result'
        )
    assert int(re.search(r'(\d+) !Number of refined parameters', text)[1]) == record['n_free'], (
        'The recorded free count must describe the actual fitting input'
    )
    assert (twin / 'fixed.pcr').is_file(), 'Every fitted reference needs an all-fixed twin'
    assert re.search(
        r'^\s*0\s+!Number of refined parameters', (twin / 'fixed.pcr').read_text(), re.MULTILINE
    ), 'The twin must calculate at the fitted state with no active variables'
    for name, digest in record['twin_artifacts_sha256'].items():
        assert sha256(twin / name) == digest, (
            'Every fitted fixed-twin artifact must retain its pin'
        )
    for index in range(1, len(record['banks']) + 1):
        suffix = '' if len(record['banks']) == 1 else f'_{index}'
        profile = twin / f'fixed{suffix}.prf'
        assert profile.is_file(), 'The fitted twin must produce a profile for every bank'
        _, values = read_profile(profile)
        assert np.isfinite(values).all(), 'A failed external calculation is not a reference'


def test_diffraction_library_tch_witness_uses_the_same_simulation_model():
    home = ROOT / 'knowledge/comparison/pd-neut-cwl_lbco_simulation/diffraction-lib'
    metadata = home / 'reference.json'
    assert metadata.is_file(), 'The TCH comparison needs a frozen diffraction-lib calculation'
    source = json.loads(metadata.read_text())
    assert source['program'] == 'diffraction-lib' and source['model_compatible'], (
        'The comparable TCH witness must identify its independent program and model'
    )
    profile = home / 'start.npz'
    assert sha256(profile) == source['artifacts_sha256']['start.npz'], (
        'The diffraction-lib witness must retain its independent calculated profile'
    )
    values = np.load(profile)
    project = edi.Project.load(ROOT / 'docs/user/cli/pd-neut-cwl_lbco_simulation/project')
    verification.set_reference_as_measured(project.experiment, values['x'], values['calculated'])
    project.calculate()
    verification.assert_patterns_agree([
        ('TCH', values['calculated'], np.asarray(project.experiment.data.intensity_calc))
    ])


@pytest.mark.parametrize(
    'case',
    [
        'pd-xray-cwl_pbso4-lab',
        'pd-neut-xray-cwl_pbso4-d1a-lab',
        'pd-neut-cwl_hs-hrpt',
        'pd-neut-cwl_yalo3-al2o3-spodi',
        'pd-xray-cwl_latp-bm01_scan',
    ],
)
def test_diffraction_library_marks_the_beba_model_gap_instead_of_comparing_minima(case):
    path = ROOT / 'knowledge/comparison' / case / 'diffraction-lib/reference.json'
    assert path.is_file(), 'Every comparison row needs an explicit model compatibility record'
    source = json.loads(path.read_text())
    assert not source['model_compatible'] and source['reason'].strip(), (
        'The TCH-versus-mixing-eta BeBa gap must be named before reporting fit agreement'
    )


@pytest.mark.parametrize('case', [case for case in SELECTED if not case.endswith('_simulation')])
def test_cli_fit_expectations_retain_independent_factors_and_reference_kinds(case):
    path = ROOT / 'docs/user/cli' / case / 'expected.json'
    assert path.is_file(), 'Every measured example must execute against an expected-result record'
    values = json.loads(path.read_text())['quantities']
    source = reference(case)
    assert source['converged'], 'A nonconvergent external attempt cannot supply minimum references'
    assert values['n_free']['kind'] == 'reference', (
        'The shared free count is an external reference'
    )
    assert values['n_free']['value'] == source['n_free'], (
        'The executing example must retain the independent FullProf free count'
    )
    assert values['rwp']['kind'] == 'reference', 'Rwp must be identified as an external reference'
    assert values['rwp']['value'] == pytest.approx(source['r_wp'], rel=1e-3), (
        'The executing Rwp reference must come from the same-start FullProf output'
    )
    assert values['rwp']['tol_rel'] == 0.05, (
        'Rwp must retain the agreed five-percent relative bound'
    )
    for name in ['reduced_chi_square', 'iterations']:
        assert values[name]['kind'] == 'regression-pin', (
            'Solver-specific terminal quantities must be identified as regression pins'
        )
    shared = [spec for name, spec in values.items() if name.startswith('param.')]
    assert shared and all(spec['kind'] == 'reference' for spec in shared), (
        'Shared fitted values must be independently referenced rather than relabelled regressions'
    )
