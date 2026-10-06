"""Read the owner-supplied FullProf run; never compute expectations with edi."""

import hashlib
import re
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
HOME = ROOT / 'knowledge/fitting/fullprof/pd-neut-cwl_yap-spodi_3k'
NUMBER = r'[-+]?\d*\.\d+(?:[Ee][-+]?\d+)?'
SITES = {
    'YAlO3': {'Y': ('c', 4), 'Al': ('a', 4), 'O1': ('c', 4), 'O2': ('d', 8)},
    'Al2O3': {'Al1': ('c', 12), 'O1': ('e', 18)},
}


def reference(*, asymmetry_off=False):
    summary = 'asymmetry-off.sum' if asymmetry_off else 'yap_3k.sum'
    text = (HOME / summary).read_text()
    result = {
        'parameters': {},
        'phases': {},
        'rwp': 0.0467 if asymmetry_off else 0.0408,
        'n_free': 52 if asymmetry_off else 56,
    }
    parts = re.split(r'=> Phase No\.\s+\d+', text)[1:]
    for name, part in zip(SITES, parts, strict=True):
        values = re.findall(r'(' + NUMBER + r')\(\s*(\d+)\)', part)
        sites = {}
        for index, site in enumerate(SITES[name]):
            row = values[index * 5 : index * 5 + 5]
            fields = {}
            for field, (value, uncertainty) in zip(
                ('fract_x', 'fract_y', 'fract_z', 'adp_iso', 'occupancy'), row, strict=True
            ):
                su = int(uncertainty) * 10 ** -len(value.split('.')[1])
                fields[field] = [float(value), su]
                if su:
                    result['parameters'][f'{name}.{site}.{field}'] = [float(value), su]
            sites[site] = fields
        cell = part.split('=> Cell parameters')[1].split('=> overall scale')[0]
        cell = [
            list(map(float, row.split()))
            for row in cell.splitlines()
            if re.match(r'^\s+' + NUMBER + r'\s+' + NUMBER + r'\s*$', row)
        ]
        for field, (value, su) in zip(
            ('length_a', 'length_b', 'length_c', 'angle_alpha', 'angle_beta', 'angle_gamma'),
            cell,
            strict=True,
        ):
            if su and not (name == 'Al2O3' and field == 'length_b'):
                result['parameters'][f'{name}.cell.{field}'] = [value, su]
        scale = re.search(
            r'=> overall scale factor\s*:\s*(' + NUMBER + r')\s+(' + NUMBER + r')', part
        )
        result['parameters'][f'{name}.scale'] = list(map(float, scale.groups()))
        result['phases'][name] = {'sites': sites, 'cell': cell, 'scale': float(scale[1])}
    first = parts[0]
    widths = first.split('=> Halfwidth parameters')[1].split('=> Preferred orientation')[0]
    for field, row in zip(
        ('broad_gauss_u', 'broad_gauss_v', 'broad_gauss_w'),
        re.findall(r'(' + NUMBER + r')\s+(' + NUMBER + r')', widths),
        strict=True,
    ):
        result['parameters'][f'profile.{field}'] = list(map(float, row))
    eta = re.search(
        r'=> Eta\(p-v\) or m\(p-vii\)\s*:\s*(' + NUMBER + r')\s+(' + NUMBER + r')', first
    )
    result['parameters']['profile.eta'] = list(map(float, eta.groups()))
    global_part = text.split('==> GLOBAL PARAMETERS')[1]
    shift = re.search(r'=> Zero-point:\s*(' + NUMBER + r')\s+(' + NUMBER + r')', global_part)
    result['parameters']['instrument.calib_twotheta_offset'] = list(map(float, shift.groups()))
    background = global_part.split('=> Background Parameters')[1].split('=> Cos(2theta)')[0]
    for i, row in enumerate(re.findall(r'(' + NUMBER + r')\s+(' + NUMBER + r')', background)):
        result['parameters'][f'background.{i + 1}'] = list(map(float, row))
    result['digests'] = {
        name: hashlib.sha256((HOME / name).read_bytes()).hexdigest()
        for name in (
            ('asymmetry-off.inp', 'asymmetry-off.out', 'asymmetry-off.sum', 'yap_3k.dat')
            if asymmetry_off
            else ('yap_3k.pcr', 'yap_3k.sum', 'yap_3k.prf', 'yap_3k.dat')
        )
    }
    return result


def write_control(root):
    ref = reference()['phases']['YAlO3']
    (root / 'structures').mkdir(parents=True)
    (root / 'experiments').mkdir()
    text = 'data_YAlO3\n_edi.schema_version 3\n'
    text += ''.join(
        f'_cell.{key} {value}\n'
        for key, (value, su) in zip(
            ('length_a', 'length_b', 'length_c', 'angle_alpha', 'angle_beta', 'angle_gamma'),
            ref['cell'],
            strict=True,
        )
    )
    text += '_space_group.name_h_m "P b n m"\n'
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
            'adp_iso',
            'adp_type',
        )
    )
    for name, fields in ref['sites'].items():
        text += (
            f'{name} {re.sub(r"\d", "", name)} {SITES["YAlO3"][name][0]} '
            + ' '.join(str(fields[key][0]) for key in ('fract_x', 'fract_y', 'fract_z'))
            + f' 1 {fields["adp_iso"][0]} Biso\n'
        )
    (root / 'structures/YAlO3.edi').write_text(text)
    text = (
        """data_spodi
_edi.schema_version 3
_experiment_type.beam_mode "constant wavelength"
_scattering_source.neutron_scattering_length sears1992
_instrument.setup_wavelength 1.54816
_instrument.calib_twotheta_offset 0.0015
_peak.type cwl-pseudo-voigt-berar-baldinozzi
_peak.broad_gauss_u 0.03889
_peak.broad_gauss_v -0.04620
_peak.broad_gauss_w 0.10586
_peak.mixing_eta_0 0.13947
_peak.mixing_eta_1 0
_peak.asym_beba_a0 0
_peak.asym_beba_b0 0
_peak.asym_beba_a1 0
_peak.asym_beba_b1 0
_peak.asym_beba_limit 160
_peak.cutoff_fwhm 20
loop_
_linked_structure.structure_id
_linked_structure.scale
"""
        f'YAlO3 {ref["scale"]}\n'
    )
    data = np.loadtxt(HOME / 'yap_3k.dat')
    grid = data[(data[:, 0] >= 4.05) & (data[:, 0] <= 151.95), 0][::23]
    text += '\nloop_\n_data.two_theta\n_data.intensity_meas\n_data.intensity_meas_su\n' + ''.join(
        f'{x} 0 1\n' for x in grid
    )
    (root / 'experiments/spodi.edi').write_text(text)
    return root


def actual_values(project, *, asymmetry_off=False):
    values = {}
    ref = reference(asymmetry_off=asymmetry_off)
    e = project.experiments[0]
    links = getattr(e, 'linked_structures', None)
    if links is None:
        links = e.linked_structure
    for key in ref['parameters']:
        bits = key.split('.')
        if bits[0] in SITES:
            s = project.structures[bits[0]]
            if bits[1] == 'scale':
                value = links[bits[0]].scale.value
            elif bits[1] == 'cell':
                value = getattr(s.cell, bits[2]).value
            else:
                site = next(site for site in s.atom_sites if site.id == bits[1])
                value = getattr(site, bits[2]).value
        elif bits[0] == 'profile':
            field = bits[1]
            if field == 'eta':
                field = 'mixing_eta_0'
            value = getattr(e.peak, field).value
        elif bits[0] == 'instrument':
            value = getattr(e.instrument, bits[1]).value
        else:
            value = e.background[int(bits[1]) - 1].intensity.value
        values[key] = float(value)
    return values
