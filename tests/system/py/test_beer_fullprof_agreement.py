"""Two-bank agreement with the unchanged owner-supplied FullProf result."""

import hashlib
import json
import shutil
from pathlib import Path

import edi as engine
import numpy as np

from tests.fixtures.multiphase import beer

ROOT = Path(__file__).resolve().parents[3]
HOME = ROOT / 'tests/fixtures/cwl_family'
REFERENCE = json.loads((HOME / 'beer-fullprof.json').read_text())
PROJECT = ROOT / 'docs/user/cli/pd-neut-tof_ferrite-austenite-beer_joint/project'


def test_fullprof_beer_reference_preserves_all_independent_variables():
    assert (
        hashlib.sha256((HOME / 'beer-fullprof.json').read_bytes()).hexdigest()
        == 'dc534e7c88ecc9c701076ad03face1ebc8f7ec8a808228cceba2a29143ad50df'
    ), 'The parsed BEER expectations must retain their independently captured FullProf values'
    assert len(REFERENCE['parameters']) == REFERENCE['n_free'] + 1 == 76, (
        'The BEER comparison must cover every free variable plus both copies of shared Biso'
    )
    assert (
        REFERENCE['parameters']['ferrite.atom_site.Fe.adp_iso']
        == REFERENCE['parameters']['austenite.atom_site.Fe.adp_iso']
    ), 'Both Fe sites must retain the FullProf code-81 value and standard uncertainty'


def loaded(tmp_path):
    destination = tmp_path / 'project'
    shutil.copytree(PROJECT, destination)
    return engine.Project.load(destination)


def test_delivered_beer_project_preserves_shared_biso_and_free_set(tmp_path):
    project = loaded(tmp_path)
    assert len(project.analysis.constraints) == 1, (
        'The BEER project must declare the FullProf cross-phase Biso equality'
    )
    assert len(project.free_parameters) == REFERENCE['n_free'], (
        'The BEER project must solve the same independent parameter count as FullProf'
    )
    for phase in ('ferrite', 'austenite'):
        assert project.structures[phase].atom_sites[0].occupancy.value == 1, (
            'Both fully occupied Fe sites must undo FullProf site/general multiplicity'
        )
    for i, value in enumerate((0.83, 1.47)):
        source = project.structures['ferrite'].atom_sites[0].adp_iso
        target = project.structures['austenite'].atom_sites[0].adp_iso
        independent = target if source.user_constrained else source
        independent.value = value
        project.analysis.calculate()
        assert source.value == target.value == value, (
            'The shared Biso relation must update both phases at a nonidentity trial value'
        )
        path = tmp_path / f'saved-{i}'
        project.save_as(path)
        project = engine.Project.load(path)
        assert len(project.analysis.constraints) == 1, (
            'Every BEER save cycle must preserve the active cross-phase Biso constraint'
        )


def test_beer_fit_agrees_with_every_fullprof_parameter(tmp_path, record_property):
    project = loaded(tmp_path)
    assert len(project.analysis.constraints) == 1, (
        'BEER agreement requires the declared shared Biso before fitting'
    )
    assert len(project.free_parameters) == REFERENCE['n_free'], (
        'BEER agreement must fit the complete external free set'
    )
    project.analysis.fit()
    actual = beer.actual_values(project, REFERENCE['parameters'])
    failures = [
        key
        for key, (value, su) in REFERENCE['parameters'].items()
        if not abs(actual[key] - value) <= su
    ]
    assert not failures, (
        'Every fitted BEER parameter must agree within its FullProf standard uncertainty: '
        + ', '.join(failures)
    )
    project.analysis.calculate()
    for experiment in project.experiments:
        x = np.asarray(experiment.data.time_of_flight)
        use = (x >= 40158.2305) & (x < 130000)
        y = np.asarray(experiment.data.intensity_meas)[use]
        su = np.asarray(experiment.data.intensity_meas_su)[use]
        calc = np.asarray(experiment.data.intensity_calc)[use]
        rwp = float(np.sqrt(np.sum(((y - calc) / su) ** 2) / np.sum((y / su) ** 2)))
        ratio = rwp / REFERENCE['rwp'][experiment.name]
        record_property(experiment.name + '_rwp_relative_to_fullprof', ratio)
        assert np.isfinite(ratio), 'Each BEER bank must yield a finite Rwp comparison'
        assert ratio > 0, 'Each BEER bank must report a finite Rwp comparison on included points'
