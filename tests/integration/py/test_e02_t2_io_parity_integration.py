"""Hidden acceptance gates for 's core-owned EDI and CIF I/O."""

from __future__ import annotations

import json
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

import edi
import pytest

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / 'tests/fixtures/e02_t2_ncaf_5bank'
PROJECT = FIXTURE / 'project'
CIF = FIXTURE / 'ncaf.cif'
PUBLISHED_CIF = FIXTURE / 'published_cod_1000236.cif'
CELL_NAMES = (
    'length_a',
    'length_b',
    'length_c',
    'angle_alpha',
    'angle_beta',
    'angle_gamma',
)
SITE_PARAMETER_NAMES = ('fract_x', 'fract_y', 'fract_z', 'occupancy', 'adp_iso')
PEAK_PARAMETER_NAMES = (
    'rise_alpha_0',
    'rise_alpha_1',
    'decay_beta_0',
    'decay_beta_1',
    'broad_gauss_sigma_0',
    'broad_gauss_sigma_1',
    'broad_gauss_sigma_2',
    'broad_gauss_size',
    'broad_gauss_strain',
    'broad_lorentz_gamma_0',
    'broad_lorentz_gamma_1',
    'broad_lorentz_gamma_2',
    'broad_lorentz_size',
    'broad_lorentz_strain',
)
INSTRUMENT_PARAMETER_NAMES = (
    'calib_d_to_tof_offset',
    'calib_d_to_tof_linear',
    'calib_d_to_tof_quadratic',
)
PUBLISHED_CELL = {
    'length_a': (10.257, 0.001),
    'length_b': (10.257, 0.001),
    'length_c': (10.257, 0.001),
    'angle_alpha': (90.0, 0.0),
    'angle_beta': (90.0, 0.0),
    'angle_gamma': (90.0, 0.0),
}
PUBLISHED_SITES = {
    'Ca1': ('Ca', 'b', (0.4667, 0.0, 0.25), 1.0, (0.0078, 0.0091, 0.0078)),
    'Al1': ('Al', 'a', (0.2482, 0.2482, 0.2482), 1.0, (0.0075, 0.0075, 0.0075)),
    'Na1': ('Na', 'a', (0.0847, 0.0847, 0.0847), 1.0, (0.0273, 0.0273, 0.0273)),
    'F1': ('F', 'c', (0.1387, 0.3062, 0.1206), 1.0, (0.0114, 0.0127, 0.0125)),
    'F2': ('F', 'c', (0.3640, 0.3627, 0.1873), 1.0, (0.0131, 0.0147, 0.0154)),
    'F3': ('F', 'a', (0.4614, 0.4614, 0.4614), 1.0, (0.0104, 0.0104, 0.0104)),
}


def _load_json(name: str) -> dict[str, Any]:
    return json.loads((FIXTURE / name).read_text())


def _parameter_triplet(parameter: object) -> list[object]:
    return [float(parameter.value), float(parameter.uncertainty), bool(parameter.free)]


def _as_sequence(value: object) -> list[object]:
    if isinstance(value, dict):
        return list(value.values())
    values = getattr(value, 'values', None)
    if callable(values):
        return list(values())
    return list(value)  # type: ignore[arg-type]


def _peak_type_token(value: object) -> str:
    return {
        'PeakProfileTypeEnum.TOF_JORGENSEN': 'tof-jorgensen',
        'PeakProfileTypeEnum.TOF_JORGENSEN_VON_DREELE': 'tof-jorgensen-von-dreele',
        'PeakProfileTypeEnum.CWL_PSEUDO_VOIGT': 'cwl-pseudo-voigt',
    }[str(value)]


def _project_snapshot(project: object) -> dict[str, object]:
    parameters: list[list[object]] = []
    metadata: dict[str, object] = {}
    structure = project.structure

    parameters.extend(
        [
            f'structure.cell.{name}',
            *_parameter_triplet(getattr(structure.cell, name)),
        ]
        for name in CELL_NAMES
    )
    metadata['structure.space_group.name_h_m'] = str(structure.space_group.name_h_m)

    for site in _as_sequence(structure.atom_sites):
        label = str(site.id)
        prefix = f'structure.atom_sites[{label}].'
        metadata[prefix + 'type_symbol'] = str(site.type_symbol)
        metadata[prefix + 'wyckoff_letter'] = str(site.wyckoff_letter)
        parameters.extend(
            [prefix + name, *_parameter_triplet(getattr(site, name))]
            for name in SITE_PARAMETER_NAMES
        )

    metadata['analysis.fitting_mode'] = str(project.analysis.fitting_mode)
    for experiment in _as_sequence(project.experiments):
        name = str(experiment.name)
        prefix = f'experiments[{name}].'
        metadata[prefix + 'peak.type'] = _peak_type_token(experiment.peak.type)
        metadata[prefix + 'instrument.setup_twotheta_bank'] = float(
            experiment.instrument.setup_twotheta_bank.value
        )
        metadata[prefix + 'peak.cutoff_fwhm'] = float(experiment.peak.cutoff_fwhm)
        metadata[prefix + 'dataset_weight'] = float(experiment.dataset_weight)
        metadata[prefix + 'excluded_regions'] = [
            [float(start), float(end)] for start, end in experiment.excluded_regions
        ]
        parameters.extend(
            [
                prefix + 'peak.' + parameter_name,
                *_parameter_triplet(getattr(experiment.peak, parameter_name)),
            ]
            for parameter_name in PEAK_PARAMETER_NAMES
            if hasattr(experiment.peak, parameter_name)
        )
        parameters.extend(
            [
                prefix + 'instrument.' + parameter_name,
                *_parameter_triplet(getattr(experiment.instrument, parameter_name)),
            ]
            for parameter_name in INSTRUMENT_PARAMETER_NAMES
            if hasattr(experiment.instrument, parameter_name)
        )
        parameters.append([
            prefix + 'linked_structure.scale',
            *_parameter_triplet(experiment.linked_structure.scale),
        ])
        background = _as_sequence(experiment.background)
        metadata[prefix + 'background.count'] = len(background)
        for index, point in enumerate(background):
            point_prefix = prefix + f'background.{index}.'
            metadata[point_prefix + 'position'] = float(point.position)
            parameters.append([point_prefix + 'intensity', *_parameter_triplet(point.intensity)])

    return {
        'parameters': parameters,
        'metadata': metadata,
    }


def test_e02_t2_edi_save_reload_preserves_semantics(tmp_path: Path) -> None:
    original = edi.Project.load(PROJECT)
    expected = _project_snapshot(original)
    destination = tmp_path / 'saved-project'
    original.save_as(destination)
    assert (destination / 'analysis/analysis.edi').is_file()
    assert len(list((destination / 'structures').glob('*.edi'))) == 1
    assert len(list((destination / 'experiments').glob('*.edi'))) == 5
    assert _project_snapshot(edi.Project.load(destination)) == expected


def _structure_snapshot(structure: object) -> dict[str, object]:
    snapshot = _project_snapshot(_StructureProjectView(structure))
    parameters = [
        [path, value, esd]
        for path, value, esd, _free in snapshot['parameters']
        if str(path).startswith('structure.')
    ]
    metadata = {
        key: value for key, value in snapshot['metadata'].items() if key.startswith('structure.')
    }
    return {'parameters': parameters, 'metadata': metadata}


class _StructureProjectView:
    def __init__(self, structure: object) -> None:
        self.structure = structure
        self.analysis = type('_AnalysisView', (), {'fitting_mode': ''})()
        self.experiments: tuple[()] = ()


def _reference_structure() -> dict[str, object]:
    reference = _load_json('crysta_reference.json')
    parameters = [
        [path, value, esd]
        for path, value, esd, _free in reference['parameters']
        if path.startswith('structure.')
    ]
    metadata = {
        key: value for key, value in reference['metadata'].items() if key.startswith('structure.')
    }
    return {'parameters': parameters, 'metadata': metadata}


def _assert_structured_rejection(operation: Callable[[], object]) -> None:
    with pytest.raises(Exception, match=r'.+') as captured:
        operation()
    error = captured.value
    diagnostics = getattr(error, 'diagnostics', None)
    assert diagnostics, 'input rejection must expose non-empty structured diagnostics'
    for diagnostic in diagnostics:
        if isinstance(diagnostic, dict):
            assert diagnostic.get('code')
            assert diagnostic.get('message')
        else:
            assert getattr(diagnostic, 'code', None)
            assert getattr(diagnostic, 'message', None)
    assert getattr(error, 'partial_model', None) is None


def _mutated_project(tmp_path: Path, mutate: Callable[[str], str]) -> Path:
    destination = tmp_path / 'project'
    shutil.copytree(PROJECT, destination)
    structure = destination / 'structures/ncaf.edi'
    structure.write_text(mutate(structure.read_text()))
    return destination


def _mutated_experiment_project(tmp_path: Path, mutate: Callable[[str], str]) -> Path:
    destination = tmp_path / 'project'
    shutil.copytree(PROJECT, destination)
    experiment = destination / 'experiments/wish_1_10.edi'
    experiment.write_text(mutate(experiment.read_text()))
    return destination


def _replace_background_body(text: str, replacement: str) -> str:
    marker = 'loop_\n_background.id\n_background.position\n_background.intensity\n'
    assert marker in text
    return text[: text.index(marker)] + replacement


def _tree_bytes(root: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in sorted(root.rglob('*'))
        if path.is_file()
    }


def test_e02_t2_save_as_replaces_the_complete_destination_without_stale_files(
    tmp_path: Path,
) -> None:
    destination = tmp_path / 'saved-project'
    shutil.copytree(PROJECT, destination)
    stale = destination / 'experiments/stale-bank.edi'
    stale.write_text('data_stale\n')

    project = edi.Project.load(PROJECT)
    expected = _project_snapshot(project)
    project.save_as(destination)

    assert not stale.exists()
    assert _project_snapshot(edi.Project.load(destination)) == expected
