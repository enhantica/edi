"""Authored pdCIFs exercise content refusal independently of file names."""

import re

from tests.fixtures import structure_cif_refusal as native

STYLES = ['dot', 'underscore', 'upper', 'multiblock', 'next-line', 'wrapped-row', 'row-comment']
LAYOUTS = ['native-suffix', 'cif-suffix', 'shadow', 'upper-suffix']
CIF = """data_cif_experiment
_edi_edi.schema_version 3
_edi_experiment_type.sample_form powder
_edi_experiment_type.beam_mode 'constant wavelength'
_diffrn_radiation.probe neutron
_edi_experiment_type.scattering_type bragg
_edi_peak.type cwl-gaussian
_edi_peak.broad_gauss_u 0
_edi_peak.broad_gauss_v 0
_edi_peak.broad_gauss_w 0.1500(2)
_edi_peak.cutoff_fwhm 5
_diffrn_radiation_wavelength.value 1.5406
_pd_calib.2theta_offset 0.123
_audit.note supplied_cif_declaration
_pd_phase_block.id phase
_pd_phase_block.scale 2.3
loop_
_pd_meas.2theta_scan
_pd_meas.intensity_total
_pd_meas.intensity_total_su
10 21 2
11 24 3
12 26 4
"""


MAIN_CIF = """data_main_cwl
_easydiffraction_experiment_type.sample_form powder
_easydiffraction_experiment_type.beam_mode 'constant wavelength'
_easydiffraction_experiment_type.radiation_probe neutron
_easydiffraction_experiment_type.scattering_type bragg
_diffrn_radiation_wavelength.value 1.494
_pd_calib.2theta_offset 0.6225
_easydiffraction_peak.broad_gauss_u 0.0834
_easydiffraction_peak.broad_gauss_v -0.1168
_easydiffraction_peak.broad_gauss_w 0.123
loop_
_pd_phase_block.id
_pd_phase_block.scale
phase 2.3
loop_
_pd_meas.2theta_scan
_pd_meas.intensity_total
_pd_meas.intensity_total_su
10.5 100 10
11.25 121 11
"""
FACTORY_STYLES = [*STYLES, 'main-classic']


def text(style):
    if style == 'main-classic':
        return MAIN_CIF
    if style == 'underscore':
        return re.sub(r'^(_\S+)', lambda m: m[1].replace('.', '_', 1), CIF, flags=re.MULTILINE)
    if style == 'upper':
        return re.sub(r'^(_\S+)', lambda m: m[1].upper(), CIF, flags=re.MULTILINE)
    if style == 'multiblock':
        return 'data_publication\n_audit.note before\n' + CIF + '\ndata_later\n_audit.note after\n'
    replacements = {
        'next-line': ('_edi_edi.schema_version 3', '_edi_edi.schema_version\n3'),
        'wrapped-row': ('10 21 2', '10 21\n2'),
        'row-comment': ('10 21 2', '10 21 2 # an authored measured row'),
    }
    old, new = replacements.get(style, ('', ''))
    return CIF.replace(old, new) if old else CIF


def poisoned_project(directory, style, layout):
    project = native.project(directory)
    name = {
        'native-suffix': 'cif_only.edi',
        'cif-suffix': 'cif_only.cif',
        'shadow': 'bank.cif',
        'upper-suffix': 'cif_only.CIF',
    }[layout]
    (project / 'experiments' / name).write_text(text(style))
    return project


def native_experiment(directory):
    source = native.ROOT / 'tests/fixtures/loop_parameter_ids/line-segment/experiments/bank.edi'
    target = directory / 'extra.edi'
    target.write_text(source.read_text().replace('data_bank', 'data_extra', 1))
    return target
