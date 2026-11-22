"""Converted parameters keep the native metadata before a save can reconstruct it."""

from pathlib import Path

import edi
import pytest

ROOT = Path(__file__).resolve().parents[3]
CASES = [
    ('pd-neut-cwl_pbso4_basic', 'pbso4.pcr'),
    ('pd-neut-tof_si-sepd', 'fixed.pcr'),
    ('pd-xray-cwl_lif_single', 'lif_single_unpolarized.pcr'),
]


def metadata(parameter):
    return (
        parameter.name,
        parameter.units,
        parameter.description,
        parameter.min_value,
        parameter.max_value,
    )


@pytest.mark.parametrize(('case', 'filename'), CASES)
def test_fullprof_parameters_keep_metadata_before_and_after_native_save(tmp_path, case, filename):
    source = ROOT / 'knowledge/verification/fullprof' / case / filename
    imported = edi.Project.load(source)
    imported.save_as(tmp_path / 'native')
    reopened = edi.Project.load(tmp_path / 'native')
    for category, fields in {
        'instrument': (
            ('setup_wavelength', 'calib_twotheta_offset')
            if 'cwl' in case
            else ('calib_d_to_tof_linear', 'calib_d_to_tof_quadratic', 'calib_d_to_tof_offset')
        ),
        'peak': (
            (
                'broad_gauss_u',
                'broad_gauss_v',
                'broad_gauss_w',
                'broad_lorentz_x',
                'broad_lorentz_y',
            )
            if 'cwl' in case
            else ('broad_gauss_sigma_0', 'broad_gauss_sigma_1', 'broad_gauss_sigma_2')
        ),
    }.items():
        for field in fields:
            before = getattr(getattr(imported.experiments[0], category), field)
            after = getattr(getattr(reopened.experiments[0], category), field)
            assert before.name == field, (
                'Every converted FullProf parameter has its declared native name before saving'
            )
            assert metadata(before) == metadata(after), (
                'FullProf import retains native names, units, descriptions and ranges before save'
            )


def test_gsas_parameters_keep_metadata_before_and_after_native_save(tmp_path):
    source = ROOT / 'tests/fixtures/project_imports/metadata.gsas.json'
    imported = edi.Project.load(source)
    imported.save_as(tmp_path / 'native')
    reopened = edi.Project.load(tmp_path / 'native')
    for category, fields in {
        'instrument': ('setup_wavelength', 'calib_twotheta_offset'),
        'peak': (
            'broad_gauss_u',
            'broad_gauss_v',
            'broad_gauss_w',
            'broad_lorentz_x',
            'broad_lorentz_y',
            'asym_fcj_1',
            'asym_fcj_2',
        ),
    }.items():
        for field in fields:
            before = getattr(getattr(imported.experiments[0], category), field)
            after = getattr(getattr(reopened.experiments[0], category), field)
            assert before.name == field, (
                'Every converted GSAS-II parameter has its declared native name before saving'
            )
            assert metadata(before) == metadata(after), (
                'GSAS-II import retains native units, descriptions and ranges before saving'
            )
