"""Imported values are read independently from cryspy's own unmodified rcif project."""

import hashlib
import json
import re
from pathlib import Path

import edi
import gemmi
import pytest

from tests.fixtures.project_save.reference import declared_rule, expected_pair

HOME = Path(__file__).resolve().parents[2] / 'fixtures/project_imports'
SOURCE = HOME / 'cryspy-pbso4.rcif'


def reference():
    raw = SOURCE.read_bytes()
    manifest = json.loads(SOURCE.with_suffix('.json').read_text(encoding='utf-8'))
    assert hashlib.sha256(raw).hexdigest() == manifest['sha256'], (
        'The cryspy import oracle retains the unmodified upstream functional project bytes'
    )
    text = raw.decode('utf-8')
    # The source's calculated _pd_proc loop is ragged; its complete input blocks precede it.
    inputs = text[text.index('data_pbso4') :].split('loop_\n_pd_proc_2theta', 1)[0]
    return gemmi.cif.read_string(inputs)


def number(block, tag):
    return gemmi.cif.as_number(block.find_value(tag))


def test_cryspy_import_preserves_the_source_cell_sites_and_uncertainties():
    source = reference()['pbso4']
    project = edi.Project.load(SOURCE)
    assert len(project.structures) == 1, 'The cryspy PbSO4 project imports its one source crystal'
    structure = project.structures[0]
    for field in ('length_a', 'length_b', 'length_c', 'angle_alpha', 'angle_beta', 'angle_gamma'):
        imported = getattr(structure.cell, field)
        tag = '_cell_' + field
        assert imported.value == pytest.approx(number(source, tag), abs=1e-10), (
            'Imported cell values come from the cryspy source rcif: ' + tag
        )
        match = re.fullmatch(r'([-+]?\d+)\.(\d+)\((\d+)\)', source.find_value(tag))
        if match:
            expected_su = int(match[3]) * 10 ** -len(match[2])
            assert imported.uncertainty == pytest.approx(expected_su, abs=1e-12), (
                'Cryspy parenthesized cell uncertainties survive import with their decimal scale'
            )
            assert imported.free, (
                'A cryspy cell value with a fitted uncertainty stays free on import'
            )
    identifiers = list(source.find_values('_atom_site_label'))
    assert len(structure.atom_sites) == len(identifiers), (
        'Every source cryspy atom site is retained exactly once'
    )
    for index, identifier in enumerate(identifiers):
        site = structure.atom_sites[identifier]
        for field in ('fract_x', 'fract_y', 'fract_z', 'occupancy'):
            expected = gemmi.cif.as_number(source.find_values('_atom_site_' + field)[index])
            assert getattr(site, field).value == pytest.approx(expected, abs=1e-10), (
                'Coordinates and occupancy retain the source convention without rescaling'
            )
        assert site.adp_type == 'Biso', (
            'Cryspy source Biso remains Biso rather than an unconverted Uiso'
        )
        assert site.adp_iso.value == pytest.approx(
            gemmi.cif.as_number(source.find_values('_atom_site_B_iso_or_equiv')[index]), abs=1e-10
        ), 'Nonzero cryspy displacement values preserve the declared Biso convention'


def test_cryspy_import_preserves_instrument_profile_and_observation_values():
    source = reference()['pd']
    project = edi.Project.load(SOURCE)
    assert len(project.experiments) == 1, (
        'The cryspy project imports its one source powder experiment'
    )
    experiment = project.experiments[0]
    for field, tag in {
        'setup_wavelength': '_setup_wavelength',
        'calib_twotheta_offset': '_setup_offset_2theta',
    }.items():
        assert getattr(experiment.instrument, field).value == pytest.approx(number(source, tag)), (
            'The nonidentity cryspy wavelength and signed angular offset retain their source units'
        )
    for field, suffix in {
        'broad_gauss_u': 'U',
        'broad_gauss_v': 'V',
        'broad_gauss_w': 'W',
        'broad_lorentz_x': 'X',
        'broad_lorentz_y': 'Y',
    }.items():
        assert getattr(experiment.peak, field).value == pytest.approx(
            number(source, '_pd_instr_resolution_' + suffix)
        ), 'Cryspy profile coefficients retain their declared angular convention on import'
    for field, tag in {
        'two_theta': '_pd_meas_2theta',
        'intensity_meas': '_pd_meas_intensity',
        'intensity_meas_su': '_pd_meas_intensity_sigma',
    }.items():
        expected = [gemmi.cif.as_number(value) for value in source.find_values(tag)]
        assert list(getattr(experiment.data, field)) == pytest.approx(expected), (
            'Cryspy grid, intensities and supplied uncertainties retain their source order'
        )


def test_cryspy_import_round_trip_retains_source_values_and_leaves_the_source_unchanged(tmp_path):
    original = SOURCE.read_bytes()
    project = edi.Project.load(SOURCE)
    project.save_as(tmp_path / 'native')
    reopened = edi.Project.load(tmp_path / 'native')
    source = reference()
    token = source['pbso4'].find_value('_cell_length_a')
    match = re.fullmatch(r'([-+]?\d+)\.(\d+)\((\d+)\)', token)
    assert match is not None, 'The independent cryspy cell source carries its decimal uncertainty'
    source_su = int(match[3]) * 10 ** -len(match[2])
    written_value, written_su = expected_pair(
        number(source['pbso4'], '_cell_length_a'), source_su, declared_rule(tmp_path / 'native')
    )
    assert reopened.structures[0].cell.length_a.value == pytest.approx(written_value, abs=5e-7), (
        'A native save retains the source cell under the independently rounded project s.u. rule'
    )
    assert reopened.structures[0].cell.length_a.uncertainty == pytest.approx(
        written_su, abs=1e-12
    ), 'A native save retains the independently rounded source cell uncertainty'
    expected = [
        gemmi.cif.as_number(value) for value in source['pd'].find_values('_pd_meas_intensity')
    ]
    assert list(reopened.experiments[0].data.intensity_meas) == pytest.approx(expected), (
        'Cryspy observations survive conversion to an ordinary saved native project'
    )
    assert SOURCE.read_bytes() == original, (
        'Importing and saving never rewrite the original cryspy project'
    )


@pytest.mark.parametrize(
    ('declaration', 'item'),
    [
        ('_unsupported_model_value 0.37', '_unsupported_model_value'),
        (
            'loop_\n_unsupported_model_label\n_unsupported_model_value\none 0.37',
            '_unsupported_model_label',
        ),
    ],
)
def test_cryspy_refuses_unconverted_scalar_and_loop_items(tmp_path, declaration, item):
    source = tmp_path / 'unsupported.rcif'
    text = SOURCE.read_text(encoding='utf-8').replace(
        'data_pbso4', 'data_pbso4\n' + declaration, 1
    )
    source.write_text(text, encoding='utf-8')
    with pytest.raises(edi.IoError, match=re.escape(item)):
        edi.Project.load(source)


@pytest.mark.parametrize('marked', ['8.479343(100)A+', '8.479343()A-'])
def test_cryspy_refuses_constraint_marks_instead_of_discarding_the_relation(tmp_path, marked):
    source = tmp_path / 'constrained.rcif'
    text = SOURCE.read_text(encoding='utf-8').replace('8.479343(100)', marked, 1)
    source.write_text(text, encoding='utf-8')
    with pytest.raises(edi.IoError, match='constraint mark'):
        edi.Project.load(source)
