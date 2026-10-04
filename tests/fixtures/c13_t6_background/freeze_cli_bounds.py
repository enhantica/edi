"""Extract CLI bounds from independent FullProf SUM output, authoring only."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
NUMBER = r'[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?'


def pair(lines, marker, offset=0):
    index = next(i for i, line in enumerate(lines) if marker in line)
    text = lines[index].split(':', 1)[-1] if offset == 0 else lines[index + offset]
    values = [float(token) for token in re.findall(NUMBER, text)]
    return values[-2:]


def atom_parameters(lines):
    result = {}
    # The source atom table prints each value with its last-digit uncertainty.
    i = next(i for i, line in enumerate(lines) if 'Name      x' in line)
    for line in lines[i + 1 :]:
        if not line.strip():
            break
        site = line.split()[0]
        atoms = re.findall(r'(' + NUMBER + r')\(\s*(\d+)\)', line)
        for name, (value, su) in zip(
            ('fract_x', 'fract_y', 'fract_z', 'adp_iso', 'occupancy'), atoms, strict=True
        ):
            digits = len(value.split('.')[1]) if '.' in value else 0
            uncertainty = int(su) * 10**-digits
            if uncertainty and name != 'occupancy':
                result[site + '.' + name] = [float(value), uncertainty]
    return result


def main():
    output = {'schema': 1, 'sigma_multiple': 4, 'cases': {}}
    for case in ('cecoal', 'pearl', 'lab6'):
        # Owner decision 2026-10-02, development hub c98ab7f36: match the least-squares objective.
        # The original cecoal M.L. SUM remains vendored as provenance, not a fit oracle.
        source = 'cecoal-ls.sum' if case == 'cecoal' else case + '.sum'
        source_file = ROOT / source
        lines = source_file.read_text().splitlines()
        parameters = {
            'scale': pair(lines, 'scale factor'),
            'calib_twotheta_offset' if case == 'lab6' else 'calib_d_to_tof_offset': pair(
                lines, 'Zero-point'
            ),
        }
        if case != 'lab6':
            for name, offset in (
                ('broad_gauss_sigma_2', 1),
                ('broad_gauss_sigma_1', 2),
                ('broad_gauss_sigma_0', 3),
            ):
                values = pair(lines, 'Gaussian variances Sig-2', offset)
                if values[1]:
                    parameters[name] = values
            for name, offset in (
                ('broad_lorentz_gamma_2', 1),
                ('broad_lorentz_gamma_1', 2),
                ('broad_lorentz_gamma_0', 3),
            ):
                values = pair(lines, 'Lorentzian FWHM Gam-2', offset)
                if values[1]:
                    parameters[name] = values
            parameters['calib_d_to_tof_quadratic'] = pair(lines, 'T.O.F.- dtt2')
            if case == 'pearl':
                parameters['calib_d_to_tof_linear'] = pair(lines, 'T.O.F.- dtt1')
                # This SUM packs (value,sigma) pairs across physical lines, retaining alpha0 fixed.
                i = next(
                    i for i, line in enumerate(lines) if 'Peak shape parameter alpha0' in line
                )
                values = [float(t) for line in lines[i + 1 : i + 5] for t in line.split()]
                parameters.update({
                    'decay_beta_0': values[2:4],
                    'rise_alpha_1': values[4:6],
                    'decay_beta_1': values[6:8],
                })
        else:
            parameters['setup_wavelength'] = pair(lines, 'wavelength (Lambda1)')
            parameters['calib_sample_displacement'] = pair(lines, 'Cos(2theta)-shift')
            parameters['calib_sample_transparency'] = pair(lines, 'Sin(2theta)-shift')
            parameters['broad_gauss_u'] = pair(lines, 'Halfwidth parameters')
            parameters['broad_gauss_v'] = pair(lines, 'Halfwidth parameters', 1)
            parameters['broad_gauss_w'] = pair(lines, 'Halfwidth parameters', 2)
            parameters['broad_lorentz_y'] = pair(lines, 'X and y parameters', 1)
        parameters.update(atom_parameters(lines))
        free_count = int(pair(lines, 'No. of fitted parameters')[-1])
        count = 24 if case == 'cecoal' else 6
        background = next(
            i
            for i, line in enumerate(lines)
            if 'Background Parameters' in line or 'Background Polynomial Parameters' in line
        )
        background_pairs = [
            list(map(float, line.split()))
            for line in lines[background + 1 : background + 1 + count]
        ]
        output['cases'][case] = {
            'source': source,
            'source_sha256': hashlib.sha256(source_file.read_bytes()).hexdigest(),
            'fit_objective': 'weighted-least-squares',
            'background_coefficients': [pair[0] for pair in background_pairs],
            'background_uncertainties': [pair[1] for pair in background_pairs],
            'n_free': free_count,
            'parameters': parameters,
        }
    (ROOT / 'cli_reference.json').write_text(json.dumps(output, indent=2) + '\n')


if __name__ == '__main__':
    main()
