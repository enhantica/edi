"""Authored save-boundary witnesses; numeric expectations come from decimals and rationals."""

import math
import re
import shutil
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
MEASURED = ((20, 1.23, 1), (30, 1.24, 2), (40, 1.25, 1), (50, 1.26, 2))


def agreement(calculated):
    residuals = [y - calculated for _, y, _ in MEASURED]
    chi = math.fsum((r / sigma) ** 2 for r, (_, _, sigma) in zip(residuals, MEASURED, strict=True))
    norm = math.fsum((y / sigma) ** 2 for _, y, sigma in MEASURED)
    return {
        'prof_r_factor': math.fsum(abs(r) for r in residuals)
        / math.fsum(y for _, y, _ in MEASURED),
        'prof_wr_factor': math.sqrt(chi / norm),
        'chi_square': chi,
    }


def base(destination):
    destination = Path(destination)
    shutil.copytree(HERE.parent / 'loop_parameter_ids/line-segment', destination)
    return destination


def special_position(destination):
    root = base(destination)
    path = root / 'structures/phase.edi'
    text = path.read_text().replace('"P 1"', '"P 63/m m c"')
    text = text.replace('_cell.length_c 4.1', '_cell.length_c 5.3')
    text = text.replace('_cell.angle_gamma 90', '_cell.angle_gamma 119.99999999999999')
    text = text.replace(
        'La a Biso 0.17 0.23 0.31', 'La c Biso 0.3333333333333333 0.6666666666666666 0.25'
    )
    path.write_text(text)
    return root


def ordinary_position(destination):
    root = base(destination)
    path = root / 'structures/phase.edi'
    path.write_text(path.read_text().replace('0.17 0.23 0.31', '0.123456789 0.23 0.31'))
    return root


def bank_angle(destination, *, exact=False):
    root = Path(destination)
    shutil.copytree(HERE.parent / 'background_estimate/basis-loader/tof', root)
    path = root / 'experiments/pearl.edi'
    text = path.read_text().replace('data_pearl', 'data_bank')
    text = re.sub(
        r'(?m)^_instrument.setup_twotheta_bank .*$',
        '_instrument.setup_twotheta_bank 94.90931761529106',
        text,
    )
    text = text.replace('_background_estimate.mode auto', '_background_estimate.mode manual')
    if exact:
        guard = (HERE.parent / 'loop_parameter_ids/line-segment/experiments/bank.edi').read_text()
        guard = guard.replace('data_bank', 'data_guard').replace('phase ', 'ceo2 ')
        for term, value in [
            ('calib_sample_displacement', '9e307'),
            ('calib_sample_transparency', '8.9e307'),
        ]:
            token = format(Decimal(value), 'f') + '(' + format(Decimal('3e307'), 'f') + '.)'
            tag = '_instrument.' + term
            line = tag + ' ' + token
            guard = (
                re.sub(r'(?m)^' + re.escape(tag) + r' .*$', line, guard)
                if tag + ' ' in guard
                else guard + '\n' + line + '\n'
            )
        (root / 'experiments/guard.edi').write_text(guard)
        record = root / 'project.edi'
        record.write_text(record.read_text() + '\n_su_format.rule iucr_19\n')
    (root / 'experiments/bank.edi').write_text(text)
    path.unlink()
    return root


def mixed_project(destination, *, empty=False, provenance='stale'):
    root = base(destination)
    (root / 'analysis/analysis.edi').write_text(
        '_edi.schema_version 3\n_fitting_mode.type joint\n'
        '_fit_result.result_kind deterministic\n_fit_result.success true\n'
        '_fit_result.prof_wr_factor 0.9\n_fit_result.reduced_chi_square 1\n'
        'loop_\n_fit_result_bank.experiment_id\n_fit_result_bank.n_data_points\n'
        '_fit_result_bank.prof_r_factor\n_fit_result_bank.prof_wr_factor\n'
        '_fit_result_bank.chi_square\ncurrent 4 0.9 0.9 1\ndue 4 0.9 0.9 1\n'
    )
    analysis = root / 'analysis/analysis.edi'
    old = agreement(1.23456789)
    analysis.write_text(
        analysis.read_text().replace(
            'current 4 0.9 0.9 1',
            'current 4 '
            + ' '.join(
                format(old[key], '.17g')
                for key in ('prof_r_factor', 'prof_wr_factor', 'chi_square')
            ),
        )
    )
    common = """data_BANK
_edi.schema_version 3
_experiment_type.sample_form powder
_experiment_type.radiation_probe neutron
_experiment_type.scattering_type bragg
_experiment_type.beam_mode "constant wavelength"
_peak.type cwl-tch-pseudo-voigt
_peak.cutoff_fwhm 5
_peak.broad_gauss_u 0
_peak.broad_gauss_v 0
_peak.broad_gauss_w 0.15
_peak.broad_lorentz_x 0
_peak.broad_lorentz_y 0
_instrument.calib_twotheta_offset 0
_instrument.setup_wavelength 1.5
_background.type line-segment
_background_estimate.mode MODE
_background_estimate.method snip
_background_estimate.use_model ignore
_background_estimate.n_points 3
loop_
_linked_structure.structure_id
_linked_structure.scale
phase 0
loop_
_background.id
_background.position
_background.intensity
left 20 1.23456789
right 50 1.23456789
loop_
_data.two_theta
_data.intensity_meas
_data.intensity_meas_su
MEASURED_ROWS
"""
    for path in (root / 'experiments').glob('*.edi'):
        path.unlink()
    for name, mode in [('due', 'auto'), ('current', 'manual')]:
        text = (
            common
            .replace('BANK', name)
            .replace('MODE', mode)
            .replace(
                'MEASURED_ROWS', '\n'.join(f'{x} {y:.17g} {sigma}' for x, y, sigma in MEASURED)
            )
        )
        if name == 'due':
            text = text.replace('left 20 1.23456789', 'left 20 2.34567891()')
            text = text.replace('right 50 1.23456789', 'right 50 3.45678912')
            if empty:
                text = re.sub(
                    r'loop_\n_background.id\n.*?(?=loop_\n_data)', '', text, flags=re.DOTALL
                )
            if provenance == 'stale':
                text += '\n_background_estimate.inputs_digest 123456789abcdef0\n'
        else:
            text = text.replace(
                '_data.intensity_meas_su\n',
                '_data.intensity_meas_su\n_data.d_spacing\n_data.intensity_calc\n_data.intensity_bkg\n_data.calc_status\n',
            )
            for x, y, sigma in MEASURED:
                text = text.replace(
                    f'{x} {y:.17g} {sigma}\n',
                    (
                        f'{x} {y:.17g} {sigma} '
                        f'{1.5 / (2 * math.sin(math.radians(x / 2))):.17g} '
                        '1.23456789 1.23456789 incl\n'
                    ),
                )
        (root / 'experiments' / (name + '.edi')).write_text(text)
    return root


def prepared_mixed(engine, root, *, empty=False, provenance='stale'):
    root = mixed_project(root, empty=empty, provenance=provenance)
    return engine.Project.load(root), root


def bank_state(bank):
    return {
        'type': bank.background_type,
        'rows': [
            (p.id, p.position, p.intensity.value, p.intensity.uncertainty, p.intensity.free)
            for p in bank.background
        ],
        'terms': [
            (p.id, p.order, p.coef.value, p.coef.uncertainty, p.coef.free)
            for p in bank.background_terms
        ],
        'origin': bank.background_origin,
        'x_min': bank.background_x_min,
        'x_max': bank.background_x_max,
        'mode': bank.background_estimate.mode,
        'settings': {
            key: getattr(bank.background_estimate, key)
            for key in (
                'method',
                'width',
                'smoothness',
                'n_points',
                'max_terms',
                'tolerance',
                'in_peaks',
                'use_model',
            )
        },
    }


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    for is_empty in (False, True):
        for state in ('stale', 'absent'):
            mixed_project(
                args.destination / (('empty' if is_empty else 'points') + '-' + state),
                empty=is_empty,
                provenance=state,
            )
