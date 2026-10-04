"""Hidden acceptance gates for 's surviving core-owned EDI I/O."""

from __future__ import annotations

import hashlib
import json
import math
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


def test_e02_t2_frozen_fixture_and_independent_references_are_locked() -> None:
    manifest = _load_json('manifest.json')
    assert manifest['schema'] == 2
    assert manifest['crysta'] == {
        'loader': 'crysta::load_project',
        'pin': 'e1f0452810006d1dd529f26a26cbcd3ad835f33c',
        'source_path': 'tools/spikes/ncaf_5bank_edi_converged_jorgensen',
    }, ' must lock the independent Crysta oracle source and its renamed loader spelling'
    assert manifest['published_structure'] == {
        'authors': 'G. Courbion and G. Férey',
        'journal': 'Journal of Solid State Chemistry 76 (1988) 426-431',
        'doi': '10.1016/0022-4596(88)90239-3',
        'cod_id': 1000236,
        'cod_revision': 130149,
        'cod_sha256': 'fef30351157a406336d44b35a416bfd848810b54112077b733b0fd7ca6142ae9',
        'source_file': 'published_cod_1000236.cif',
        'source_url': 'https://www.crystallography.net/cod/1000236.cif@130149',
        'role': 'independent published structural-value oracle',
    }
    # File hashes are regression/provenance pins for the migrated schema-2 corpus.  Correctness
    # comes from the separately generated direct-crysta snapshot and published COD values below.
    for relative, expected_hash in manifest['files'].items():
        assert hashlib.sha256((FIXTURE / relative).read_bytes()).hexdigest() == expected_hash
    assert sorted(path.name for path in (PROJECT / 'experiments').glob('*.edi')) == [
        'wish_1_10.edi',
        'wish_2_9.edi',
        'wish_3_8.edi',
        'wish_4_7.edi',
        'wish_5_6.edi',
    ]


def test_e02_t2_project_load_matches_pinned_crysta_loader_parameter_sets() -> None:
    loaded = edi.Project.load(PROJECT)
    actual = _project_snapshot(loaded)
    expected = _load_json('crysta_reference.json')
    # The independently compiled pre-hierarchy C++ snapshot carries the JvD-only Lorentz slots as
    # fixed zeros even for pure Jorgensen banks. I15 makes those illegal union members absent from
    # the concrete Python type; derive that exclusion from the reference's own peak selector.
    jvd_only = {f'peak.{name}' for name in PEAK_PARAMETER_NAMES if 'lorentz_' in name}
    excluded = {
        path
        for path, *_values in expected['parameters']
        if any(
            path == f'experiments[{bank}].{suffix}'
            and expected['metadata'][f'experiments[{bank}].peak.type'] == 'tof-jorgensen'
            for bank in ('wish_1_10', 'wish_2_9', 'wish_3_8', 'wish_4_7', 'wish_5_6')
            for suffix in jvd_only
        )
    }
    assert not excluded & {row[0] for row in actual['parameters']}, (
        'pure Jorgensen concrete types must not expose JvD-only Lorentz parameters'
    )
    expected['parameters'] = [row for row in expected['parameters'] if row[0] not in excluded]
    assert actual == expected, (
        'the live Edi load must match the independent pre-hierarchy reference after removing only '
        'reference-proven illegal union members'
    )


@pytest.mark.parametrize('method_name', ['from_cif_str', 'from_cif_path'])
def test_e02_t2_cif_and_edi_structures_are_model_equivalent(method_name: str) -> None:
    from_edi = edi.Project.load(PROJECT).structure
    source = CIF.read_text(encoding='utf-8') if method_name == 'from_cif_str' else CIF
    from_cif = getattr(edi.StructureFactory, method_name)(source)
    assert _structure_snapshot(from_edi) == _reference_structure(), (
        'the frozen EDI project must still match its independent pre-task Crysta snapshot'
    )
    assert _structure_snapshot(from_cif) == _reference_structure(), (
        'both CIF entry points must parse the real IUCr NCAF twin into the independent snapshot'
    )


@pytest.mark.parametrize('method_name', ['from_cif_str', 'from_cif_path'])
def test_e02_t2_published_cod_structure_matches_hand_pinned_values(
    method_name: str,
) -> None:
    source = (
        PUBLISHED_CIF.read_text(encoding='utf-8')
        if method_name == 'from_cif_str'
        else PUBLISHED_CIF
    )
    structure = getattr(edi.StructureFactory, method_name)(source)
    assert structure.space_group.name_h_m == 'I 21 3', (
        'COD 1000236 revision 130149 reports space group I 21 3'
    )
    for name, (expected_value, expected_uncertainty) in PUBLISHED_CELL.items():
        parameter = getattr(structure.cell, name)
        assert float(parameter.value) == pytest.approx(expected_value, abs=1e-12), (
            'cell values must come from COD 1000236 revision 130149',
            name,
        )
        assert float(parameter.uncertainty) == pytest.approx(expected_uncertainty, abs=1e-12), (
            'cell uncertainties must come from COD 1000236 revision 130149',
            name,
        )

    sites = {str(site.id): site for site in _as_sequence(structure.atom_sites)}
    assert set(sites) == set(PUBLISHED_SITES), (
        'the parsed atom labels must equal the published COD 1000236 sites'
    )
    for label, (element, wyckoff, coordinates, occupancy, u_diagonal) in PUBLISHED_SITES.items():
        site = sites[label]
        assert str(site.type_symbol) == element, ('published atom type mismatch', label)
        assert str(site.wyckoff_letter) == wyckoff, ('published Wyckoff letter mismatch', label)
        actual_coordinates = tuple(
            float(getattr(site, name).value) for name in ('fract_x', 'fract_y', 'fract_z')
        )
        assert actual_coordinates == pytest.approx(coordinates, abs=1e-12), (
            'published fractional coordinates must match COD 1000236 revision 130149',
            label,
        )
        assert float(site.occupancy.value) == pytest.approx(occupancy, abs=1e-12), (
            'published site occupancy mismatch',
            label,
        )
        expected_b_eq = 8.0 * math.pi**2 * sum(u_diagonal) / 3.0
        assert float(site.adp_iso.value) == pytest.approx(expected_b_eq, abs=1e-12), (
            'published anisotropic U diagonal must convert to B-equivalent',
            label,
        )


def test_e02_t2_truncated_edi_is_rejected_without_partial_model(tmp_path: Path) -> None:
    path = _mutated_project(tmp_path, lambda text: text.rsplit(' ', 1)[0] + '\n')
    _assert_structured_rejection(lambda: edi.Project.load(path))


def test_e02_t2_unknown_edi_block_is_rejected_without_partial_model(tmp_path: Path) -> None:
    path = _mutated_project(tmp_path, lambda text: text + '\ndata_unexpected\n_probe.value 1\n')
    _assert_structured_rejection(lambda: edi.Project.load(path))


def test_e02_t2_non_finite_numeric_is_rejected_without_partial_model(tmp_path: Path) -> None:
    path = _mutated_project(tmp_path, lambda text: text.replace('10.250256', 'nan', 1))
    _assert_structured_rejection(lambda: edi.Project.load(path))


def test_e02_t2_wrong_format_handoff_is_rejected_without_partial_model() -> None:
    _assert_structured_rejection(lambda: edi.Project.load(CIF))


@pytest.mark.parametrize(
    'mutate',
    [
        pytest.param(
            lambda text: text.replace('_peak.type tof-jorgensen', '_peak.type pseudo-voigt', 1),
            id='unknown-peak-selector',
        ),
        pytest.param(
            lambda text: text.replace(
                '_background.type line-segment', '_background.type spline', 1
            ),
            id='unknown-background-selector',
        ),
        pytest.param(
            lambda text: text.replace('_background.type line-segment\n', '', 1),
            id='background-body-without-selector',
        ),
        pytest.param(
            lambda text: text.replace(
                '_background.type line-segment',
                '_background.type line-segment\n_background.order 3',
                1,
            ),
            id='selector-body-mismatch',
        ),
    ],
)
def test_e02_t2_format_discriminator_rejects_unsupported_selector_bodies(
    tmp_path: Path, mutate: Callable[[str], str]
) -> None:
    path = _mutated_experiment_project(tmp_path, mutate)
    _assert_structured_rejection(lambda: edi.Project.load(path))


@pytest.mark.parametrize(
    'replacement',
    [
        pytest.param(
            'loop_\n_background.intensity\n465\n',
            id='intensity-only-loop',
        ),
        pytest.param(
            '_background.position 9162\n_background.intensity 465\n',
            id='scalar-items',
        ),
        pytest.param(
            'loop_\n_background.position\n9162\n\nloop_\n_background.intensity\n465\n',
            id='split-loops',
        ),
    ],
)
def test_e02_t2_line_segment_body_requires_both_columns_in_one_loop(
    tmp_path: Path, replacement: str
) -> None:
    path = _mutated_experiment_project(
        tmp_path, lambda text: _replace_background_body(text, replacement)
    )
    _assert_structured_rejection(lambda: edi.Project.load(path))


@pytest.mark.parametrize('entity', ['structure', 'experiment'])
def test_e02_t2_save_as_rejects_entity_path_traversal_without_escape(
    tmp_path: Path, entity: str
) -> None:
    project = edi.Project.load(PROJECT)
    escape_name = f'escaped-{entity}'
    if entity == 'structure':
        structure = project.structure
        structure.name = f'../../{escape_name}'
        project.structure = structure
    else:
        project.experiments[0].name = f'../../{escape_name}'

    destination = tmp_path / 'saved-project'
    _assert_structured_rejection(lambda: project.save_as(destination))
    assert not destination.exists()
    assert not (tmp_path / f'{escape_name}.edi').exists()


def test_e02_t2_save_as_rejects_duplicate_experiment_names_before_writing(
    tmp_path: Path,
) -> None:
    project = edi.Project.load(PROJECT)
    # Before: admit a duplicate then refuse save. After : refuse at
    # the setter, retain both original ids and leave the destination untouched.
    names = [item.name for item in project.experiments]
    destination = tmp_path / 'saved-project'
    with pytest.raises(ValueError, match=names[0]):
        project.experiments[1].name = names[0]
    assert [item.name for item in project.experiments] == names, (
        ' duplicate experiment rename preserves original membership'
    )
    assert not destination.exists(), ' refused rename cannot publish a project'


def test_e02_t2_late_save_failure_preserves_the_complete_prior_destination(
    tmp_path: Path,
) -> None:
    destination = tmp_path / 'saved-project'
    shutil.copytree(PROJECT, destination)
    before = _tree_bytes(destination)

    project = edi.Project.load(PROJECT)
    structure = project.structure
    structure.space_group.name_h_m = 'P 1'
    project.structure = structure
    project.experiments[1].name = 'x' * 300

    _assert_structured_rejection(lambda: project.save_as(destination))
    assert _tree_bytes(destination) == before
    assert not destination.with_name(destination.name + '.edi-save-staging').exists()
    assert not destination.with_name(destination.name + '.edi-save-previous').exists()
