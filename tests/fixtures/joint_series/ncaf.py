"""Copied NCAF observations, seeded from the committed FullProf optimum."""

import json
import re
import shutil
from pathlib import Path

import gemmi
import numpy as np
import pytest

from tests.fixtures.joint_series.cases import clear_free_flags

ROOT = Path(__file__).resolve().parents[3]
CASE = ROOT / 'docs/user/cli/pd-neut-tof_ncaf-wish-5bank_start-fullprof'
BANKS = ('wish_5_6', 'wish_4_7', 'wish_3_8', 'wish_2_9', 'wish_1_10')

MAX_POINTS = 100


def prepare(destination, *, points, descent, small=False):
    assert 1 <= points <= MAX_POINTS, 'Owner 6c4f7a9d9 caps seeded cadence at 100 points'
    shutil.copytree(CASE / 'project', destination)
    (destination / 'scan').mkdir()
    banks = BANKS[:2] if small else BANKS
    if small:
        reduced_template(destination, banks)
    for bank in banks:
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
    text = analysis.read_text()
    if small:
        text = (
            '\n'.join(
                line
                for line in text.splitlines()
                if not any(line.startswith(bank + ' ') for bank in BANKS[2:])
            )
            + '\n'
        )
    text = text.replace('_fitting_mode.type joint', '_fitting_mode.type sequential')
    text += (
        f'\n_minimizer.descent {descent}\n_minimizer.max_iterations 3\n'
        '_minimizer.stop_rules chi_square_change\n_sequential_fit.data_dir scan\n'
        'loop_\n_sequential_fit_experiment.experiment_id\n_sequential_fit_experiment.file_pattern\n'
    )
    text += ''.join(f'{bank} "*_{bank}.xye"\n' for bank in banks)
    analysis.write_text(text)
    return destination


def atom_references():
    quantities = json.loads((CASE / 'expected.json').read_text())['quantities']
    return {
        key.removeprefix('param.').removesuffix('.value'): value
        for key, value in quantities.items()
        if key.startswith('param.') and value['kind'] == 'reference'
    }


def fixed_atoms(project):
    for name, reference in atom_references().items():
        atom, quantity = name.split('.')
        parameter = getattr(
            next(a for a in project.structures['ncaf'].atom_sites if a.id == atom), quantity
        )
        assert not parameter.free, 'The reduced fixture must keep structural references fixed'
        assert parameter.value == pytest.approx(reference['value'], abs=reference['tol_abs']), (
            'Fixed NCAF inputs must retain the independently committed FullProf atom references'
        )


def linear_scales(project, prepared_profiles=None):
    """Known fixed profiles: solve each bank's one-dimensional weighted least squares."""
    fixed_atoms(project)
    assert len(project.free_parameters) == 2, (
        'The small two-bank reference has exactly two independent bank scale parameters'
    )
    result, sums, n = {}, [], 0
    baselines, profiles = (
        prepared_profiles if prepared_profiles is not None else linear_profiles(project)
    )
    for bank in BANKS[:2]:
        experiment = project.experiments[bank]
        baseline, profile = baselines[bank], profiles[bank]
        su = np.asarray(experiment.data.intensity_meas_su)
        target = np.asarray(experiment.data.intensity_meas) - baseline
        mask = np.isfinite(profile) & np.isfinite(target) & np.isfinite(su) & (su > 0)
        grid = np.asarray(experiment.data.time_of_flight)
        for lower, upper in experiment.excluded_regions:
            mask &= (grid < lower) | (grid > upper)
        profile, target, su = profile[mask], target[mask], su[mask]
        assert len(profile) > 1, (
            'The linear reference must use actual finite, unexcluded measurements'
        )
        fitted = float(np.dot(profile / su, target / su) / np.dot(profile / su, profile / su))
        information = float(np.dot(profile / su, profile / su))
        sums.append(float(np.sum(((target - fitted * profile) / su) ** 2)))
        n += len(target)
        result[bank] = fitted, information
    chi = sum(sums) / (n - 2)
    return {
        bank: (value, np.sqrt(chi / information)) for bank, (value, information) in result.items()
    }


def sparse_observations(file):
    # The PR witness keeps real WISH bins; the slow entry retains every bin.
    block = gemmi.cif.read_string(file.read_text()).sole_block()
    loop = block.find_loop('_data.time_of_flight').get_loop()
    width = loop.width()
    rows = range(0, loop.length(), 8)
    values = loop.values
    loop.set_all_values([
        [values[row * width + column] for row in rows] for column in range(width)
    ])
    file.write_text(block.as_string())


def linear_profiles(project):
    scales = [project.experiments[bank].linked_structures['ncaf'].scale for bank in BANKS[:2]]
    initial = [scale.value for scale in scales]
    for scale in scales:
        scale.value = 0
    project.analysis.calculate()
    baselines = {
        bank: np.asarray(project.experiments[bank].data.intensity_calc).copy()
        for bank in BANKS[:2]
    }
    for scale in scales:
        scale.value = 1
    project.analysis.calculate()
    profiles = {
        bank: np.asarray(project.experiments[bank].data.intensity_calc).copy() - baselines[bank]
        for bank in BANKS[:2]
    }
    for scale, value in zip(scales, initial, strict=True):
        scale.value = value
    return baselines, profiles


def reduced_template(destination, banks):
    for file in (destination / 'experiments').glob('*.edi'):
        if file.stem not in banks:
            file.unlink()
        else:
            file.write_text(clear_free_flags(file.read_text()))
    for file in (destination / 'structures').glob('*.edi'):
        file.write_text(clear_free_flags(file.read_text()))
    for file in (destination / 'experiments').glob('*.edi'):
        file.write_text(file.read_text().replace('ncaf  ', 'ncaf '))
    for file in (destination / 'experiments').glob('*.edi'):
        file.write_text(re.sub(r'(?m)^(ncaf\s+[-+0-9.eE]+)$', r'\1()', file.read_text()))
    for bank in banks:
        sparse_observations(destination / f'experiments/{bank}.edi')
