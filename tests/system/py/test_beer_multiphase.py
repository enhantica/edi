"""The external BEER two-phase/two-bank load, fit and persistence contract."""

import hashlib
import math
from pathlib import Path

import edi as engine
import numpy as np

from tests.fixtures.multiphase import beer, support

ROOT = Path(__file__).resolve().parents[3]


def test_beer_reference_binds_both_banks_and_every_reported_uncertainty():
    ref = beer.reference()
    assert (
        hashlib.sha256((beer.HOME / 'reference.json').read_bytes()).hexdigest()
        == 'b194523d2cbd6cf9e250b39609e59966a3563059d46980665130800649ca3f12'
    ), (
        'The committed independent BEER values, uncertainties and run '
        'provenance must retain their authoring digest'
    )
    assert (
        ref['archive_sha256'] == '68bdc067bda10fa07bfa9546375fa1ac85dd575add401c6b813cbd066cdb7d5e'
    ), 'The BEER measured-data archive must match the digest in the pinned external data index'
    assert ref['diffraction_lib_commit'] == '0d9f10e412a0cd08d4dd0af95845dd9bb597dcdf', (
        'BEER expectations must identify the owner-selected independent source commit'
    )
    assert ref['versions']['cryspy'] == '0.12.1', (
        'The BEER reference must identify the default independent calculator version'
    )
    for name, expected in ref['data_sha256'].items():
        assert hashlib.sha256((beer.HOME / 'data' / name).read_bytes()).hexdigest() == expected, (
            'Every committed BEER input must retain its external source digest'
        )
    for directory, manifest in (('initial', 'initial_sha256'), ('stage-2', 'output_sha256')):
        assert beer.tree_digests(beer.HOME / 'reference-run' / directory) == ref[manifest], (
            'The independent BEER input and output Edi trees must retain every recorded digest'
        )
    assert len(ref['stages']) == 2, 'The BEER reference must retain both tutorial stages'
    assert ref['reference_variant'] == 'unconstrained-independent-bank-scales', (
        'The BEER agreement reference must compare independently free bank scales'
    )
    assert all(s['success'] for s in ref['stages']), (
        'The BEER reference must preserve both successful tutorial fit stages'
    )
    assert len(ref['stages'][0]['parameters']) == 56, (
        'The first unconstrained BEER fit must retain every background and all four phase scales'
    )
    assert len(ref['stages'][1]['parameters']) == 16, (
        'The unconstrained BEER reference must retain both N2 scales '
        'and every second-stage parameter'
    )
    assert all(
        math.isfinite(p['value']) and math.isfinite(p['su']) and p['su'] > 0
        for stage in ref['stages']
        for p in stage['parameters'].values()
    ), 'Every BEER comparison needs a finite external value and its positive reported uncertainty'


def test_beer_scale_convention_uses_only_reference_geometry_and_maps_each_uncertainty():
    reference = beer.reference()
    original = (beer.HOME / 'reference.json').read_bytes()
    for bank in ('expt_s2', 'expt_n2'):
        assert math.isclose(beer.scale_factor(reference, bank), math.sqrt(2), rel_tol=1e-15), (
            'The independent 90-degree BEER scattering geometry must map scales by sqrt(2)'
        )
    for stage in reference['stages']:
        expected = beer.mapped_parameters(reference, stage)
        assert set(expected) == set(stage['parameters']), (
            'Convention mapping must retain every independently fitted BEER parameter'
        )
        for key, parameter in stage['parameters'].items():
            if '.linked_structure.' in key and key.endswith('.scale'):
                assert expected[key]['value'] == parameter['value'] * math.sqrt(2), (
                    'Each BEER bank phase scale must use the independent TOF prefactor conversion'
                )
                assert expected[key]['su'] == parameter['su'] * math.sqrt(2), (
                    'Each phase scale must retain its own external SU in the converted units'
                )
            else:
                assert expected[key] == parameter, (
                    'The TOF scale convention must not alter any other external parameter'
                )
    changed = beer.reference()
    changed['stages'][0]['all_parameters']['expt_n2.instrument.twotheta_bank']['value'] = 60
    assert math.isclose(beer.scale_factor(changed, 'expt_n2'), 2, rel_tol=1e-15), (
        'The mapping must read the declared reference angle rather than hard-code the BEER factor'
    )
    assert (beer.HOME / 'reference.json').read_bytes() == original, (
        'Convention comparisons must preserve the raw independent reference artifact exactly'
    )


def test_beer_two_phases_and_independent_bank_scales_survive_two_save_cycles(tmp_path):
    project = engine.Project.load(beer.write_initial(tmp_path / 'input'))
    assert set(project.structures.keys()) == {'ferrite', 'austenite'}, (
        'The BEER project must load both independently specified Fe phases'
    )
    assert set(project.experiments.keys()) == {'expt_s2', 'expt_n2'}, (
        'The BEER project must load both independent time-of-flight banks'
    )
    for name, expected_a in (('ferrite', 2.886), ('austenite', 3.6468)):
        assert project.structures[name].cell.length_a.value == expected_a, (
            'Each BEER phase must retain its distinct tutorial lattice constant'
        )
    # Authored nonidentity writes exercise independent bank storage before persistence.
    support.links(project.experiments['expt_n2'])['ferrite'].scale.value *= 1.17
    support.links(project.experiments['expt_s2'])['austenite'].scale.value *= 0.81
    scales = {
        (experiment.name, phase): support.links(experiment)[phase].scale.value
        for experiment in project.experiments
        for phase in ('ferrite', 'austenite')
    }
    before = {}
    for experiment in project.experiments:
        assert list(support.links(experiment).keys()) == ['ferrite', 'austenite'], (
            'Each BEER bank must retain both named phase links'
        )
    project.analysis.calculate()
    for experiment in project.experiments:
        assert set(experiment.refln.structure_id) == {'ferrite', 'austenite'}, (
            'Both BEER phase identities must reach each bank reflection chart'
        )
        before[experiment.name] = np.asarray(experiment.data.intensity_calc).copy()
    for index in range(2):
        saved = tmp_path / f'saved-{index}'
        project.save_as(saved)
        project = engine.Project.load(saved)
        assert set(project.structures.keys()) == {'ferrite', 'austenite'}, (
            'Each BEER save cycle must retain both complete phase blocks'
        )
        text = (saved / 'analysis/analysis.edi').read_text()
        assert '_constraint.' not in text, (
            'Unconstrained BEER save cycles must not create cross-bank scale constraints'
        )
        for experiment in project.experiments:
            for phase in ('ferrite', 'austenite'):
                row = support.links(experiment)[phase]
                assert row.scale.value == scales[experiment.name, phase], (
                    'Each BEER bank must preserve its own independent phase scale after reopen'
                )
                assert row.scale.free, (
                    'All four unconstrained BEER bank phase scales must remain independently free'
                )
        project.analysis.calculate()
        for experiment in project.experiments:
            np.testing.assert_array_equal(
                np.asarray(experiment.data.intensity_calc),
                before[experiment.name],
                err_msg='BEER save and reopen must preserve each calculated bank exactly',
            )


def test_beer_joint_fit_recovers_both_phases_with_every_external_uncertainty(tmp_path):
    ref = beer.reference()
    project = engine.Project.load(beer.write_initial(tmp_path / 'fit'))
    assert len(project.free_parameters) == 56, (
        'The unconstrained BEER first stage must fit every tutorial parameter and both N2 scales'
    )
    stage_deviations = {}
    for index, stage in enumerate(ref['stages'], 1):
        expected_parameters = beer.mapped_parameters(ref, stage)
        result = project.analysis.fit()
        assert result.converged, (
            'Each BEER tutorial stage must report a completed converged joint fit'
        )
        values = beer.actual_values(project, expected_parameters)
        deviations = {
            key: {'actual': values[key], 'expected': parameter['value'], 'su': parameter['su']}
            for key, parameter in expected_parameters.items()
            if abs(values[key] - parameter['value']) > parameter['su']
        }
        if deviations:
            stage_deviations[index] = deviations
        assert abs(beer.active_rwp(project) / stage['active_rwp'] - 1) <= 0.05, (
            'BEER fit quality on the included windows must agree within five '
            'percent relative to the external run'
        )
        for experiment in project.experiments:
            for point in experiment.background:
                point.intensity.free = False
    assert not stage_deviations, (
        'Every BEER fitted parameter must agree within its own '
        'independent reported standard uncertainty, with phase scale value '
        'and SU mapped by 1/sin(theta_bank): '
        f'{stage_deviations}'
    )
    assert len(project.free_parameters) == 16, (
        'Fixing only BEER backgrounds must leave all sixteen '
        'unconstrained second-stage parameters free'
    )
    expected_parameters = beer.mapped_parameters(ref, ref['stages'][-1])
    for name in ('ferrite', 'austenite'):
        for experiment in project.experiments:
            expected = expected_parameters[f'{experiment.name}.linked_structure.{name}.scale']
            assert (
                abs(support.links(experiment)[name].scale.value - expected['value'])
                <= expected['su']
            ), (
                'Each bank must recover its own independent BEER phase scale '
                'within its converted SU'
            )
    final = beer.actual_values(project, ref['stages'][-1]['parameters'])
    saved = tmp_path / 'fitted-saved'
    project.save_as(saved)
    reopened = engine.Project.load(saved)
    assert beer.actual_values(reopened, final) == final, (
        'Every fitted BEER phase, profile and calibration value must '
        'survive save and reopen exactly'
    )
    assert len(reopened.free_parameters) == 16, (
        'BEER save and reopen must retain the free set '
        'and all four independently fitted phase scales'
    )


def test_beer_cli_id_and_verification_page_use_the_committed_external_inputs():
    project_dir = ROOT / 'docs/user/cli' / beer.PROJECT_ID / 'project'
    assert project_dir.is_dir(), (
        'The BEER two-phase CLI project must use an id naming the instrument'
    )
    page = ROOT / 'docs/dev/verification/pd-neut-tof_ferrite-austenite_beer_joint.py'
    assert page.is_file(), 'BEER needs its own executable independent verification page'
    text = page.read_text()
    assert beer.PROJECT_ID in text and 'reference.json' in text and 'CrySPY' in text, (
        'The BEER verification page must name the delivered project and '
        'the committed independent reference'
    )
    assert 'diffraction-lib' in text and 'uncertainty' in text and 'beer' in text.lower(), (
        'The BEER verification page must explain the external origin and '
        'parameter uncertainty bounds'
    )
    assert (
        'assert ' in text
        and '.fit(' in text
        and 'pytest.skip' not in text
        and 'pytest.xfail' not in text
    ), 'The BEER verification page must execute its fit and its independent comparisons'
    delivered = engine.Project.load(project_dir)
    expected = engine.Project.load(beer.HOME / 'projects/initial')
    for experiment in expected.experiments:
        actual = delivered.experiments[experiment.name]
        for phase in ('ferrite', 'austenite'):
            actual_scale = support.links(actual)[phase].scale
            expected_scale = support.links(experiment)[phase].scale
            assert actual_scale.value == expected_scale.value, (
                'The delivered BEER project must use the converted independent-bank scale input'
            )
            assert actual_scale.free == expected_scale.free, (
                'The delivered BEER project must fit all four unconstrained bank phase scales'
            )
        np.testing.assert_array_equal(
            np.asarray(actual.data.intensity_meas),
            np.asarray(experiment.data.intensity_meas),
            err_msg=(
                'The BEER CLI project must use every committed measured value '
                'from both source banks'
            ),
        )
        np.testing.assert_array_equal(
            np.asarray(actual.data.intensity_meas_su),
            np.asarray(experiment.data.intensity_meas_su),
            err_msg='The BEER CLI project must retain every source measurement uncertainty',
        )
