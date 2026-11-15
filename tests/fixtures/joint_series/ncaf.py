"""Copied NCAF observations, seeded from the committed FullProf optimum."""

import json
import shutil
from pathlib import Path

import gemmi

ROOT = Path(__file__).resolve().parents[3]
CASE = ROOT / 'docs/user/cli/pd-neut-tof_ncaf-wish-5bank_start-fullprof'
BANKS = ('wish_5_6', 'wish_4_7', 'wish_3_8', 'wish_2_9', 'wish_1_10')


def prepare(destination, *, points, descent):
    shutil.copytree(CASE / 'project', destination)
    (destination / 'scan').mkdir()
    for bank in BANKS:
        text = (destination / f'experiments/{bank}.edi').read_text()
        block = gemmi.cif.read_string(text).sole_block()
        table = block.find([
            '_data.time_of_flight',
            '_data.intensity_meas',
            '_data.intensity_meas_su',
        ])
        pattern = ''.join(' '.join(row) + '\n' for row in table)
        for point in range(points):
            (destination / 'scan' / f'P{point:04d}_{bank}.xye').write_text(pattern)
    analysis = destination / 'analysis/analysis.edi'
    text = analysis.read_text().replace(
        '_fitting_mode.type joint', '_fitting_mode.type sequential'
    )
    text += (
        f'\n_minimizer.descent {descent}\n_minimizer.max_iterations 3\n'
        '_minimizer.stop_rules chi_square_change\n_sequential_fit.data_dir scan\n'
        'loop_\n_sequential_fit_experiment.experiment_id\n_sequential_fit_experiment.file_pattern\n'
    )
    text += ''.join(f'{bank} "*_{bank}.xye"\n' for bank in BANKS)
    analysis.write_text(text)
    return destination


def atom_references():
    quantities = json.loads((CASE / 'expected.json').read_text())['quantities']
    return {
        key.removeprefix('param.').removesuffix('.value'): value
        for key, value in quantities.items()
        if key.startswith('param.') and value['kind'] == 'reference'
    }
