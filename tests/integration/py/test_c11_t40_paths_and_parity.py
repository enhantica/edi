"""Hidden  gates for path grammar, shortcuts, seams, and parity docs."""

from __future__ import annotations

import re
from pathlib import Path

import edi
import pytest
from c11_t40_helpers import ROOT, make_schema_2_project, oracle


def test_c11_t40_nested_categories_are_live_references(
    tmp_path: Path,
) -> None:
    project = edi.Project.load(make_schema_2_project(tmp_path))
    project.experiment.peak.broad_gauss_sigma_0.value = 8.25
    assert project.experiment.peak.broad_gauss_sigma_0.value == 8.25, (
        'the nested peak category must preserve the assigned value'
    )
    assert project.experiments[0].peak.broad_gauss_sigma_0.value == 8.25, (
        'the project collection must share nested peak storage'
    )


def test_c11_t40_project_shortcuts_share_storage_and_fail_closed_when_empty() -> None:
    project = edi.Project(name='shortcut-storage')
    project.structures.clear()
    project.experiments.clear()
    with pytest.raises((IndexError, ValueError), match=r'(?i)(structure|empty|first)'):
        _ = project.structure
    with pytest.raises((IndexError, ValueError), match=r'(?i)(experiment|empty|first)'):
        _ = project.experiment

    structure = edi.Structure()
    experiment = edi.BraggPdExperiment()
    project.structure = structure
    project.experiment = experiment
    assert len(project.structures) == len(project.experiments) == 1
    project.structure.cell.length_a.value = 12.75
    assert project.structures[0].cell.length_a.value == 12.75
    assert project.experiment.name == project.experiments[0].name

    assert hasattr(project, 'fitting_mode'), (
        'the project must expose the direct fitting-mode shortcut'
    )
    assert hasattr(project.analysis, 'fitting_mode')
    project.fitting_mode = 'joint'
    assert project.analysis.fitting_mode == 'joint', (
        'setting the project shortcut must update the analysis fitting mode'
    )
    project.analysis.fitting_mode = 'single'
    assert project.fitting_mode == 'single', (
        'setting the analysis fitting mode must update the project shortcut'
    )
    assert callable(project.analysis.fit)
    assert callable(project.analysis.calculate)
    for direct in ('fit', 'fit_joint', 'calculate'):
        assert callable(getattr(project, direct))


def test_c11_t40_factories_accept_only_the_categorised_vocabulary() -> None:
    structure = edi.StructureFactory.from_dict({
        'cell': {'length_a': 10.25},
        'atom_sites': [
            {
                'id': 'Ca',
                'type_symbol': 'Ca',
                'wyckoff_letter': 'a',
                'fract_x': 0.0,
                'fract_y': 0.0,
                'fract_z': 0.0,
                'occupancy': 1.0,
                'adp_iso': 0.5,
            }
        ],
    })
    assert structure.cell.length_a.value == 10.25
    assert structure.atom_sites[0].adp_iso.value == 0.5

    experiment = edi.ExperimentFactory.from_dict({
        'peak': {'broad_gauss_sigma_0': 7.3},
        'instrument': {'calib_d_to_tof_linear': 7476.91},
        'linked_structure': {'scale': 1.5},
        'experiment_type': {'beam_mode': 'time-of-flight'},
    })
    assert experiment.peak.broad_gauss_sigma_0.value == 7.3
    assert experiment.instrument.calib_d_to_tof_linear.value == 7476.91

    for retired in ('a', 'b', 'c', 'alpha', 'beta', 'gamma'):
        with pytest.raises(KeyError, match=r'(?i)(unrecognized|unknown|allowed)'):
            edi.StructureFactory.from_dict({'cell': {retired: 10.25}})
    for retired in ('label', 'element', 'wyckoff', 'b_iso'):
        with pytest.raises(KeyError, match=r'(?i)(unrecognized|unknown|allowed)'):
            edi.StructureFactory.from_dict({'atom_sites': [{retired: 'retired'}]})
    for spec in ({'space_group': 'P 1'}, {'space_group_code': '1'}):
        with pytest.raises((KeyError, TypeError), match=r'(?i)(unrecognized|unknown|category)'):
            edi.StructureFactory.from_dict(spec)

    flat_retired = (
        'sigma0',
        'sigma1',
        'sigma2',
        'gamma0',
        'gamma1',
        'gamma2',
        'size_g',
        'strain_g',
        'size_l',
        'strain_l',
        'alpha0',
        'alpha1',
        'beta0',
        'beta1',
        'zero',
        'dtt1',
        'dtt2',
        'u',
        'v',
        'w',
        'x',
        'y',
        'wavelength',
        'twotheta_offset',
        'scale',
        'structure_id',
        'bank_two_theta_deg',
        'peak_type',
        'absorption_type',
        'abscor1',
        'abscor2',
        'kind',
        'beam_mode',
    )
    for retired in flat_retired:
        with pytest.raises(KeyError, match=r'(?i)(unrecognized|unknown|allowed)'):
            edi.ExperimentFactory.from_dict({retired: 1.0})

    categorised_retired = (
        ('peak', 'sigma0'),
        ('peak', 'sigma1'),
        ('peak', 'sigma2'),
        ('peak', 'gamma0'),
        ('peak', 'gamma1'),
        ('peak', 'gamma2'),
        ('peak', 'size_g'),
        ('peak', 'strain_g'),
        ('peak', 'size_l'),
        ('peak', 'strain_l'),
        ('peak', 'alpha0'),
        ('peak', 'alpha1'),
        ('peak', 'beta0'),
        ('peak', 'beta1'),
        ('peak', 'u'),
        ('peak', 'v'),
        ('peak', 'w'),
        ('peak', 'x'),
        ('peak', 'y'),
        ('instrument', 'zero'),
        ('instrument', 'dtt1'),
        ('instrument', 'dtt2'),
        ('instrument', 'd_to_tof_offset'),
        ('instrument', 'd_to_tof_linear'),
        ('instrument', 'd_to_tof_quadratic'),
        ('instrument', 'twotheta_bank'),
        ('instrument', 'wavelength'),
        ('instrument', 'twotheta_offset'),
    )
    for category, retired in categorised_retired:
        with pytest.raises(KeyError, match=r'(?i)(unrecognized|unknown|allowed)'):
            edi.ExperimentFactory.from_dict({category: {retired: 1.0}})

    for spec in (
        {'experiment_type': {'beam_mode': 'not-a-mode'}},
        {'peak': {'type': 'not-a-profile'}},
    ):
        with pytest.raises(
            (KeyError, ValueError), match=r'(?i)(unknown|unsupported|mode|profile)'
        ):
            edi.ExperimentFactory.from_dict(spec)


def _markdown_tables(text: str) -> list[tuple[list[str], list[list[str]]]]:
    lines = text.splitlines()
    tables: list[tuple[list[str], list[list[str]]]] = []
    index = 0
    while index + 1 < len(lines):
        header = lines[index]
        divider = lines[index + 1]
        if header.startswith('|') and re.fullmatch(r'\|[ :\-|]+\|', divider):
            columns = [cell.strip() for cell in header.strip('|').split('|')]
            rows: list[list[str]] = []
            index += 2
            while index < len(lines) and lines[index].startswith('|'):
                rows.append([cell.strip() for cell in lines[index].strip('|').split('|')])
                index += 1
            tables.append((columns, rows))
            continue
        index += 1
    return tables


def test_c11_t40_parity_document_is_a_complete_machine_readable_diff() -> None:
    document = ROOT / 'docs/dev/design/diffraction-lib-parity.md'
    text = document.read_text(encoding='utf-8')
    assert oracle()['source']['commit'] in text
    tables = _markdown_tables(text)
    by_columns = {tuple(columns): rows for columns, rows in tables}

    divergence_columns = (
        'edi name',
        'diffraction-lib name',
        'surface',
        'justification',
    )
    assert divergence_columns in by_columns
    edi_only_columns = next(
        columns
        for columns in by_columns
        if 'edi name' in columns and 'diffraction-lib name' not in columns
    )
    upstream_only_columns = next(
        columns
        for columns in by_columns
        if 'diffraction-lib name' in columns and 'edi name' not in columns
    )
    assert len(edi_only_columns) >= 2
    assert len(upstream_only_columns) >= 2

    divergences = '\n'.join(' | '.join(row) for row in by_columns[divergence_columns])
    for witness in (
        'abscor1',
        'beam_mode',
        'Enum',
        'PdCwlData',
        'excluded_regions',
        'experiment.dataset_weight',
        'joint_fit.weight',
    ):
        assert witness in divergences

    edi_only = '\n'.join(' | '.join(row) for row in by_columns[edi_only_columns])
    for witness in ('FitResultBase', 'IterationRecord'):
        assert witness in edi_only

    upstream_rows = by_columns[upstream_only_columns]
    documented = {row[0].strip('`') for row in upstream_rows}
    assert documented == set(oracle()['unimplemented_upstream'])
    assert all(
        len(row) == len(upstream_only_columns) and all(cell for cell in row)
        for row in upstream_rows
    )
