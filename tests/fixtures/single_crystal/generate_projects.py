"""Translate the frozen FullProf structures and derive decimal extinction samples."""

from __future__ import annotations

import json
from decimal import Decimal, localcontext
from pathlib import Path

HERE = Path(__file__).resolve().parent
SUFFIXES = ('11', '22', '33', '12', '13', '23')


def structure(case, stem):  # noqa: PLR0914 - the external structure table
    lines = (HERE / 'fullprof' / case / f'{stem}.pcr').read_text().splitlines()
    output = (HERE / 'fullprof' / case / f'{stem}.out').read_text()
    symbol = next(line.split('<--')[0].strip() for line in lines if '<--Space group' in line)
    group_order = {'F m m m': 32, 'F d -3 m': 192, 'P 21/c': 4}[symbol]
    table = output.split('=> Initial parameters ==>')[1].split('=> It is assumed')[0]
    multiplicities = {}
    for line in table.splitlines():
        fields = line.split()
        if len(fields) == 11 and fields[1].isalpha() and fields[-1].isdigit():
            multiplicities[fields[0]] = int(fields[-1])
    cell_index = next(i for i, line in enumerate(lines) if '# Cell Info' in line)
    cell = lines[cell_index + 1].split()[:6]
    text = f'data_structure\n_edi.schema_version 3\n_space_group.name_h_m "{symbol}"\n'
    code = {'F d -3 m': '2', 'F m m m': 'abc', 'P 21/c': 'b1'}[symbol]
    text += f'_space_group.coord_system_code {code}\n'
    names = ('length_a', 'length_b', 'length_c', 'angle_alpha', 'angle_beta', 'angle_gamma')
    text += ''.join(f'_cell.{key} {value}\n' for key, value in zip(names, cell, strict=True))
    text += 'loop_\n' + ''.join(
        f'_atom_site.{key}\n'
        for key in (
            'id',
            'type_symbol',
            'wyckoff_letter',
            'fract_x',
            'fract_y',
            'fract_z',
            'occupancy',
            'adp_type',
            'adp_iso',
        )
    )
    tensors = []
    for i, line in enumerate(lines):
        fields = line.split()
        if len(fields) < 11 or fields[0] not in multiplicities:
            continue
        label, element = fields[:2]
        letters = (
            {'Pr': 'i', 'Ni': 'a', 'O1': 'e', 'O2': 'i', 'Oi': 'f', 'Od': 'p'}
            if symbol == 'F m m m'
            else {'Tb': 'd', 'Ti': 'c', 'O1': 'f', 'O2': 'b'}
        )
        letter = 'e' if symbol == 'P 21/c' else letters[label]
        occupancy = Decimal(fields[6]) * group_order / multiplicities[label]
        kind = 'beta' if fields[9] == '2' else 'Biso'
        text += (
            ' '.join([
                label,
                element.title(),
                letter,
                *fields[2:5],
                str(occupancy),
                kind,
                fields[5],
            ])
            + '\n'
        )
        if kind == 'beta':
            tensors.append(label + ' ' + ' '.join(lines[i + 2].split()[:6]))
    if tensors:
        text += 'loop_\n_atom_site_aniso.id\n'
        text += ''.join(f'_atom_site_aniso.adp_{key}\n' for key in SUFFIXES)
        text += '\n'.join(tensors) + '\n'
    return text


def main():  # noqa: PLR0914 - independent decimal sample variables
    reference = json.loads((HERE / 'fullprof.json').read_text())
    for case, record in reference['cases'].items():
        path = HERE / 'projects' / case
        (path / 'structures').mkdir(parents=True, exist_ok=True)
        (path / 'experiments').mkdir(exist_ok=True)
        (path / 'structures/structure.edi').write_text(structure(case, record['stem']))
        pcr = (HERE / 'fullprof' / case / (record['stem'] + '.pcr')).read_text()
        scale = pcr.split('!   Sc1')[1].splitlines()[1].split()[0]
        tof = 'tof' in case
        text = 'data_experiment\n_edi.schema_version 3\n'
        text += '_experiment_type.sample_form "single crystal"\n'
        text += (
            '_experiment_type.radiation_probe neutron\n_experiment_type.scattering_type bragg\n'
        )
        text += (
            '_experiment_type.beam_mode "'
            + ('time-of-flight' if tof else 'constant wavelength')
            + '"\n'
        )
        text += '_scattering_source.neutron_scattering_length sears1992\n'
        if not tof:
            wavelength = (
                (HERE / 'fullprof' / case / (record['stem'] + '.int'))
                .read_text()
                .splitlines()[2]
                .split()[0]
            )
            text += f'_instrument.setup_wavelength {wavelength}\n'
        if 'extinction' in case:
            text += '_extinction.type becker-coppens\n_extinction.model gauss\n'
            text += '_extinction.radius 10\n_extinction.mosaicity 35000\n'
        text += 'loop_\n_linked_structure.structure_id\n_linked_structure.scale\n'
        text += f'structure {scale}\nloop_\n'
        text += ''.join(
            f'_refln.{key}\n'
            for key in ('index_h', 'index_k', 'index_l', 'intensity_meas', 'intensity_meas_su')
        )
        if tof:
            text += '_refln.wavelength\n'
        text += ''.join(' '.join(str(v) for v in row) + '\n' for row in record['input_rows'])
        (path / 'experiments/experiment.edi').write_text(text)
    samples = []
    with localcontext() as ctx:
        ctx.prec = 50
        dec = Decimal
        pi = dec('3.14159265358979323846264338327950288419716939937510')
        for hkl, wavelength, radius, mosaicity in (
            ([2, 1, 3], '1.6', '0', '37'),
            ([2, 1, 3], '1.6', '12.7', '37'),
            ([2, 1, 3], '1.6', '91.3', '35000'),
            ([4, 1, 3], '1.9', '28.4', '43000'),
            ([4, 1, 3], '1.9', '91.3', '0'),
        ):
            cell = [dec(v) for v in ('5.1', '6.2', '7.3')]
            lam, r, g = dec(wavelength), dec(radius), dec(mosaicity) * pi / 10800
            volume = cell[0] * cell[1] * cell[2]
            s2 = sum((dec(h) / a) ** 2 for h, a in zip(hkl, cell, strict=True)) / 4
            f2 = (dec('1.03') * dec('0.73')) ** 2 * (-2 * dec('0.41') * s2).exp()
            c = 1 - 2 * lam**2 * s2
            x = dec('1.5') * f2 * (lam * r / volume) ** 2
            yp = (
                1
                + 2 * x
                + (dec('.2') + dec('.45') * c)
                * x
                * x
                / (1 + (dec('.22') - dec('.12') * (dec('.5') - c) ** 2) * x)
            ).sqrt() ** -1
            row = {
                'hkl': hkl,
                'cell': [str(v) for v in cell],
                'wavelength': wavelength,
                'radius': radius,
                'mosaicity': mosaicity,
                'f2': str(f2),
                'primary': str(yp),
            }
            for model in ('gauss', 'lorentz'):
                denominator = (
                    ((g * lam) ** 2 + dec('1.125') * r * r * (1 - c * c)).sqrt()
                    if model == 'gauss'
                    else g * lam + r * (1 - c * c).sqrt()
                )
                xs = x * lam * g / denominator if r * g else dec(0)
                a = (
                    dec('.58') + dec('.48') * c + dec('.24') * c * c
                    if model == 'gauss'
                    else dec('.025') + dec('.285') * c
                )
                b = (
                    dec('.02') - dec('.025') * c
                    if model == 'gauss'
                    else (
                        dec('.15') - dec('.2') * (dec('.75') - c) ** 2
                        if c > 0
                        else -dec('.45') * c
                    )
                )
                k = dec('2.12') if model == 'gauss' else dec(2)
                row[model] = str(yp / (1 + k * xs + a * xs * xs / (1 + b * xs)).sqrt())
            samples.append(row)
    (HERE / 'extinction.json').write_text(json.dumps(samples, indent=2) + '\n')


if __name__ == '__main__':
    main()
