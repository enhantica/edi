"""BEER structural behavior; external FullProf agreement is inactive."""

import math
from pathlib import Path

import edi as engine
import numpy as np

from tests.fixtures.multiphase import beer, support

ROOT = Path(__file__).resolve().parents[3]


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


def test_beer_joint_fit_preserves_both_phases_and_independent_bank_scales(tmp_path):
    project = engine.Project.load(beer.write_initial(tmp_path / 'fit'))
    first_count = len(project.free_parameters)
    background_count = sum(len(experiment.background) for experiment in project.experiments)
    assert all(
        point.intensity.free
        for experiment in project.experiments
        for point in experiment.background
    ), 'The BEER behavior vehicle must start with independently free background points'
    initial_rwp = beer.active_rwp(project)
    for _ in range(2):
        result = project.analysis.fit()
        assert result.converged, 'Each BEER stage must complete its declared joint fit'
        current_rwp = beer.active_rwp(project)
        assert math.isfinite(current_rwp) and current_rwp < initial_rwp, (
            'A BEER joint fit must improve the included-window residual from its starting model'
        )
        assert set(project.structures.keys()) == {'ferrite', 'austenite'}, (
            'The BEER joint fit must retain both independent structures'
        )
        assert set(project.experiments.keys()) == {'expt_s2', 'expt_n2'}, (
            'The BEER joint fit must retain both banks'
        )
        for experiment in project.experiments:
            for phase in ('ferrite', 'austenite'):
                scale = support.links(experiment)[phase].scale
                assert scale.free and math.isfinite(scale.value) and scale.value > 0, (
                    'Both phase scales in each bank must remain independent finite free parameters'
                )
            for point in experiment.background:
                point.intensity.free = False
        expected_count = first_count - background_count
        assert len(project.free_parameters) == expected_count, (
            'Fixing only BEER background points must preserve every other free parameter'
        )
    scales = {
        (experiment.name, phase): support.links(experiment)[phase].scale.value
        for experiment in project.experiments
        for phase in ('ferrite', 'austenite')
    }
    before = {
        experiment.name: np.asarray(experiment.data.intensity_calc).copy()
        for experiment in project.experiments
    }
    saved = tmp_path / 'fitted-saved'
    project.save_as(saved)
    reopened = engine.Project.load(saved)
    assert len(reopened.free_parameters) == expected_count, (
        'Saving a fitted BEER project must retain its complete free-parameter set'
    )
    reopened.analysis.calculate()
    for experiment in reopened.experiments:
        for phase in ('ferrite', 'austenite'):
            assert (
                support.links(experiment)[phase].scale.value == scales[experiment.name, phase]
            ), 'Every independently fitted BEER bank phase scale must survive save and reopen'
        np.testing.assert_array_equal(
            np.asarray(experiment.data.intensity_calc),
            before[experiment.name],
            err_msg='A fitted BEER project must preserve each complete calculated bank on reopen',
        )
