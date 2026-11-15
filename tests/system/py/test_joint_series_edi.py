"""Experiment sets persist ordinary constraints and series links preserve their folder."""

import shutil
from pathlib import Path

import edi
import pytest

from tests.fixtures.joint_series import cases

ROOT = Path(__file__).resolve().parents[3]


def make_set(root, *, phases=('phase',)):
    project = edi.Project.load(cases.base_project(root, phases=phases))
    assert hasattr(project, 'experiment_sets'), (
        'The project must expose experiment sets over its ordinary experiment rows'
    )
    group = project.experiment_sets.create(id='banks', template='zeta', members=list(cases.BANKS))
    return project, group


def test_sharing_switch_writes_constraints_and_recognizes_hand_edits(tmp_path):
    project, group = make_set(tmp_path / 'project')
    path = 'peak.broad_gauss_w'
    project.analysis.aliases.create(
        id='same_alpha_peak_broad_gauss_w', param=project.structure.cell.length_a
    )
    group.share(path)
    assert path in group.shared, 'A complete equality tie must read as sharing enabled'
    original = project.analysis.aliases['same_alpha_peak_broad_gauss_w']
    assert original.parameter_unique_name == 'phase.cell.length_a', (
        'Generated sharing ids must preserve an existing alias by choosing a suffix'
    )
    project.experiments['zeta'].peak.broad_gauss_w.value = 0.27
    project.analysis.calculate()
    assert project.experiments['alpha'].peak.broad_gauss_w.value == 0.27, (
        'Sharing must apply an ordinary equality relation to every member'
    )
    project.save_as(tmp_path / 'saved')
    text = (tmp_path / 'saved/analysis/analysis.edi').read_text()
    assert '_alias.parameter_unique_name' in text and '_constraint.expression' in text, (
        'The sharing switch must save the existing typed alias and constraint categories'
    )
    restored = edi.Project.load(tmp_path / 'saved')
    assert path in restored.experiment_sets['banks'].shared, (
        'The sharing switch must be derived from saved relation rows on reopen'
    )
    constraints = list(restored.analysis.constraints)
    assert len(constraints) == 1, 'Two experiments need exactly one equality follower'
    constraints[0].expression += ' + 0.125'
    assert path not in restored.experiment_sets['banks'].shared, (
        'A hand-edited nonequality must make the sharing switch read as off'
    )
    group.unshare(path)
    assert path not in group.shared, 'Unshare must remove the generated tie'
    assert 'same_alpha_peak_broad_gauss_w' in project.analysis.aliases, (
        'Unshare must retain a pre-existing user alias that collided with its generated id'
    )


def test_shared_phase_ratios_keep_distinct_overall_scales_and_three_independents(tmp_path):
    project, group = make_set(tmp_path / 'project', phases=('phase', 'other'))
    project.structures['phase'].cell.length_a.free = False
    project.structures['other'].cell.length_a.free = False
    for bank, scales in zip(cases.BANKS, ((2, 1), (3, 7)), strict=True):
        for phase, value in zip(('phase', 'other'), scales, strict=True):
            project.experiments[bank].linked_structures[phase].scale.value = value
    assert len(project.free_parameters) == 4, 'Two phases in two banks have four unshared scales'
    group.phase_ratios_shared = True
    assert len(project.free_parameters) == 3, (
        'Sharing ratios leaves two leader scales and one member overall scale independent'
    )
    project.analysis.calculate()
    for bank, expected in zip(cases.BANKS, ((2, 1), (3, 1.5)), strict=True):
        got = [
            project.experiments[bank].linked_structures[phase].scale.value
            for phase in ('phase', 'other')
        ]
        assert got == list(expected), (
            'Sharing phase ratios must preserve each bank overall scale and set only its follower'
        )
    project.save_as(tmp_path / 'saved')
    restored = edi.Project.load(tmp_path / 'saved')
    assert restored.experiment_sets['banks'].phase_ratios_shared, (
        'A shared phase ratio must remain enabled from its ordinary saved constraints'
    )


def test_zero_leader_ratio_reference_refuses_without_partial_constraints(tmp_path):
    project, group = make_set(tmp_path / 'project', phases=('phase', 'other'))
    for link in project.experiments['zeta'].linked_structures:
        link.scale.value = 0
    with pytest.raises((ValueError, RuntimeError), match=r'scale|phase|starting'):
        group.phase_ratios_shared = True
    assert not group.phase_ratios_shared and len(project.analysis.constraints) == 0, (
        'All-zero leader scales must refuse sharing before writing any partial relation'
    )


def test_series_save_keeps_one_external_folder_and_patterns_without_per_file_entries(tmp_path):
    root = cases.generated_series(tmp_path / 'project', edi)
    external = tmp_path / 'measured'
    shutil.move(root / 'scan', external)
    analysis = root / 'analysis/analysis.edi'
    analysis.write_text(
        analysis.read_text().replace(
            '_sequential_fit.data_dir scan', f'_sequential_fit.data_dir "{external}"'
        )
    )
    project = edi.Project.load(root)
    project.save_as(tmp_path / 'saved')
    text = (tmp_path / 'saved/analysis/analysis.edi').read_text()
    assert '_sequential_fit_experiment.file_pattern' in text, (
        'Saving a linked series must preserve its one pattern per experiment'
    )
    assert not any(key in text for key in cases.POINTS), (
        'A saved series declaration must not expand into one entry per point or file'
    )
    saved_patterns = list((tmp_path / 'saved').rglob('*.xy'))
    assert not saved_patterns, 'Keeping a series linked must not copy its measured patterns'
    shutil.move(external, tmp_path / 'moved-measured')
    restored = edi.Project.load(tmp_path / 'saved')
    assert len(restored.experiments) == 2, (
        'A missing linked folder must not prevent opening the experiment templates'
    )


def test_scan_adr_amendment_defines_the_join_and_single_experiment_rule():
    text = (ROOT / 'docs/dev/adrs/0026-scan-datasets-and-scale.md').read_text()
    assert 'results_experiments.csv' in text and 'joined by `point`' in text, (
        'The scan storage ADR must amend its one-store contract with the point and experiment join'
    )
    assert 'no second file' in text, (
        'The amended scan ADR must retain the one-experiment exception'
    )
