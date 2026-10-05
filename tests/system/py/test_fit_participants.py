"""Fit admissibility follows only enabled participants of the requested problem."""

import os
from pathlib import Path

import edi as engine
import numpy as np
import pytest

from tests.fixtures.multiphase import participants as case
from tests.fixtures.multiphase import support


@pytest.mark.parametrize('key', case.GRAPHS)
@pytest.mark.parametrize('reverse', [False, True], ids=['forward', 'reverse'])
@pytest.mark.parametrize('entry', ['joint', 'analysis'])
def test_each_active_component_needs_its_own_anchor(tmp_path, key, reverse, entry):
    project = engine.Project.load(str(case.graph(tmp_path / 'input', key, reverse=reverse)))
    if not case.GRAPHS[key][3]:
        with pytest.raises(ValueError, match=r'dilation|null direction'):
            project.fit_joint(
                should_cancel=lambda: True
            ) if entry == 'joint' else project.analysis.fit(should_cancel=lambda: True)
    else:
        result = (
            project.fit_joint(should_cancel=lambda: True)
            if entry == 'joint'
            else project.analysis.fit(should_cancel=lambda: True)
        )
        assert result is not None, 'Every independently anchored active component must be admitted'


@pytest.mark.parametrize(
    'key', ['foreign-wavelength', 'foreign-cell', 'inactive-fixed-bank', 'connected-unanchored']
)
def test_fit_identifiability_is_not_a_load_calculate_or_save_precondition(tmp_path, key):
    project = engine.Project.load(str(case.graph(tmp_path / 'input', key)))
    project.analysis.calculate()
    before = [np.asarray(bank.data.intensity_calc).copy() for bank in project.experiments]
    assert all(np.isfinite(values).all() for values in before), (
        'A singular fit graph must remain calculable'
    )
    project.save_as(str(tmp_path / 'saved'))
    carried = engine.Project.load(str(tmp_path / 'saved'))
    carried.analysis.calculate()
    for values, bank in zip(before, carried.experiments, strict=True):
        np.testing.assert_array_equal(
            np.asarray(bank.data.intensity_calc),
            values,
            err_msg='Saving a calculable model must preserve it when fitting would be singular',
        )


def test_warm_disabled_bridge_removes_its_anchor_and_reenabling_restores_it(tmp_path):
    project = engine.Project.load(str(case.graph(tmp_path / 'input', 'connected-wavelength')))
    project.fit_joint(should_cancel=lambda: True)
    support.enable(support.links(project.experiments['q'])['alpha'], value=False)
    with pytest.raises(ValueError, match=r'dilation|null direction'):
        project.fit_joint(should_cancel=lambda: True)
    support.enable(support.links(project.experiments['q'])['alpha'], value=True)
    project.fit_joint(should_cancel=lambda: True)


@pytest.mark.parametrize('entry', ['single', 'analysis-single', 'joint', 'analysis-joint'])
@pytest.mark.parametrize(
    'selection', ['other-bank-empty', 'disabled-empty', 'unused-empty-first', 'selected-empty']
)
@pytest.mark.parametrize('reverse', [False, True], ids=['forward', 'reverse'])
def test_atom_site_requirement_matches_the_requested_banks(tmp_path, entry, selection, reverse):
    single = 'single' in entry
    edges = {'p': [('alpha', True)], 'q': [('beta', True)]}
    empty = {'beta'}
    if selection == 'disabled-empty':
        edges['q'] = [('alpha', True), ('beta', False)]
    elif selection == 'unused-empty-first':
        edges = {'p': [('beta', True)], 'q': [('beta', True)]}
        empty = {'alpha'}
    elif selection == 'selected-empty':
        empty = {'alpha'}
    project = engine.Project.load(
        str(
            case.write(
                tmp_path / 'input',
                edges,
                fixed_wavelengths=('p', 'q'),
                reverse=reverse,
                mode='single' if single else 'joint',
            )
        )
    )
    for name in empty:
        project.structures[name].atom_sites.clear()
    # An undeclared one-call single fit of a multi-bank project is also a public path.
    # The analysis facade takes the declared single/joint path on the same project.
    should_refuse = (selection == 'selected-empty' and (not single or not reverse)) or (
        selection == 'other-bank-empty' and (not single or reverse)
    )
    call = (
        project.analysis.fit
        if entry.startswith('analysis')
        else project.fit
        if single
        else project.fit_joint
    )
    if should_refuse:
        with pytest.raises(ValueError, match='no atom sites'):
            call(should_cancel=lambda: True)
    else:
        result = call(should_cancel=lambda: True)
        assert result is not None, (
            'Empty structures outside the requested enabled participants must not prevent fitting'
        )


@pytest.mark.parametrize('entry', ['single', 'joint', 'analysis-single', 'analysis-joint'])
@pytest.mark.parametrize('spelling', ['empty-structure-name', 'empty-link-id'])
def test_canonical_phase_identity_cannot_bypass_active_atom_site_requirement(
    tmp_path, entry, spelling
):
    root = case.write(
        tmp_path / 'input',
        {'p': [('alpha', True), ('beta', True)], 'q': [('beta', True)]},
        fixed_wavelengths=('p', 'q'),
        mode='single' if 'single' in entry else 'joint',
    )
    path = root / 'structures/alpha.edi'
    path.write_text(path.read_text().replace('data_alpha', 'data_structure'))
    for path in (root / 'experiments').glob('*.edi'):
        path.write_text(path.read_text().replace('alpha 1.125()', 'structure 1.125()'))
    project = engine.Project.load(str(root))
    project.structures['structure'].atom_sites.clear()
    if spelling == 'empty-structure-name':
        project.structures['structure'].name = ''
    else:
        support.links(project.experiments['p'])['structure'].structure_id = ''
    call = (
        project.analysis.fit
        if entry.startswith('analysis')
        else project.fit
        if entry == 'single'
        else project.fit_joint
    )
    with pytest.raises(ValueError, match='no atom sites'):
        call(should_cancel=lambda: True)


def test_singleton_unnamed_link_compatibility_still_validates_its_atoms(tmp_path):
    root = case.write(
        tmp_path / 'input',
        {'p': [('alpha', True)]},
        fixed_wavelengths={'p'},
        mode='single',
    )
    (root / 'structures/beta.edi').unlink()
    project = engine.Project.load(str(root))
    project.structures['alpha'].atom_sites.clear()
    support.links(project.experiments['p'])['alpha'].structure_id = ''
    with pytest.raises(ValueError, match='no atom sites'):
        project.fit(should_cancel=lambda: True)


def test_mixed_beam_families_remain_refused_for_joint_fit(tmp_path):

    corpus = Path(os.environ['EDI_CRYSTA_CORPUS_ROOT'])
    text = (corpus.parent / 'fixtures/c11_t57_profiles/tof/model.edi').read_text()
    project = engine.Project.load(str(case.mixed(tmp_path / 'input', text)))
    with pytest.raises(ValueError, match=r'mixed|homogeneous|same.*kind|same.*family|uniform'):
        project.analysis.fit(should_cancel=lambda: True)
