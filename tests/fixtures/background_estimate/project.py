"""Materialize the frozen estimator inputs as ordinary projects."""

import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent


def materialize(destination, row, *, kind='line-segment', reference_profile=False):
    destination = Path(destination)
    for directory in ('structures', 'experiments', 'analysis'):
        (destination / directory).mkdir(parents=True, exist_ok=True)
    values = np.loadtxt(HERE / row['input_file'])
    (destination / 'project.edi').write_text(
        '_edi.schema_version 3\n_metadata.name background-estimate\n'
    )
    (destination / 'analysis/analysis.edi').write_text(
        '_edi.schema_version 3\n_fitting_mode.type single\n'
    )
    (destination / 'structures/phase.edi').write_text("""data_phase
_edi.schema_version 3
_cell.length_a 4.1
_cell.length_b 4.1
_cell.length_c 4.1
_cell.angle_alpha 90
_cell.angle_beta 90
_cell.angle_gamma 90
_space_group.name_h_m "P m -3 m"
loop_
_atom_site.id
_atom_site.type_symbol
_atom_site.wyckoff_letter
_atom_site.adp_type
_atom_site.fract_x
_atom_site.fract_y
_atom_site.fract_z
_atom_site.occupancy
_atom_site.adp_iso
Si Si a Biso 0 0 0 1 0.5
""")
    cw = row['beam_mode'] == 'constant wavelength'
    instrument = (
        """_peak.type cwl-tch-pseudo-voigt
_peak.broad_gauss_u 0
_peak.broad_gauss_v 0
_peak.broad_gauss_w 0.1
_peak.broad_lorentz_x 0
_peak.broad_lorentz_y 0
_instrument.setup_wavelength 1.54
_instrument.calib_twotheta_offset 0
"""
        if cw
        else """_peak.type tof-pseudo-voigt
_peak.broad_gauss_sigma_0 100
_peak.broad_gauss_sigma_1 0
_peak.broad_gauss_sigma_2 0
_peak.broad_lorentz_gamma_0 0
_peak.broad_lorentz_gamma_1 0
_peak.broad_lorentz_gamma_2 0
_instrument.calib_d_to_tof_offset 0
_instrument.calib_d_to_tof_linear 17000
_instrument.calib_d_to_tof_quadratic 0
_instrument.setup_twotheta_bank 90
"""
    )
    low, high = row['active_endpoints']
    if kind == 'line-segment':
        background = f"""loop_
_background.id
_background.position
_background.intensity
old_a {low:.17g} 0
old_b {high:.17g} 0
"""
    else:
        background = (
            '_background.origin 80\n'
            if kind == 'polynomial'
            else f'_background.x_min {low:.17g}\n_background.x_max {high:.17g}\n'
        )
        background += """loop_
_background.id
_background.order
_background.coef
constant 0 17
linear 1 3.25
quadratic 2 -1.5
"""
    exclusion = 'loop_\n_excluded_region.start\n_excluded_region.end\n'
    exclusion += ''.join(f'{a:.17g} {b:.17g}\n' for a, b in row['excluded'])
    data = ''.join(f'{a:.17g} {b:.17g} {max(c, 1e-12):.17g}\n' for a, b, c in values)
    (destination / 'experiments/bank.edi').write_text(f'''data_bank
_edi.schema_version 3
_calculator.type crysta
_experiment_type.sample_form powder
_experiment_type.radiation_probe neutron
_experiment_type.scattering_type bragg
_experiment_type.beam_mode "{row['beam_mode']}"
{instrument}
_peak.cutoff_fwhm 5
loop_
_linked_structure.structure_id
_linked_structure.scale
phase 0

_background.type {kind}
{background}
{exclusion}
loop_
_data.{'two_theta' if cw else 'time_of_flight'}
_data.intensity_meas
_data.intensity_meas_su
{data}''')
    if reference_profile:
        path = destination / 'experiments/bank.edi'
        path.write_text(
            path.read_text() + '\n_background_estimate.tolerance 2\n'
            '_background_estimate.in_peaks drop\n'
            '_background_estimate.use_model false\n'
        )
    return destination


if __name__ == '__main__':
    for name, case in json.loads((HERE / 'reference.json').read_text())['cases'].items():
        materialize(HERE / 'projects' / name, case, reference_profile=True)
