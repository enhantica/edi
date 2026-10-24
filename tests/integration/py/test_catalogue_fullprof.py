"""Same-start independent patterns and the durable external reference inventory."""

import copy
import hashlib
import json
import math
import re
from pathlib import Path

import edi
import numpy as np
import pytest
from edi import verification

from tests.fixtures.example_catalogue.fullprof_profile import read_profile
from tests.integration.py.test_example_catalogue import SELECTED

ROOT = Path(__file__).resolve().parents[3]
# The recorded comparison decision names these four cases explicitly.
ASYMMETRY_OFF_CASES = {
    'pd-neut-cwl_hs-hrpt',
    'pd-neut-cwl_yalo3-al2o3-spodi',
    'pd-neut-xray-cwl_pbso4-d1a-lab',
    'pd-xray-cwl_latp-bm01_scan',
}
# The October 24 minor-phase decision applies only to this template variant.
LATP_CASE = 'pd-xray-cwl_latp-bm01_scan'
LATP_CELL_PINS = {
    'param.alpo4_c2221.cell_length_a.value',
    'param.alpo4_c2221.cell_length_b.value',
    'param.alpo4_c2221.cell_length_c.value',
    'param.alpo4_p63mc.cell_length_a.value',
    'param.alpo4_p63mc.cell_length_c.value',
}
COMPARISON_BOUNDS = json.loads(
    (ROOT / 'tests/fixtures/example_catalogue/comparison-bounds.json').read_text()
)['cases']


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


def assert_shared_references(values, source, regression_pins=frozenset()):
    project = ROOT / source['start_project']
    structures = len(list((project / 'structures').glob('*.edi')))
    expected = {}
    for unique, code in source['parameter_codes'].items():
        if not code:
            continue
        if '.cell.' in unique:
            structure, field = unique.split('.cell.')
            label = 'cell_' + field
        elif '.atom_site.' in unique:
            structure, field = unique.split('.atom_site.')
            site, attribute = field.split('.')
            if attribute not in {'fract_x', 'fract_y', 'fract_z', 'adp_iso'}:
                continue
            label = site + '.' + attribute
        else:
            continue
        prefix = structure + '.' if structures > 1 else ''
        expected['param.' + prefix + label + '.value'] = source['fullprof_parameters'][str(code)][
            'value'
        ]
    shared = {name: spec for name, spec in values.items() if name.startswith('param.')}
    assert shared and shared.keys() == expected.keys(), (
        'Every shared fitted value must be present exactly once in its comparison model'
    )
    for name, spec in shared.items():
        if name in regression_pins:
            assert spec.get('kind') == 'regression-pin', (
                'Only the five decided minor-phase cells are explicitly labelled regression pins'
            )
            assert isinstance(spec['value'], (int, float)) and math.isfinite(spec['value']), (
                'Every labelled minor-phase regression pin requires a finite numeric value'
            )
        else:
            assert spec.get('kind') == 'reference', (
                'Shared fitted values remain independent references '
                'outside the exact cell exception'
            )
            assert spec['value'] == expected[name], (
                'Each shared fitted value must equal its independent FullProf parameter'
            )
        assert (
            spec['tol_rel'] is None
            and spec['tol_abs'] is not None
            and math.isfinite(spec['tol_abs'])
            and spec['tol_abs'] > 0
        ), 'Shared fitted values require finite positive absolute uncertainty bounds'


def assert_comparison_disposition(case, expected):
    groups = {'default': expected}
    groups.update(expected.get('variants', {}))
    assert groups.keys() == COMPARISON_BOUNDS[case].keys(), (
        'The comparison retains its complete declared model and variant inventory'
    )
    for group, block in groups.items():
        disposition = case == LATP_CASE and group == 'asymmetry-off'
        status = 'max_iter' if disposition else 'done'
        assert block.get('status', 'done') == status, (
            'Only the decided LATP template asymmetry-off fit '
            'expects the resume-cap max_iter status'
        )
        frozen = COMPARISON_BOUNDS[case][group]
        values = block['quantities']
        assert values.keys() == frozen.keys(), (
            'Every comparison quantity remains present across the case-specific disposition'
        )
        for name, spec in values.items():
            bounds = {key: spec[key] for key in ('tol_abs', 'tol_rel')}
            if disposition and name in LATP_CELL_PINS:
                assert (
                    bounds['tol_rel'] is None
                    and bounds['tol_abs'] is not None
                    and math.isfinite(bounds['tol_abs'])
                    and 0 < bounds['tol_abs'] <= frozen[name]['tol_abs']
                ), 'The five labelled cell pins require an explicit unrelaxed numeric bound'
            else:
                assert bounds == frozen[name], (
                    'Every other comparison bound remains exactly as committed before the decision'
                )
    if case == LATP_CASE:
        assert expected['source']['provenance'] == 'PROVENANCE.md', (
            'The minor-phase disposition must point to its own committed provenance explanation'
        )


def assert_latp_provenance(reason):
    reason = reason.casefold().replace('₄', '4')
    assert all(
        word in reason
        for word in ('alpo4', 'cell', 'fullprof', 'regression', 'max_iter', 'adr-0098', 'resume')
    ) and any(word in reason for word in ('lower', 'better')), (
        'The provenance explains the minor-phase minimum gap and names the ADR-0098 resume cap'
    )


def test_latp_disposition_provenance_names_the_resume_cap():
    reason = (ROOT / 'docs/user/cli' / LATP_CASE / 'PROVENANCE.md').read_text()
    assert_latp_provenance(reason)


def assert_cli_expectations(case, expected):
    values = expected['quantities']
    source = reference(case)
    assert expected.get('template', False) is case.endswith('_scan'), (
        'A scan compares its template single fit; ordinary cases cannot substitute a template'
    )
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
    assert values['rwp']['tol_abs'] is None, (
        'The five-percent Rwp bound cannot be overridden by an absolute tolerance'
    )
    for name in ['reduced_chi_square', 'iterations']:
        assert values[name]['kind'] == 'regression-pin', (
            'Solver-specific terminal quantities must be identified as regression pins'
        )
    variants = expected.get('variants', {})
    if case in ASYMMETRY_OFF_CASES:
        assert 'asymmetry-off' in variants, (
            'Each decided asymmetry comparison requires its explicit asymmetry-off variant'
        )
        assert not any(name.startswith('param.') for name in values), (
            'The full asymmetry model compares factors; shared values belong to asymmetry-off'
        )
        home = reference_home(case) / 'asymmetry-off'
        off = json.loads((home / 'reference.json').read_text())
        assert (
            off['program'] == 'FullProf'
            and off['converged']
            and off['scope'] == 'asymmetry-off fit'
            and off['start_project'] == source['start_project']
        ), 'The alternate values require a converged FullProf asymmetry-off fit of this start'
        pattern = (
            r'Parameter number\s+(\d+)\s*:\s+(\S+)\s+([-+\d.Ee]+)'
            r'\s*\(\s*\+/-\s*([-+\d.Ee]+)'
        )
        table = {
            index: {'symbol': symbol, 'value': float(value), 'uncertainty': float(sigma)}
            for index, symbol, value, sigma in re.findall(pattern, (home / 'fit.out').read_text())
        }
        assert table and off['fullprof_parameters'] == table, (
            'The asymmetry-off parameter reference must retain the actual FullProf output table'
        )
        alternate = variants['asymmetry-off']['quantities']
        assert alternate['n_free']['kind'] == 'reference', (
            'The asymmetry-off free count remains an independent reference'
        )
        assert alternate['n_free']['value'] == off['n_free'], (
            'The asymmetry-off free count must describe its own FullProf fit'
        )
        for name in ['reduced_chi_square', 'iterations']:
            assert alternate[name]['kind'] == 'regression-pin', (
                'The asymmetry-off solver terminal quantities remain labelled regression pins'
            )
        assert_shared_references(
            alternate, off, LATP_CELL_PINS if case == LATP_CASE else frozenset()
        )
    else:
        assert 'asymmetry-off' not in variants, (
            'Only the four decided cases may move shared values to an asymmetry-off comparison'
        )
        assert_shared_references(values, source)
    assert_comparison_disposition(case, expected)


@pytest.mark.parametrize('case', [case for case in SELECTED if not case.endswith('_simulation')])
def test_cli_fit_expectations_retain_independent_factors_and_reference_kinds(case):
    path = ROOT / 'docs/user/cli' / case / 'expected.json'
    assert path.is_file(), 'Every measured example must execute against an expected-result record'
    assert_cli_expectations(case, json.loads(path.read_text()))


@pytest.mark.parametrize(
    'escape',
    [
        'missing-variant',
        'empty-shared',
        'missing-one-shared',
        'extra-shared',
        'relabelled-shared',
        'changed-shared-value',
        'unbounded-shared',
        'wrong-off-free-count',
        'relabelled-off-free-count',
        'changed-full-rwp',
        'relaxed-full-rwp',
        'relabelled-full-rwp',
        'missing-scan-template',
        'ordinary-case-moved-to-variant',
    ],
)
def test_comparison_contract_refuses_missing_or_relabelled_references(escape):  # noqa: PLR0912 - explicit record mutations
    case = 'pd-neut-cwl_hs-hrpt'
    if escape == 'missing-scan-template':
        case = 'pd-xray-cwl_latp-bm01_scan'
    elif escape == 'ordinary-case-moved-to-variant':
        case = 'pd-neut-cwl_lbco-hrpt'
    path = ROOT / 'docs/user/cli' / case / 'expected.json'
    expected = json.loads(path.read_text())
    assert_cli_expectations(case, expected)
    bad = copy.deepcopy(expected)
    if escape == 'ordinary-case-moved-to-variant':
        bad['variants'] = {'asymmetry-off': {'quantities': bad['quantities']}}
    elif escape == 'missing-scan-template':
        del bad['template']
    else:
        values = bad['variants']['asymmetry-off']['quantities']
        shared = [name for name in values if name.startswith('param.')]
        if escape == 'missing-variant':
            del bad['variants']['asymmetry-off']
        elif escape == 'empty-shared':
            for name in shared:
                del values[name]
        elif escape == 'missing-one-shared':
            del values[shared[0]]
        elif escape == 'extra-shared':
            values['param.unknown.value'] = copy.deepcopy(values[shared[0]])
        elif escape == 'relabelled-shared':
            values[shared[0]]['kind'] = 'regression-pin'
        elif escape == 'changed-shared-value':
            values[shared[0]]['value'] += 1
        elif escape == 'unbounded-shared':
            values[shared[0]]['tol_abs'] = float('inf')
        elif escape == 'wrong-off-free-count':
            values['n_free']['value'] += 1
        elif escape == 'relabelled-off-free-count':
            values['n_free']['kind'] = 'regression-pin'
        elif escape == 'changed-full-rwp':
            bad['quantities']['rwp']['value'] += 1
        elif escape == 'relaxed-full-rwp':
            for field, value in [('tol_rel', 0.5), ('tol_abs', 1.0)]:
                relaxed = copy.deepcopy(expected)
                relaxed['quantities']['rwp'][field] = value
                with pytest.raises(AssertionError):
                    assert_cli_expectations(case, relaxed)
            return
        elif escape == 'relabelled-full-rwp':
            bad['quantities']['rwp']['kind'] = 'regression-pin'
    with pytest.raises(AssertionError):
        assert_cli_expectations(case, bad)


@pytest.mark.parametrize(
    'escape',
    [
        'unlabelled-cell',
        'missing-cell',
        'extra-cell',
        'relaxed-cell-pin',
        'relabelled-latp-phase',
        'changed-latp-reference',
        'relaxed-latp-bound',
        'relaxed-other-case-bound',
        'unlabelled-other-case-value',
        'other-case-pin',
        'wrong-status',
        'missing-status',
        'other-case-max-iter',
        'default-model-pin',
        'wrong-default-status',
        'wrong-provenance-link',
        'missing-resume-explanation',
    ],
)
def test_latp_minor_phase_disposition_cannot_escape_its_case_and_bounds(escape):  # noqa: PLR0912, PLR0915 - explicit disposition escapes
    case = 'pd-neut-cwl_hs-hrpt' if 'other-case' in escape else LATP_CASE
    path = ROOT / 'docs/user/cli' / case / 'expected.json'
    expected = json.loads(path.read_text())
    assert_cli_expectations(case, expected)
    bad = copy.deepcopy(expected)
    alternate = bad['variants']['asymmetry-off']
    values = alternate['quantities']
    cell = min(LATP_CELL_PINS)
    p1 = 'param.latp.P1.adp_iso.value'
    if escape == 'unlabelled-cell':
        for name in sorted(LATP_CELL_PINS):
            unlabelled = copy.deepcopy(expected)
            del unlabelled['variants']['asymmetry-off']['quantities'][name]['kind']
            with pytest.raises(AssertionError):
                assert_cli_expectations(case, unlabelled)
        return
    if escape == 'missing-cell':
        del values[cell]
    elif escape == 'extra-cell':
        values['param.alpo4_c2221.cell_angle_alpha.value'] = copy.deepcopy(values[cell])
    elif escape == 'relaxed-cell-pin':
        values[cell]['tol_abs'] = 2 * COMPARISON_BOUNDS[case]['asymmetry-off'][cell]['tol_abs']
    elif escape == 'relabelled-latp-phase':
        values[p1]['kind'] = 'regression-pin'
    elif escape == 'changed-latp-reference':
        values[p1]['value'] += 1
    elif escape == 'relaxed-latp-bound':
        for name in [key for key in values if key.startswith('param.latp.')]:
            relaxed = copy.deepcopy(expected)
            relaxed['variants']['asymmetry-off']['quantities'][name]['tol_abs'] *= 1.01
            with pytest.raises(AssertionError):
                assert_cli_expectations(case, relaxed)
        return
    elif escape in {'relaxed-other-case-bound', 'unlabelled-other-case-value', 'other-case-pin'}:
        name = next(key for key in values if key.startswith('param.'))
        if escape == 'relaxed-other-case-bound':
            values[name]['tol_abs'] *= 1.01
        elif escape == 'unlabelled-other-case-value':
            del values[name]['kind']
        else:
            values[name]['kind'] = 'regression-pin'
    elif escape == 'wrong-status':
        alternate['status'] = 'done'
    elif escape == 'missing-status':
        del alternate['status']
    elif escape == 'other-case-max-iter':
        alternate['status'] = 'max_iter'
    elif escape == 'default-model-pin':
        bad['quantities'][cell] = copy.deepcopy(values[cell])
    elif escape == 'wrong-default-status':
        bad['status'] = 'max_iter'
    elif escape == 'wrong-provenance-link':
        bad['source']['provenance'] = 'README.md'
    elif escape == 'missing-resume-explanation':
        with pytest.raises(AssertionError):
            assert_latp_provenance(
                'AlPO4 cells; FullProf lower minimum; regression pins; max_iter'
            )
        return
    with pytest.raises(AssertionError):
        assert_cli_expectations(case, bad)
