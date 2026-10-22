"""Generate small diffraction inputs using closed forms, without either library."""

import json
import math
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STRUCTURE = """data_phase
_edi.schema_version 3
_cell.length_a 4
_cell.length_b 4
_cell.length_c 4
_cell.angle_alpha 90
_cell.angle_beta 90
_cell.angle_gamma 90
_space_group.name_h_m "P m -3 m"
loop_
_atom_site.id
_atom_site.wyckoff_letter
_atom_site.type_symbol
_atom_site.adp_type
_atom_site.fract_x
_atom_site.fract_y
_atom_site.fract_z
_atom_site.occupancy
_atom_site.adp_iso
Si1 a Si Biso 0 0 0 1 0.4
"""


def generate():
    for kind in ('cw', 'tof'):
        root = ROOT / kind
        for part in ('structures', 'experiments', 'analysis'):
            (root / part).mkdir(parents=True, exist_ok=True)
        (root / 'project.edi').write_text(
            '_edi.schema_version 3\n_metadata.name "Excluded regions"\n'
        )
        (root / 'structures/phase.edi').write_text(STRUCTURE)
        (root / 'analysis/analysis.edi').write_text(
            '_edi.schema_version 3\n_fitting_mode.type single\n'
        )
        if kind == 'cw':
            axis = 'two_theta'
            grid = [10 + i / 2 for i in range(161)]
            regions = [[10, 15], [38.5, 41.5], [85, 90]]
            instrument = (
                '_instrument.setup_wavelength 1.54\n_instrument.calib_twotheta_offset 0.29\n'
            )
            peak = (
                '_peak.type cwl-tch-pseudo-voigt\n'
                '_peak.broad_gauss_u 0\n'
                '_peak.broad_gauss_v 0\n'
                '_peak.broad_gauss_w 0.01\n'
                '_peak.broad_lorentz_x 0\n'
                '_peak.broad_lorentz_y 0\n'
            )
            mode = '"constant wavelength"'
            d = [1.54 / (2 * math.sin(math.radians(x / 2))) for x in grid]
        else:
            axis = 'time_of_flight'
            grid = [5000 + 100 * i for i in range(161)]
            regions = [[5000, 6000], [10000, 11000], [20000, 21000]]
            instrument = (
                '_instrument.setup_twotheta_bank 90\n'
                '_instrument.calib_d_to_tof_offset 37\n'
                '_instrument.calib_d_to_tof_linear 5000\n'
                '_instrument.calib_d_to_tof_quadratic 2.5\n'
                '_instrument.calib_d_to_tof_reciprocal 0\n'
            )
            peak = (
                '_peak.type tof-jorgensen-von-dreele\n'
                '_peak.rise_alpha_0 0.014\n'
                '_peak.rise_alpha_1 0.055\n'
                '_peak.decay_beta_0 0.0047\n'
                '_peak.decay_beta_1 0.137\n'
                '_peak.broad_gauss_sigma_0 0\n'
                '_peak.broad_gauss_sigma_1 0\n'
                '_peak.broad_gauss_sigma_2 15.4\n'
                '_peak.broad_lorentz_gamma_0 0\n'
                '_peak.broad_lorentz_gamma_1 8.29\n'
                '_peak.broad_lorentz_gamma_2 0\n'
            )
            mode = 'time-of-flight'
            d = [2 * (x - 37) / (5000 + math.sqrt(5000**2 + 10 * (x - 37))) for x in grid]
        if kind == 'tof':
            peak += (
                '_peak.broad_gauss_size 0\n'
                '_peak.broad_gauss_strain 0\n'
                '_peak.broad_lorentz_size 0\n'
                '_peak.broad_lorentz_strain 0\n'
            )
        text = (
            f'data_pattern\n'
            f'_edi.schema_version 3\n'
            f'_experiment_type.sample_form powder\n'
            f'_experiment_type.radiation_probe neutron\n'
            f'_experiment_type.scattering_type bragg\n'
            f'_experiment_type.beam_mode {mode}\n'
            f'_calculator.type crysta\n'
            f''
        )
        text += peak + '_peak.cutoff_fwhm 8\n' + instrument
        text += '\nloop_\n_linked_structure.structure_id\n_linked_structure.scale\nphase 1\n'
        text += (
            '_background.type line-segment\n'
            'loop_\n'
            '_background.id\n'
            '_background.position\n'
            '_background.intensity\n'
        )
        text += f'1 {grid[0]} 40\n2 {grid[-1]} 80\n'
        text += '\nloop_\n_excluded_region.id\n_excluded_region.start\n_excluded_region.end\n'
        text += ''.join(f'{i} {lo} {hi}\n' for i, (lo, hi) in enumerate(regions, 1))
        text += f'\nloop_\n_data.{axis}\n_data.intensity_meas\n_data.intensity_meas_su\n'
        text += ''.join(
            f'{x:.12g} {100 + 0.4 * i + 10 * math.sin(i / 7):.12g} {2 + i % 3:.12g}\n'
            for i, x in enumerate(grid)
        )
        (root / 'experiments/pattern.edi').write_text(text)
        included = [not any(lo <= x <= hi for lo, hi in regions) for x in grid]
        oracle = {
            'axis': axis,
            'x': grid,
            'd': d,
            'regions': regions,
            'included': included,
            'full': [grid[0], grid[-1]],
            'included_range': [
                min(x for x, keep in zip(grid, included, strict=True) if keep),
                max(x for x, keep in zip(grid, included, strict=True) if keep),
            ],
        }
        (ROOT / f'{kind}.json').write_text(json.dumps(oracle, indent=2) + '\n')

    scan = ROOT / 'cw-scan'
    shutil.copytree(ROOT / 'cw', scan, dirs_exist_ok=True)
    (scan / 'analysis/analysis.edi').write_text(
        '_edi.schema_version 3\n'
        '_fitting_mode.type sequential\n'
        '_sequential_fit.data_dir experiments/scan\n'
        '_sequential_fit.file_pattern *.xy\n'
    )
    folder = scan / 'experiments/scan'
    folder.mkdir(exist_ok=True)
    points = (scan / 'experiments/pattern.edi').read_text().split('_data.intensity_meas_su\n')[1]
    for i in range(2):
        (folder / f'{i}.xy').write_text('XYDATA\n' + points)


if __name__ == '__main__':
    generate()
