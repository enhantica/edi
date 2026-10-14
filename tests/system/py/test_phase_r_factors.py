"""Phase identities through each fit path, persistence and a changed-free-set refit."""

import math
import re

import numpy as np
import pytest

from tests.fixtures.phase_factors.reference import axial_profiles
from tests.fixtures.xray_doublet import phase_membership as doublet_phase
from tests.integration.py.test_anisotropic_adps import loop_rows
from tests.system.py.test_latest_fit_uncertainty import ENGINE, vehicle
from tests.system.py.test_powder_r_factors import profile_checks, record, scan_template_background


def isolated_patterns(root, *, zero_background=False):
    parts = []
    for selected in range(2):
        project = ENGINE.Project.load(root)
        experiment = project.experiments[0]
        if zero_background:
            for term in experiment.background_terms:
                term.coef.value = 0
        for index, link in enumerate(experiment.linked_structures):
            link.scale.value = (0.8, 1.2)[index] if index == selected else 0.0
        project.analysis.calculate()
        parts.append(
            np.asarray(experiment.data.intensity_calc).copy()
            - np.asarray(experiment.data.intensity_bkg).copy()
        )
    return parts


def data_text(grid, observed, sigma):
    return ''.join(
        f'{x:.17g} {y:.17g} {s:.17g}\n' for x, y, s in zip(grid, observed, sigma, strict=True)
    )


def phase_vehicle(root, mode):
    vehicle(root, 'multiphase')
    for key, lengths in (('phase', (4.1, 3.95, 2.0)), ('other', (3.6, 3.3, 2.0))):
        path = root / f'structures/{key}.edi'
        text = path.read_text()
        for axis, length in zip('abc', lengths, strict=True):
            text = re.sub(rf'(?m)^_cell.length_{axis} .+$', f'_cell.length_{axis} {length}', text)
        path.write_text(text.replace('0.7 0.3', '0.7 0').replace('0.3 0.8', '0.3 0'))
    experiment = root / 'experiments/bank.edi'
    header = experiment.read_text().split('loop_\n_data.')[0]
    header = header.replace('phase 0\nother 0', 'phase 0.8\nother 1.2')
    header = header.replace('_peak.broad_gauss_w 0.15', '_peak.broad_gauss_w 0.0025')
    header = header.replace('1 0 4()\n2 1 1()\n3 2 3', '1 0 10()\n2 1 0()\n3 2 0')
    header += 'loop_\n_data.two_theta\n_data.intensity_meas\n_data.intensity_meas_su\n'
    grid = np.linspace(20, 29, 901)
    sigma = 0.7 + (np.arange(len(grid)) % 7) / 5
    experiment.write_text(header + data_text(grid, np.full_like(grid, 10), sigma))
    (root / 'analysis/analysis.edi').write_text(
        '_edi.schema_version 3\n_fitting_mode.type single\n'
    )
    parts = isolated_patterns(root)
    # Two separated axial reflections have equal multiplicity and equal neutron |F|.
    masks = [
        [
            np.abs(grid - 2 * math.degrees(math.asin(1.54 / (2 * length)))) < 0.27
            for length in lengths
        ]
        for lengths in ((4.1, 3.95), (3.6, 3.3))
    ]
    assert all(
        np.any(part[mask] > 0) for part, rings in zip(parts, masks, strict=True) for mask in rings
    ), 'Each authored phase must contain two nonempty rings'
    assert not np.any((parts[0] > 0) & (parts[1] > 0)), (
        'The authored phase profiles must not overlap'
    )
    observations = {}
    for name, ratios in {
        'bank': ((1.17, 0.81), (0.93, 1.29)),
        'second': ((0.77, 1.12), (1.23, 0.87)),
    }.items():
        observed = 10 + parts[0] + parts[1]
        for part, rings, phase_ratios in zip(parts, masks, ratios, strict=True):
            for mask, ratio in zip(rings, phase_ratios, strict=True):
                observed[mask] += (ratio - 1) * part[mask]
        observations[name] = observed
    experiment.write_text(header + data_text(grid, observations['bank'], sigma))
    analysis = f'_edi.schema_version 3\n_fitting_mode.type {mode}\n'
    if mode == 'joint':
        (root / 'experiments/second.edi').write_text(
            header.replace('data_bank', 'data_second')
            + data_text(grid, observations['second'], sigma * 1.7)
        )
        analysis += 'loop_\n_joint_fit.experiment_id\n_joint_fit.weight\nbank 1\nsecond 1\n'
    elif mode in {'sequential', 'independent'}:
        folder = root / 'experiments/scan'
        folder.mkdir()
        # The saved template is neither the first nor the terminal scan file.
        for index, observed in enumerate((
            observations['second'],
            observations['bank'],
            observations['second'],
        )):
            (folder / f'{index}.dat').write_text('XYDATA\n' + data_text(grid, observed, sigma))
        analysis += (
            '_sequential_fit.data_dir experiments/scan\n_sequential_fit.file_pattern *.dat\n'
            '_sequential_fit.template_file 1.dat\n'
        )
    (root / 'analysis/analysis.edi').write_text(analysis)
    if mode != 'joint':
        observations.pop('second')
    return ENGINE.Project.load(root), parts, masks, grid, sigma, observations


def phase_checks(project, text, parts, observations, backgrounds=None):
    rows = loop_rows(text, '_fit_result_phase')
    keys = [
        (row['_fit_result_phase.experiment_id'], row['_fit_result_phase.structure_id'])
        for row in rows
    ]
    expected_keys = {(bank, phase) for bank in observations for phase in ('phase', 'other')}
    assert len(keys) == len(expected_keys), (
        '_fit_result_phase must have one row per (experiment_id, structure_id) composite key'
    )
    assert set(keys) == expected_keys, (
        '_fit_result_phase.experiment_id and _fit_result_phase.structure_id '
        'must preserve the composite key'
    )
    for experiment in project.experiments:
        observed = observations[experiment.name]
        background = (
            np.asarray(experiment.data.intensity_bkg)
            if backgrounds is None
            else backgrounds[experiment.name]
        )
        # The denominator is the actual total calculated-minus-background input.
        # For scans reconstruct the selected template, preserving addition order.
        total = (
            np.asarray(experiment.data.intensity_calc) - background
            if backgrounds is None
            else ((background + parts[0]) + parts[1]) - background
        )
        share = np.divide(observed - background, total, out=np.zeros_like(total), where=total > 0)
        profiles = axial_profiles(np.asarray(experiment.data.two_theta))
        for name, reflections in zip(('phase', 'other'), profiles, strict=True):
            io = np.asarray([np.sum(profile * share) for profile in reflections])
            ic = np.asarray([np.sum(profile) for profile in reflections])
            assert np.all(io > 0), 'Every ring must retain positive observed intensity'
            assert np.all(ic > 0), 'Every ring must retain positive calculated intensity'
            bragg = np.abs(io - ic).sum() / np.abs(io).sum()
            amplitudes = np.sqrt(io / ic)
            amplitude = np.abs(amplitudes - 1).sum() / amplitudes.sum()
            row = next(
                row
                for row in rows
                if row['_fit_result_phase.experiment_id'] == experiment.name
                and row['_fit_result_phase.structure_id'] == name
            )
            assert float(row['_fit_result_phase.bragg_r_factor']) == pytest.approx(
                bragg, rel=1e-12
            ), '_fit_result_phase.bragg_r_factor must use its phase observations'
            assert float(row['_fit_result_phase.f_r_factor']) == pytest.approx(
                amplitude, rel=1e-12
            ), '_fit_result_phase.f_r_factor must use its phase amplitudes'


def retained_metrics(text, prefix, fields):
    rows = loop_rows(text, prefix)
    keyed = {}
    for row in rows:
        key = (row[prefix + '.experiment_id'], row.get(prefix + '.structure_id', ''))
        assert key not in keyed, 'Reload must not collapse or duplicate metric composite keys'
        assert all(prefix + '.' + field in row for field in fields), (
            'Every required metric field must remain present across the file boundary'
        )
        keyed[key] = [float(row[prefix + '.' + field]) for field in fields]
    return keyed


def assert_retained_metrics(text, copied):
    for prefix, fields in (
        ('_fit_result_phase', ('bragg_r_factor', 'f_r_factor')),
        (
            '_fit_result_bank',
            (
                'n_data_points',
                'prof_r_factor',
                'prof_wr_factor',
                'prof_wr_expected',
                'prof_cr_factor',
                'prof_cwr_factor',
                'chi_square',
            ),
        ),
    ):
        before = retained_metrics(text, prefix, fields)
        after = retained_metrics(copied, prefix, fields)
        assert set(after) == set(before), 'Reload must retain every metric composite identity'
        for key, values in before.items():
            assert after[key] == pytest.approx(values, rel=1e-12), (
                'Every metric value must survive reload independent of row ordering'
            )


@pytest.mark.parametrize('mode', ['single', 'joint', 'sequential', 'independent'])
def test_phase_and_profile_results_follow_reload_and_changed_free_set_refit(tmp_path, mode):
    project, parts, masks, grid, sigma, observations = phase_vehicle(tmp_path / 'input', mode)
    project.analysis.fit()
    text, _ = record(project, tmp_path / 'saved')
    declared = {
        name: np.column_stack((grid, observed, sigma * (1.7 if name == 'second' else 1)))
        for name, observed in observations.items()
    }
    backgrounds = None
    if mode in {'sequential', 'independent'}:
        backgrounds = {
            'bank': scan_template_background(
                project, tmp_path / 'saved', declared['bank'], constrained=False
            )
        }
    phase_checks(
        project,
        text,
        isolated_patterns(tmp_path / 'input', zero_background=True),
        observations,
        backgrounds,
    )
    profile_checks(
        project, text, declared, dict.fromkeys(observations, 2), backgrounds, sum(parts)
    )
    loaded = ENGINE.Project.load(tmp_path / 'saved')
    assert_retained_metrics(text, record(loaded, tmp_path / 'reopened')[0])
    if mode in {'sequential', 'independent'}:
        for ledger in (tmp_path / 'saved/analysis').glob('*.csv'):
            ledger.unlink()
    loaded = ENGINE.Project.load(tmp_path / 'saved')
    changed = {name: observed.copy() for name, observed in observations.items()}
    for observed in changed.values():
        observed[masks[0][0]] += 0.13 * parts[0][masks[0][0]]
        observed[masks[1][1]] += 0.17 * parts[1][masks[1][1]]
    for experiment in loaded.experiments:
        experiment.background_terms[0].coef.free = False
        experiment.data = ENGINE.PdCwlData(
            two_theta=grid,
            intensity_meas=changed[experiment.name],
            intensity_meas_su=declared[experiment.name][:, 2],
        )
    if mode in {'sequential', 'independent'}:
        folder = tmp_path / 'saved/experiments/scan'
        assert folder.is_dir(), 'Saving a scan must retain the declared independent data files'
        for index in range(3):
            observed = changed['bank'].copy()
            if index != 1:
                observed[masks[0][1]] += 0.19 * parts[0][masks[0][1]]
            (folder / f'{index}.dat').write_text('XYDATA\n' + data_text(grid, observed, sigma))
    loaded.analysis.fit()
    latest, _ = record(loaded, tmp_path / 'refitted')
    declared = {
        name: np.column_stack((grid, observed, declared[name][:, 2]))
        for name, observed in changed.items()
    }
    backgrounds = None
    if mode in {'sequential', 'independent'}:
        backgrounds = {
            'bank': scan_template_background(
                loaded, tmp_path / 'refitted', declared['bank'], constrained=False
            )
        }
    phase_checks(
        loaded,
        latest,
        isolated_patterns(tmp_path / 'input', zero_background=True),
        changed,
        backgrounds,
    )
    profile_checks(loaded, latest, declared, dict.fromkeys(changed, 1), backgrounds, sum(parts))
    assert loop_rows(latest, '_fit_result_phase') != loop_rows(text, '_fit_result_phase'), (
        'The new observations must replace the saved phase results as the latest fit'
    )


@pytest.mark.parametrize('case', doublet_phase.CASES)
@pytest.mark.parametrize('reverse', [False, True], ids=['increasing', 'decreasing'])
@pytest.mark.parametrize(
    ('entry', 'selection'),
    [
        ('direct', 'all'),
        ('direct', 'excluded'),
        ('direct', 'zero-sigma'),
        ('direct', 'negative-sigma'),
        ('analysis', 'all'),
        ('analysis', 'excluded'),
        ('analysis', 'zero-sigma'),
        ('analysis', 'negative-sigma'),
        ('joint-direct', 'all'),
        ('joint-direct', 'excluded'),
        ('joint-direct', 'zero-sigma'),
        ('joint-direct', 'negative-sigma'),
        ('joint-analysis', 'all'),
        ('joint-analysis', 'excluded'),
        ('joint-analysis', 'zero-sigma'),
        ('joint-analysis', 'negative-sigma'),
        ('sequential', 'all'),
        ('sequential', 'excluded'),
        ('independent', 'all'),
        ('independent', 'excluded'),
    ],
)
def test_doublet_phase_membership_and_orbit_share_survive_fit_and_reload(  # noqa: PLR0912, PLR0914, PLR0915
    tmp_path, case, reverse, selection, entry
):
    root = tmp_path / 'input'
    mode = (
        'joint'
        if entry.startswith('joint')
        else entry
        if entry in {'sequential', 'independent'}
        else 'single'
    )
    grid, positions, eligible = doublet_phase.write(root, case, reverse, mode)
    project = ENGINE.Project.load(root)
    project.analysis.calculate()
    calculated = np.asarray(project.experiments[0].data.intensity_calc).copy()
    if case in doublet_phase.BOUNDARY_CASES:
        assert np.all(calculated > 0), 'The boundary witness must paint a real positive tail'
        assert eligible == (case == 'shifted-centre'), (
            'Strict Bragg reachability must reject equality and beyond-limit lines, '
            'while the authored reachable shifted centre is inside the high-angle window'
        )
    multiplier = np.full_like(grid, 1.2)
    if case == 'both-unequal':
        multiplier[grid > sum(positions) / 2] = 0.8
    used = np.ones(len(grid), dtype=bool)
    if selection != 'all':
        used[::7] = False
        used[[0, -1]] = True
    sigma = np.ones_like(grid)
    if selection.endswith('sigma'):
        sigma[~used] = 0 if selection == 'zero-sigma' else -2
    observed = calculated * multiplier
    observed[~used] = 1e9
    for bank in project.experiments:
        path = root / f'experiments/{bank.name}.edi'
        header = (
            path.read_text().split('_data.intensity_meas_su\n', 1)[0] + '_data.intensity_meas_su\n'
        )
        text = header + doublet_phase.rows(grid, observed, sigma)
        if selection == 'excluded':
            text += 'loop_\n_excluded_region.id\n_excluded_region.start\n_excluded_region.end\n'
            text += ''.join(
                f'{i} {x - 1e-7:.17g} {x + 1e-7:.17g}\n'
                for i, x in enumerate(grid[~used], start=1)
            )
        path.write_text(text)
    if mode in {'sequential', 'independent'}:
        scan = root / 'experiments/scan'
        scan.mkdir(exist_ok=True)
        for index in range(3):
            scan_observed = observed if index == 1 else calculated * (0.9 if index == 0 else 1.4)
            (scan / f'{index}.dat').write_text(
                'XYDATA\n' + doublet_phase.rows(grid, scan_observed, sigma)
            )
    refusal = None
    try:
        project = ENGINE.Project.load(root)
        call = (
            project.fit
            if entry == 'direct'
            else project.fit_joint
            if entry == 'joint-direct'
            else project.analysis.fit
        )
        result = call()
    except ValueError as error:
        refusal = str(error)
    if refusal is not None:
        assert selection.endswith('sigma'), 'Positive-sigma doublet fits must reach phase quality'
        assert re.search(r'(?i)sigma|intensity_meas_su|uncertaint', refusal), (
            'Only an explicit invalid-sigma refusal may replace used-point quality evaluation'
        )
        return
    assert result is not None, 'Every admitted fit path must return its phase-quality record'
    saved = tmp_path / 'saved'
    project.save_as(saved)
    loaded = ENGINE.Project.load(saved)
    loaded.save_as(tmp_path / 'copied')
    expected = (0.0, 0.0)
    if eligible:
        share = 1.2
        if case == 'both-unequal':
            profiles = doublet_phase.component_weights(grid, positions)
            total = profiles[0] + profiles[1]
            share = np.sum(total[used] * multiplier[used]) / np.sum(total[used])
        expected = (abs(share - 1) / share, abs(math.sqrt(share) - 1) / math.sqrt(share))
    for destination in (saved, tmp_path / 'copied'):
        phase_rows = loop_rows(
            (destination / 'analysis/analysis.edi').read_text(), '_fit_result_phase'
        )
        expected_keys = {(bank.name, 'phase') for bank in project.experiments}
        assert {
            (row['_fit_result_phase.experiment_id'], row['_fit_result_phase.structure_id'])
            for row in phase_rows
        } == expected_keys, 'Doublet quality must retain every phase/bank key on disk'
        actual = [
            (
                float(row['_fit_result_phase.bragg_r_factor']),
                float(row['_fit_result_phase.f_r_factor']),
            )
            for row in phase_rows
        ]
        assert all(pair == pytest.approx(expected, rel=2e-11, abs=2e-13) for pair in actual), (
            'Phase Bragg and F factors must count either centred active line as one orbit, '
            'use only admitted rows, '
            'exclude outside tails and inactive lines, '
            'and preserve the closed-form shares on reload: '
            f'{actual} vs {expected}'
        )
