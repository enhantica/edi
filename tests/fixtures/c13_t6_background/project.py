"""Visible  declaration fixtures; no correctness oracle is generated here."""

from __future__ import annotations

from pathlib import Path


def materialize(root, row, x, observed, *, free=(), coefficients=None, kind=None):
    root = Path(root)
    for name in ('structures', 'experiments', 'analysis'):
        (root / name).mkdir(parents=True, exist_ok=True)
    (root / 'project.edi').write_text('_edi.schema_version 3\n_metadata.name background-probe\n')
    (root / 'analysis/analysis.edi').write_text(
        '_edi.schema_version 3\n_fitting_mode.type single\n_minimizer.max_iterations 60\n'
    )
    (root / 'structures/structure.edi').write_text("""data_structure
_edi.schema_version 3
_cell.length_a 4.156885
_cell.length_b 4.156885
_cell.length_c 4.156885
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
La La a Biso 0 0 0 1 0.5
""")
    cw = row['project'].startswith('pd-neut-cwl')
    axis = 'two_theta' if cw else 'time_of_flight'
    mode = 'constant wavelength' if cw else 'time-of-flight'
    instrument = (
        """_peak.type cwl-tch-pseudo-voigt
_peak.broad_gauss_u 0
_peak.broad_gauss_v 0
_peak.broad_gauss_w 0.01
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
_instrument.calib_d_to_tof_linear 6000
_instrument.calib_d_to_tof_quadratic 0
_instrument.setup_twotheta_bank 90
"""
    )
    kind = kind or row['type']
    if kind == 'line-segment':
        background = f"""_background.type line-segment
loop_
_background.position
_background.intensity
{x[0]:.17g} 10
{x[-1]:.17g} 35
"""
    else:
        coefficients = row['coefficients'] if coefficients is None else coefficients
        background = f'_background.type {kind}\n'
        if kind == 'polynomial':
            background += f'_background.origin {row["origin"]:.17g}\n'
        else:
            background += (
                f'_background.x_min {row["x_min"]:.17g}\n_background.x_max {row["x_max"]:.17g}\n'
            )
        background += 'loop_\n_background.order\n_background.coef\n'
        background += ''.join(
            f'{i} {value:.17g}{"()" if i in free else ""}\n'
            for i, value in enumerate(coefficients)
        )
    data = ''.join(f'{a:.17g} {b:.17g} 1\n' for a, b in zip(x, observed, strict=True))
    (root / 'experiments/experiment.edi').write_text(f'''data_experiment
_edi.schema_version 3
_calculator.type crysta
_experiment_type.sample_form powder
_experiment_type.radiation_probe neutron
_experiment_type.scattering_type bragg
_experiment_type.beam_mode "{mode}"
{instrument}
_peak.cutoff_fwhm 1
loop_
_linked_structure.structure_id
_linked_structure.scale
structure 0

{background}
loop_
_data.{axis}
_data.intensity_meas
_data.intensity_meas_su
{data}''')
    return root
