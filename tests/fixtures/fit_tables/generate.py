"""Save a crysta curve reference and derive display factors from the saved numbers."""

import json
import math
import os
import re
import shutil
from pathlib import Path

import crysta

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
SOURCE = ROOT / 'docs/user/cli/pd-neut-tof_ncaf-wish-5bank_start-5/project'
FREE = re.compile(r'(?<!\S)[-+\d.eE]+\(\d*\)(?!\S)')


def data_rows(path):
    text = path.read_text()
    block = next(part for part in text.split('loop_\n')[1:] if part.startswith('_data.'))
    lines = block.splitlines()
    columns = []
    while lines and lines[0].startswith('_'):
        columns.append(lines.pop(0))
    rows = []
    for line in lines:
        if not line.strip() or line.startswith(('loop_', '_')):
            break
        rows.append(dict(zip(columns, line.split(), strict=True)))
    return columns, rows


def sums(rows):
    y = [float(r['_data.intensity_meas']) for r in rows]
    calc = [float(r['_data.intensity_calc']) for r in rows]
    bkg = [float(r['_data.intensity_bkg']) for r in rows]
    su = [float(r['_data.intensity_meas_su']) for r in rows]
    return {
        'n': len(rows),
        'absolute': sum(abs(a - b) for a, b in zip(y, calc, strict=True)),
        'weighted': sum(((a - b) / s) ** 2 for a, b, s in zip(y, calc, su, strict=True)),
        'obs_absolute': sum(abs(a) for a in y),
        'obs_weighted': sum((a / s) ** 2 for a, s in zip(y, su, strict=True)),
        'corrected_absolute': sum(abs(a - b) for a, b in zip(y, bkg, strict=True)),
        'corrected_weighted': sum(((a - b) / s) ** 2 for a, b, s in zip(y, bkg, su, strict=True)),
    }


def factors(total, p):
    return [
        total['absolute'] / total['obs_absolute'],
        math.sqrt(total['weighted'] / total['obs_weighted']),
        math.sqrt((total['n'] - p) / total['obs_weighted']),
        total['absolute'] / total['corrected_absolute'],
        math.sqrt(total['weighted'] / total['corrected_weighted']),
    ]


def scalar(text, tag):
    value = re.search(r'^' + re.escape(tag) + r'\s+(\S+)', text, re.MULTILINE)[1]
    return float(value.split('(')[0])


def bank_reference(path, total_p):
    columns, rows = data_rows(path)
    stats = sums([r for r in rows if r['_data.calc_status'] == 'incl'])
    # Each bank's expected factor uses the whole fitted model's free count,
    # as the documented N-P definition does for the fitted project.
    # d is a conversion even on the missing-value rows. All five banks
    # declare a quadratic calibration and a zero reciprocal term.
    text = path.read_text()

    offset = scalar(text, '_instrument.calib_d_to_tof_offset')
    linear = scalar(text, '_instrument.calib_d_to_tof_linear')
    quadratic = scalar(text, '_instrument.calib_d_to_tof_quadratic')
    for row in rows:
        if row['_data.calc_status'] == 'excl':
            delta = float(row['_data.time_of_flight']) - offset
            row['_data.d_spacing'] = format(
                2 * delta / (linear + math.sqrt(linear * linear + 4 * quadratic * delta)),
                '.12g',
            )
            row['_data.intensity_calc'] = row['_data.intensity_bkg'] = '.'
    prefix = text.split('loop_\n' + columns[0], 1)[0]
    path.write_text(
        prefix
        + 'loop_\n'
        + '\n'.join(columns)
        + '\n'
        + ''.join(' '.join(row[c] for c in columns) + '\n' for row in rows)
    )
    return {
        'name': path.stem,
        'sums': stats,
        'values': factors(stats, total_p),
        'parameters': total_p,
    }


def result_settings(banks, pooled, global_values, total_p):
    settings = (SOURCE / 'analysis/analysis.edi').read_text()
    names = [
        'prof_r_factor',
        'prof_wr_factor',
        'prof_wr_expected',
        'prof_cr_factor',
        'prof_cwr_factor',
    ]
    settings += (
        '\n'
        '_fit_result.result_kind deterministic\n'
        '_fit_result.success true\n'
        '_fit_result.iterations 17\n'
        '_fit_result.fitting_time 1.3\n'
    )
    settings += (
        f'_fit_result.reduced_chi_square {pooled["weighted"] / (pooled["n"] - total_p):.16g}\n'
    )
    settings += ''.join(
        f'_fit_result.{name} {value:.16g}\n'
        for name, value in zip(names, global_values, strict=True)
    )
    settings += '\nloop_\n_fit_result_bank.experiment_id\n_fit_result_bank.n_data_points\n'
    settings += ''.join(f'_fit_result_bank.{name}\n' for name in names)
    settings += '_fit_result_bank.chi_square\n'
    settings += ''.join(
        bank['name']
        + ' '
        + str(bank['sums']['n'])
        + ' '
        + ' '.join(format(v, '.16g') for v in bank['values'])
        + ' '
        + format(bank['sums']['weighted'], '.16g')
        + '\n'
        for bank in banks
    )
    # Phase display values are hand-declared independent inputs, not physics oracles.
    settings += (
        '\n'
        'loop_\n'
        '_fit_result_phase.experiment_id\n'
        '_fit_result_phase.structure_id\n'
        '_fit_result_phase.bragg_r_factor\n'
        '_fit_result_phase.f_r_factor\n'
    )
    settings += ''.join(
        f'{bank["name"]} ncaf {0.02 + i * 0.01} {0.01 + i * 0.005}\n'
        for i, bank in enumerate(banks)
    )
    return settings


def single_dataset(destination, settings, banks):
    one = HERE / 'one'
    if one.exists():
        shutil.rmtree(one)
    shutil.copytree(destination, one)
    for path in (one / 'experiments').glob('*.edi'):
        if path.stem != banks[0]['name']:
            path.unlink()
    lines = settings.splitlines()
    first = next(i for i, line in enumerate(lines) if line.startswith('_fit_result.'))
    one_settings = (
        '_edi.schema_version 4\n_fitting_mode.type single\n' + '\n'.join(lines[first:]) + '\n'
    )
    one_settings = (
        '\n'.join(
            line
            for line in one_settings.splitlines()
            if not any(line.startswith(bank['name'] + ' ') for bank in banks[1:])
        )
        + '\n'
    )
    names = [
        'prof_r_factor',
        'prof_wr_factor',
        'prof_wr_expected',
        'prof_cr_factor',
        'prof_cwr_factor',
    ]
    for name, value in zip(names, banks[0]['values'], strict=True):
        one_settings = re.sub(
            r'(?m)^_fit_result\.' + name + r'\s+\S+',
            f'_fit_result.{name} {value:.16g}',
            one_settings,
        )
    (one / 'analysis/analysis.edi').write_text(one_settings)


def generate():
    destination = HERE / 'five'
    if destination.exists():
        shutil.rmtree(destination)
    model = crysta.Project.load(SOURCE)
    model.analysis.fit()
    model.analysis.calculate()
    model.save_as(destination)
    shared_p = sum(len(FREE.findall(p.read_text())) for p in (SOURCE / 'structures').glob('*.edi'))
    total_p = shared_p + sum(
        len(FREE.findall(p.read_text())) for p in (SOURCE / 'experiments').glob('*.edi')
    )
    banks = [
        bank_reference(path, total_p)
        for path in sorted((destination / 'experiments').glob('*.edi'))
    ]
    pooled = {key: sum(bank['sums'][key] for bank in banks) for key in banks[0]['sums']}
    global_values = factors(pooled, total_p)
    settings = result_settings(banks, pooled, global_values, total_p)
    (destination / 'analysis/analysis.edi').write_text(settings)
    single_dataset(destination, settings, banks)
    provenance = {
        'source': (
            'crysta fit and forward calculation, then textbook sums of saved '
            'curves; timing and phase display records are authored'
        ),
        'crysta_sha': os.environ['CRYSTA_REFERENCE_SHA'],
        'input': str(SOURCE.relative_to(ROOT)),
        'parameters': total_p,
        'banks': banks,
        'pooled': pooled,
        'global_values': global_values,
        'bank1_brief_percent': [12.03, 4.66, 4.45, 29.41, 15.34],
    }
    (HERE / 'reference.json').write_text(json.dumps(provenance, indent=2) + '\n')
    print(
        'NCAF bank 1 percentages:', [round(v * 100, 2) for v in banks[0]['values']], 'P=', total_p
    )


if __name__ == '__main__':
    generate()
