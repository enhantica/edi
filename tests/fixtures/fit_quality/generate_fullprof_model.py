"""Build a fixed calculation subject from the matched FullProf PCR and profile."""

import argparse
import hashlib
import json
from pathlib import Path


def after(lines, marker):
    index = next(i for i, line in enumerate(lines) if line.startswith(marker))
    return list(map(float, lines[index + 1].split('#')[0].split()))


def structure_text(lines):
    text = 'data_lbco\n_edi.schema_version 3\n'
    for name, value in zip(
        ('length_a', 'length_b', 'length_c', 'angle_alpha', 'angle_beta', 'angle_gamma'),
        after(lines, '!     a '),
        strict=True,
    ):
        text += f'_cell.{name} {value:.17g}\n'
    text += '_space_group.name_h_m "P m -3 m"\n\nloop_\n'
    text += ''.join(
        '_atom_site.' + name + '\n'
        for name in (
            'id',
            'type_symbol',
            'fract_x',
            'fract_y',
            'fract_z',
            'wyckoff_letter',
            'occupancy',
            'adp_iso',
            'adp_type',
        )
    )
    for name, letter, multiplicity in (
        ('La', 'a', 1),
        ('Ba', 'a', 1),
        ('Co', 'b', 1),
        ('O', 'c', 3),
    ):
        row = next(line.split() for line in lines if line.startswith(name + ' '))
        x, y, z, adp, occupancy = map(float, row[2:7])
        occupancy *= 48 / multiplicity
        text += (
            f'{name} {name} {x:.17g} {y:.17g} {z:.17g} {letter} {occupancy:.17g} {adp:.17g} Biso\n'
        )
    return text


def data_text(prf, corpus):
    # The PRF owns included points and observations; the matched corpus supplies sigma.
    data = corpus.read_text().split('_data.intensity_meas_su\n', 1)[1]
    measured = {
        round(float(row[0]), 3): (float(row[2]), float(row[3]))
        for line in data.splitlines()
        if (row := line.split())
    }
    profile = prf.read_text().split('BEGIN\n', 1)[1].split('END', 1)[0]
    text = 'loop_\n_data.two_theta\n_data.intensity_meas\n_data.intensity_meas_su\n'
    for line in profile.splitlines():
        x, observed = map(float, line.split()[:2])
        original, sigma = measured[round(x, 3)]
        if observed != original:
            message = 'FullProf and corpus observations must match at every selected point'
            raise ValueError(message)
        text += f'{x:.17g} {observed:.17g} {sigma:.17g}\n'
    return text


def experiment_text(lines):
    text = (
        'data_hrpt\n_edi.schema_version 3\n_experiment_type.sample_form powder\n'
        '_experiment_type.beam_mode "constant wavelength"\n'
        '_experiment_type.radiation_probe neutron\n_experiment_type.scattering_type bragg\n'
        '_peak.type cwl-tch-pseudo-voigt\n'
    )
    for name, value in zip(
        ('broad_gauss_u', 'broad_gauss_v', 'broad_gauss_w', 'broad_lorentz_x', 'broad_lorentz_y'),
        after(lines, '!       U ')[:5],
        strict=True,
    ):
        text += f'_peak.{name} {value:.17g}\n'
    text += f'_peak.cutoff_fwhm {after(lines, "! Lambda1")[4]:.17g}\n'
    text += f'_instrument.setup_wavelength {after(lines, "! Lambda1")[0]:.17g}\n'
    text += f'_instrument.calib_twotheta_offset {after(lines, "!  Zero ")[0]:.17g}\n'
    text += (
        'loop_\n_linked_structure.structure_id\n_linked_structure.scale\n'
        f'lbco {after(lines, "!  Scale ")[0]:.17g}\n'
    )
    text += (
        '_background.type line-segment\nloop_\n_background.id\n'
        '_background.position\n_background.intensity\n'
    )
    start = next(i for i, line in enumerate(lines) if line.startswith('!2Theta/TOF')) + 1
    for index, line in enumerate(lines[start:], 1):
        if line.startswith('!'):
            break
        position, intensity = map(float, line.split()[:2])
        text += f'{index} {position:.17g} {intensity:.17g}\n'
    return text


def materialize(pcr, prf, corpus, destination):
    lines = pcr.read_text().splitlines()
    destination.mkdir(parents=True, exist_ok=True)
    for directory in ('structures', 'experiments', 'analysis'):
        (destination / directory).mkdir(exist_ok=True)
    (destination / 'structures/lbco.edi').write_text(structure_text(lines))
    (destination / 'experiments/hrpt.edi').write_text(
        experiment_text(lines) + data_text(prf, corpus)
    )
    (destination / 'analysis/analysis.edi').write_text(
        '_edi.schema_version 3\n_fitting_mode.type single\n'
    )
    (destination / 'project.edi').write_text(
        '_edi.schema_version 3\n_metadata.name lbco_fullprof_fixed_model\n'
    )


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('pcr', 'prf', 'corpus', 'destination'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    materialize(args.pcr, args.prf, args.corpus, args.destination)

    manifest_path = args.destination.parent / 'inputs.json'
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        for directory in ('fullprof', 'fullprof-model'):
            for artifact in sorted((args.destination.parent / directory).rglob('*')):
                if artifact.is_file():
                    manifest[str(artifact.relative_to(args.destination.parent))] = hashlib.sha256(
                        artifact.read_bytes()
                    ).hexdigest()
        manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
