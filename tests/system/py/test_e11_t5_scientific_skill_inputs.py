"""Actual example input/API reachability, independently committed measurements.

No numerical golden, fit acceptance/adoption or generated-CIF substitute is used.
The staged call has a real saved model iteration bound, never an alternate engine.
"""

from __future__ import annotations

import hashlib
import json
import runpy
from pathlib import Path
from types import SimpleNamespace

import edi
import pytest

ROOT = Path(__file__).resolve().parents[3]
MEASURED = ROOT / 'knowledge/verification/fullprof/pd-neut-cwl_lbco-hrpt_basic/lbco.dat'
SOURCE_SHA = '83c7f3d27d2e254367dd7dc3730261b9a5ebb811baaeed01fde050a7ba99be24'


def example():
    return runpy.run_path(str(ROOT / 'examples/fit_lbco_hrpt.py'), run_name='original_example')


def original_rows():
    return [
        tuple(map(float, line.split()))
        for line in MEASURED.read_text().splitlines()
        if line.strip()
    ]


def test_existing_lbco_example_reads_its_committed_genuine_measurement():
    module = example()
    actual = module['load_measurement'](module['MEASUREMENT'])
    assert hashlib.sha256(module['MEASUREMENT'].read_bytes()).hexdigest() == SOURCE_SHA, (
        'SCI INPUT: actual example resolves the original provenance-bound LBCO measurement'
    )
    assert list(zip(*actual, strict=True)) == original_rows(), (
        'SCI INPUT: example retains every genuine measured coordinate, intensity and uncertainty'
    )


def test_existing_lbco_stage_calls_real_project_managed_fit_and_preserves_population(tmp_path):
    module = example()
    rows = original_rows()
    grid, observed, sigma = map(list, zip(*rows, strict=True))
    project = module['build_project']()
    project.experiment.data = edi.PdCwlData(
        two_theta=grid, intensity_meas=observed, intensity_meas_su=sigma
    )
    module['release'](project, full=False)
    exclusions = list(project.experiment.excluded_regions)
    staged = tmp_path / 'actual-bounded-stage'
    project.save_as(staged)
    analysis = staged / 'analysis/analysis.edi'
    analysis.write_text(analysis.read_text() + '\n_minimizer.max_iterations 2\n')
    actual = edi.Project.load(staged)
    result = module['fit_stage']('Actual bounded public stage', actual, (grid, observed, sigma))
    assert result.iterations <= 2, 'SCI API: actual stage honors the saved model iteration budget'
    data = actual.experiment.data
    assert (
        list(zip(data.two_theta, data.intensity_meas, data.intensity_meas_su, strict=True)) == rows
    ), 'SCI API: ordinary example fit uses actual project data without replacing measured weights'
    assert list(actual.experiment.excluded_regions) == exclusions, (
        'SCI API: a staged example call preserves the declared excluded population'
    )


@pytest.mark.parametrize('boundary', ['A', 'B'])
def test_real_cancelled_result_stops_existing_example_before_further_work(
    monkeypatch, capsys, boundary
):
    module = example()
    namespace = module['main'].__globals__
    monkeypatch.setitem(namespace, 'MEASUREMENT', MEASURED)
    calls = []
    actual_cancelled = []

    def stage(label, project, data):
        calls.append(label)
        grid, observed, sigma = data
        project.experiment.data = edi.PdCwlData(
            two_theta=grid, intensity_meas=observed, intensity_meas_su=sigma
        )
        if boundary == 'B' and len(calls) == 1:
            # Only the prerequisite caller return is simulated, explicitly. This
            # does not assert an actual first-stage solve/convergence.
            return SimpleNamespace(
                status=edi.FitStatus.DONE,
                converged=True,
                iterations=0,
                rwp=0.0,
                reduced_chi_square=0.0,
            )
        outcome = project.fit(should_cancel=lambda: True)
        actual_cancelled.append(outcome)
        return outcome

    monkeypatch.setitem(namespace, 'fit_stage', stage)
    code = module['main']()
    assert actual_cancelled and all(
        outcome.status == edi.FitStatus.CANCELLED for outcome in actual_cancelled
    ), 'EX1 SETUP: cancellation is the genuine public engine result, not a fabricated terminal'
    assert len(calls) == (1 if boundary == 'A' else 2), (
        'EX1: real cancellation cannot start a later staged refinement'
    )
    assert code != 0, 'EX1: genuine cancellation cannot become successful workflow completion'
    assert 'engine parity reached' not in capsys.readouterr().out, (
        'EX1: parity cannot reclassify actual cancelled work as a successful workflow'
    )


@pytest.mark.parametrize('boundary', ['A', 'B'])
@pytest.mark.parametrize('status', ['CANCELLED', 'ERROR', 'UNAVAILABLE', 'SUPERSEDED'])
def test_status_only_caller_policy_never_turns_non_success_into_parity_success(
    monkeypatch, boundary, status
):
    # Explicit caller-policy simulation, NOT a fabricated live engine result or
    # scientific outcome. The native return type has no writable constructor.
    module = example()
    namespace = module['main'].__globals__
    reference = json.loads(module['BASELINE'].read_text())[module['BASELINE_KEY']]
    monkeypatch.setitem(namespace, 'MEASUREMENT', MEASURED)
    calls = []

    def stage(label, project, _data):
        calls.append(label)
        project.structure.cell.length_a.value = reference['parameters']['lbco.cell.length_a']
        project.experiment.linked_structure.scale.value = reference['parameters'][
            'hrpt.linked_structure.lbco.scale'
        ]
        failed = len(calls) == (1 if boundary == 'A' else 2)
        return SimpleNamespace(
            status=getattr(edi.FitStatus, status) if failed else edi.FitStatus.DONE,
            converged=not failed,
            rwp=reference['wr_factor_all'],
            reduced_chi_square=reference['reduced_chi_square'],
            iterations=0,
        )

    monkeypatch.setitem(namespace, 'fit_stage', stage)
    code = module['main']()
    assert len(calls) == (1 if boundary == 'A' else 2), (
        'EX1 CALLER ONLY: declared failed/unavailable/superseded stage cannot start later work'
    )
    assert code != 0, (
        'EX1 CALLER ONLY: matching independent comparison values cannot override non-success'
    )


PUBLISHED_PBSO4 = {
    'Pb': ('Pb', (0.18820, 0.25, 0.16700), 4),
    'S': ('S', (0.06300, 0.25, 0.68600), 4),
    'O1': ('O', (-0.09500, 0.25, 0.60000), 4),
    'O2': ('O', (0.18100, 0.25, 0.54300), 4),
    'O3': ('O', (0.08500, 0.02600, 0.80600), 8),
}


def persistence_project(structure):
    # Explicit calculation-only grid completes the ordinary saved project. It
    # supplies NO invented measured y/sigma and no calculation is performed.
    project = edi.Project(name='structure-persistence-control')
    project.structure = structure
    project.experiment = edi.ExperimentFactory.from_cif_str(
        """data_persistence_grid
_edi.schema_version 2
_experiment_type.sample_form powder
_experiment_type.beam_mode "constant wavelength"
_experiment_type.radiation_probe neutron
_experiment_type.scattering_type bragg
_peak.type cwl-tch-pseudo-voigt
_peak.broad_gauss_u 0.1
_peak.broad_gauss_v 0
_peak.broad_gauss_w 0.1
_peak.broad_lorentz_x 0
_peak.broad_lorentz_y 0.1
_peak.cutoff_fwhm 8
_instrument.setup_wavelength 1.909
_instrument.calib_twotheta_offset 0
_data_range.two_theta_min 10
_data_range.two_theta_max 10.2
_data_range.two_theta_step 0.1
"""
    )
    project.experiment.linked_structure.structure_id = structure.name
    return project


def verify_published_pbso4(reopened, expected_sites):
    assert reopened.space_group.name_h_m == 'P n m a', (
        'CIF: missing optional Wyckoff column cannot change the actual declared space group'
    )
    assert [
        float(getattr(reopened.cell, field).value)
        for field in (
            'length_a',
            'length_b',
            'length_c',
            'angle_alpha',
            'angle_beta',
            'angle_gamma',
        )
    ] == pytest.approx([8.48, 5.398, 6.958, 90.0, 90.0, 90.0], abs=1e-12), (
        'CIF: published cell values survive actual save/reopen'
    )
    group = json.loads((ROOT / 'tests/fixtures/c34_t25_fullprof/wyckoff.json').read_text())[
        'groups'
    ]['Pnma']
    sites = {site.id: site for site in reopened.atom_sites}
    assert set(sites) == set(expected_sites), 'CIF: all genuine published atom identities survive'
    for label, (element, coordinates, multiplicity) in expected_sites.items():
        site = sites[label]
        actual = [
            float(getattr(site, field).value) % 1 for field in ('fract_x', 'fract_y', 'fract_z')
        ]
        assert actual == pytest.approx([x % 1 for x in coordinates], abs=1e-12), (
            'CIF: optional-letter resolution cannot move the published physical fractional site'
        )
        assert site.type_symbol == element and float(site.occupancy.value) == 1.0, (
            'CIF: resolving an optional label cannot change element or published site occupancy'
        )
        assert site.adp_type == 'Uiso' and float(site.adp_iso.value) == pytest.approx(0.01), (
            'CIF: original explicit isotropic U convention and physical value survive persistence'
        )
        expected = next(
            row
            for row in group['wyckoff']
            if row['special_op'] == ('x,1/4,z' if multiplicity == 4 else 'x,y,z')
        )
        assert (
            site.wyckoff_letter == expected['letter'] and expected['multiplicity'] == multiplicity
        ), 'CIF: actual optional-letter resolution matches independent cctbx position/multiplicity'
        orbit = set()
        for operation in group['operations']:
            r, t = operation['r'], operation['t']
            orbit.add(
                tuple(
                    round((sum(r[3 * i + j] * coordinates[j] for j in range(3)) + t[i]) % 1, 10)
                    for i in range(3)
                )
            )
        assert len(orbit) == multiplicity, (
            'CIF REFERENCE: original coordinates and independent cctbx '
            'operations reproduce input count'
        )


@pytest.mark.parametrize('factory', ['from_cif_path', 'from_cif_str'])
def test_genuine_classic_cif_without_optional_letters_saves_and_reopens_unchanged(
    tmp_path, factory
):
    source = ROOT / 'tests/fixtures/assistant/reference/PbSO4-Wyckoff.cif'
    original = source.read_bytes()
    assert hashlib.sha256(original).hexdigest() == (
        '9bc19d0995561afd78a5f0563599c032751621da994e36c7570b4f515d9f0e2f'
    ), 'CIF INPUT: published tutorial bytes remain the independent original'
    value = source if factory == 'from_cif_path' else original.decode()
    structure = getattr(edi.StructureFactory, factory)(value)
    project = persistence_project(structure)
    target = tmp_path / 'saved-original-cif'
    project.save_as(target)
    reopened = edi.Project.load(target).structure
    verify_published_pbso4(reopened, PUBLISHED_PBSO4)
    assert source.read_bytes() == original, (
        'CIF: actual factory/persistence cannot mutate source bytes'
    )


def test_genuine_published_explicit_wyckoff_letters_remain_authoritative(tmp_path):
    source = ROOT / 'tests/fixtures/e02_t2_ncaf_5bank/published_cod_1000236.cif'
    original = source.read_bytes()
    structure = edi.StructureFactory.from_cif_path(source)
    expected = {site.id: site.wyckoff_letter for site in structure.atom_sites}
    assert all(expected.values()), 'CIF SETUP: genuine COD input supplies its explicit letters'
    project = persistence_project(structure)
    target = tmp_path / 'saved-cod-control'
    project.save_as(target)
    actual = edi.Project.load(target)
    assert {site.id: site.wyckoff_letter for site in actual.structure.atom_sites} == expected, (
        'CIF: filling absent optional letters cannot rewrite existing explicit published letters'
    )
    assert source.read_bytes() == original, (
        'CIF: explicit-letter control preserves its genuine input'
    )


@pytest.mark.parametrize(
    ('unknown', 'image'), [('?', False), ('.', False), (None, True), ('?', True), ('.', True)]
)
def test_derived_unknown_optional_letter_and_equivalent_orbit_image_preserve_physics(
    tmp_path, unknown, image
):
    source = ROOT / 'tests/fixtures/assistant/reference/PbSO4-Wyckoff.cif'
    original = source.read_bytes()
    text = original.decode()
    assert '1/2-x,1/2+y,1/2+z' in text, (
        'CIF DERIVED INPUT: the actual original supplies this literal symmetry operation'
    )
    expected_sites = {}
    for label, (element, xyz, multiplicity) in PUBLISHED_PBSO4.items():
        position = ((0.5 - xyz[0]) % 1, (0.5 + xyz[1]) % 1, (0.5 + xyz[2]) % 1) if image else xyz
        expected_sites[label] = (element, position, multiplicity)
    if unknown is not None:
        text = text.replace(
            '_atom_site_symmetry_multiplicity',
            '_atom_site_symmetry_multiplicity\n   _atom_site_Wyckoff_symbol',
        )
    lines = []
    for line in text.splitlines():
        prepared = line
        fields = line.split()
        if len(fields) >= 9 and fields[0] in expected_sites:
            if image:
                fields[2:5] = [format(x, '.17g') for x in expected_sites[fields[0]][1]]
            if unknown is not None:
                fields.append(unknown)
            prepared = ' '.join(fields)
        lines.append(prepared)
    selected = tmp_path / 'explicitly-derived-original.cif'
    selected.write_text('\n'.join(lines) + '\n')
    structure = edi.StructureFactory.from_cif_path(selected)
    project = persistence_project(structure)
    target = tmp_path / 'saved-derived-input'
    project.save_as(target)
    verify_published_pbso4(edi.Project.load(target).structure, expected_sites)
    assert source.read_bytes() == original, (
        'CIF DERIVED INPUT: unknown tokens/orbit-image controls never alter the genuine original'
    )
