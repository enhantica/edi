"""Visible smoke tests for the  ``import edi`` project I/O surface.

These exercise the *public API contract* — that ``Project.load``/``save_as`` and ``IoError`` exist
and behave — via representation-level invariants (a save→load fixed point, a structured fail-closed
rejection). They deliberately assert
**no crystallographic reference values**: correctness-against-crysta parity is the job of the
independent-reference hidden gate (tests/hidden). The round-trip fixed point here is a
self-contained structural invariant, not a pinned physics value.
"""

from __future__ import annotations

from pathlib import Path

import edi
import pytest

from tests.fixtures.c34_t28_baseline.generate_bytes import observe


def _sample_project() -> edi.Project:
    """A tiny two-bank project built purely in memory (no file, no oracle values)."""
    structure = edi.Structure()
    structure.name = 'demo'
    structure.space_group.name_h_m = 'P 1'
    structure.cell.length_a = edi.Parameter(5.0)
    structure.cell.length_b = edi.Parameter(5.0)
    structure.cell.length_c = edi.Parameter(5.0)

    site = edi.AtomSite()
    site.id = 'Na1'
    site.type_symbol = 'Na'
    site.wyckoff_letter = 'a'
    site.fract_x = edi.Parameter(0.25, 0.001, True)  # refined
    site.fract_y = edi.Parameter(0.0)  # fixed
    site.fract_z = edi.Parameter(0.5)
    site.occupancy = edi.Parameter(1.0)
    site.adp_iso = edi.Parameter(0.5, 0.01, True)
    structure.atom_sites.add(site)

    experiments = []
    for index, name in enumerate(('bank_a', 'bank_b')):
        experiment = edi.BraggPdExperiment()
        experiment.name = name
        experiment.peak.type = 'tof-jorgensen'
        experiment.linked_structure.structure_id = 'demo'
        experiment.dataset_weight = 1.0
        experiment.instrument.setup_twotheta_bank.value = 90.0 + index
        experiment.peak.cutoff_fwhm = 20.0
        experiment.instrument.calib_d_to_tof_offset = edi.Parameter(2.5, 0.1, True)  # refined
        experiment.instrument.calib_d_to_tof_linear = edi.Parameter(5000.0, 0.1, True)
        experiment.linked_structure.scale = edi.Parameter(3.0, 0.01, True)
        experiment.data = edi.PdTofData(
            time_of_flight=[1000.5, 1001.25, 1002.0],
            intensity_meas=[4.0, 9.0, 16.0],
            intensity_meas_su=[2.0, 3.0, 4.0],
        )
        experiment.excluded_regions = [(0.0, 7000.0)]
        point = edi.LineSegment()
        point.position = 6000.0
        point.intensity = edi.Parameter(280.0, 0.001, True)
        experiment.background = [point]
        experiments.append(experiment)

    project = edi.Project(name='demo')
    project.structure = structure
    project.experiment = experiments[0]
    project.experiments.add(experiments[1])
    project.analysis.fitting_mode = 'joint'
    return project


def _triplet(parameter: edi.Parameter) -> tuple[float, float, bool]:
    return (parameter.value, parameter.uncertainty, parameter.free)


def test_edi_project_save_reload_is_a_representation_fixed_point(tmp_path: Path) -> None:
    project = _sample_project()
    destination = tmp_path / 'demo-project'
    project.save_as(destination)

    reloaded = edi.Project.load(destination)

    assert reloaded.analysis.fitting_mode == 'joint'
    assert reloaded.structure.name == 'demo'
    assert reloaded.structure.space_group.name_h_m == 'P 1'
    assert [experiment.name for experiment in reloaded.experiments] == ['bank_a', 'bank_b']

    original_site = project.structure.atom_sites[0]
    reloaded_site = reloaded.structure.atom_sites[0]
    assert reloaded_site.id == original_site.id
    assert reloaded_site.type_symbol == original_site.type_symbol
    assert reloaded_site.wyckoff_letter == original_site.wyckoff_letter
    # value/esd/free survive the round trip exactly (refined and fixed alike).
    assert _triplet(reloaded_site.fract_x) == _triplet(original_site.fract_x)
    assert _triplet(reloaded_site.fract_y) == _triplet(original_site.fract_y)
    assert _triplet(reloaded_site.adp_iso) == _triplet(original_site.adp_iso)

    for original, restored in zip(project.experiments, reloaded.experiments, strict=True):
        assert _triplet(restored.instrument.calib_d_to_tof_offset) == _triplet(
            original.instrument.calib_d_to_tof_offset
        )
        assert _triplet(restored.linked_structure.scale) == _triplet(
            original.linked_structure.scale
        )
        assert restored.peak.type == original.peak.type
        assert (
            restored.instrument.setup_twotheta_bank.value
            == original.instrument.setup_twotheta_bank.value
        )
        assert restored.excluded_regions == original.excluded_regions
        assert _triplet(restored.background[0].intensity) == _triplet(
            original.background[0].intensity
        )


def test_multiple_structures_and_their_links_survive_two_save_cycles(tmp_path: Path) -> None:
    """Several structure blocks persist independently, including equal site ids."""
    project = _sample_project()
    second = edi.Structure()
    second.name = 'demo_two'
    second.space_group.name_h_m = 'P 1'
    second.cell.length_a = edi.Parameter(6.25)
    second.cell.length_b = edi.Parameter(7.5)
    second.cell.length_c = edi.Parameter(8.75)
    site = edi.AtomSite()
    site.id = 'Na1'
    site.type_symbol = 'Cl'
    site.wyckoff_letter = 'a'
    site.fract_x = edi.Parameter(0.375, 0.002, True)
    site.fract_y = edi.Parameter(0.125)
    site.fract_z = edi.Parameter(0.625)
    second.atom_sites.add(site)
    project.structures.add(second)
    for index, experiment in enumerate(project.experiments):
        link = edi.LinkedStructure()
        link.structure_id = 'demo_two'
        link.scale = edi.Parameter(0.375 + index, 0.025 if index == 0 else 0.0, index == 0)
        link.enabled = index == 0
        experiment.linked_structures.add(link)
    first = tmp_path / 'first'
    second_save = tmp_path / 'second'
    project.save_as(first)
    restored = edi.Project.load(first)
    assert set(restored.structures.keys()) == {'demo', 'demo_two'}, (
        'Saving several structures must retain every separately keyed structure'
    )
    assert _triplet(restored.structures['demo'].atom_sites['Na1'].fract_x) == (
        0.25,
        0.001,
        True,
    ), 'A site id in the first structure must retain the first structure parameter'
    assert _triplet(restored.structures['demo_two'].atom_sites['Na1'].fract_x) == (
        0.375,
        0.002,
        True,
    ), 'The same site id in another structure must retain its independent parameter'
    assert restored.structures['demo_two'].cell.length_a.value == 6.25, (
        'Saving multiple structures must preserve the second cell independently'
    )
    for index, experiment in enumerate(restored.experiments):
        links = {link.structure_id: link for link in experiment.linked_structures}
        assert set(links) == {'demo', 'demo_two'}, (
            'Each bank must retain both linked structures through project loading'
        )
        assert _triplet(links['demo_two'].scale) == (
            0.375 + index, 0.025 if index == 0 else 0.0, index == 0
        ), (
            'Each bank phase scale must retain its own value, uncertainty and free flag'
        )
        assert links['demo_two'].enabled == (index == 0), (
            'A disabled link must remain present with its persisted participation flag'
        )
    restored.save_as(second_save)

    def files(directory):
        return {
            path.relative_to(directory): path.read_bytes()
            for path in directory.rglob('*')
            if path.is_file()
        }

    # Prescribe the same clock input through the shared byte-witness producer;
    # compare complete saved files, including metadata, without masking output.
    canonical_first = tmp_path / 'canonical_first'
    canonical_second = tmp_path / 'canonical_second'
    observe(first, canonical_first)
    observe(second_save, canonical_second)
    assert files(canonical_first) == files(canonical_second), (
        'The full multi-structure project must reach a byte-exact fixed point '
        'with a prescribed clock'
    )


def test_malformed_input_fails_closed_with_structured_diagnostics(tmp_path: Path) -> None:
    missing = tmp_path / 'does-not-exist'
    with pytest.raises(edi.IoError) as excinfo:
        edi.Project.load(missing)
    assert issubclass(edi.IoError, ValueError)
    diagnostics = excinfo.value.diagnostics
    assert diagnostics and diagnostics[0]['code'] and diagnostics[0]['message']
