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
        == 'd1db452ea46531ec8d9ab2b31360a4b0487bc03c34a29e9db6fe1aef960a6df8'
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
    assert all(s['success'] for s in ref['stages']), (
        'The BEER reference must preserve both successful tutorial fit stages'
    )
    assert len(ref['stages'][0]['parameters']) == 54, (
        'The first BEER fit must retain all backgrounds'
    )
    assert len(ref['stages'][1]['parameters']) == 14, (
        'The BEER reference must include all first-stage backgrounds and '
        'every second-stage parameter'
    )
    assert all(
        math.isfinite(p['value']) and math.isfinite(p['su']) and p['su'] > 0
        for stage in ref['stages']
        for p in stage['parameters'].values()
    ), 'Every BEER comparison needs a finite external value and its positive reported uncertainty'


def test_beer_two_phases_and_bank_constraints_survive_two_save_cycles(tmp_path):
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
        assert all(
            word in text
            for word in (
                's2_ferrite_scale',
                's2_austenite_scale',
                'n2_ferrite_scale',
                'n2_austenite_scale',
                'n2_ferrite_scale = s2_ferrite_scale',
                'n2_austenite_scale = s2_austenite_scale',
            )
        ), 'Both cross-bank phase-scale constraints must persist after every save cycle'
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
    assert len(project.free_parameters) == 54, (
        'The BEER first stage must fit every tutorial parameter with both '
        'bank scale constraints applied'
    )
    for stage in ref['stages']:
        result = project.fit()
        assert result.converged, (
            'Each BEER tutorial stage must report a completed converged joint fit'
        )
        values = beer.actual_values(project, stage['parameters'])
        assert all(
            abs(values[key] - p['value']) <= p['su'] for key, p in stage['parameters'].items()
        ), (
            'Every BEER fitted parameter must agree within its own '
            'independent reported standard uncertainty'
        )
        assert abs(beer.active_rwp(project) / stage['active_rwp'] - 1) <= 0.05, (
            'BEER fit quality on the included windows must agree within five '
            'percent relative to the external run'
        )
        for experiment in project.experiments:
            for point in experiment.background:
                point.intensity.free = False
    assert len(project.free_parameters) == 14, (
        'Fixing only BEER backgrounds must leave all fourteen second-stage parameters free'
    )
    for name in ('ferrite', 'austenite'):
        expected = ref['stages'][-1]['parameters'][f'expt_s2.linked_structure.{name}.scale']
        for experiment in project.experiments:
            assert (
                abs(support.links(experiment)[name].scale.value - expected['value'])
                <= expected['su']
            ), (
                'Both banks must recover each distinct constrained BEER phase '
                'scale within its external uncertainty'
            )
    final = beer.actual_values(project, ref['stages'][-1]['parameters'])
    saved = tmp_path / 'fitted-saved'
    project.save_as(saved)
    reopened = engine.Project.load(saved)
    assert beer.actual_values(reopened, final) == final, (
        'Every fitted BEER phase, profile and calibration value must '
        'survive save and reopen exactly'
    )
    assert len(reopened.free_parameters) == 14, (
        'BEER save and reopen must retain the free set and both constrained phase scales'
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
