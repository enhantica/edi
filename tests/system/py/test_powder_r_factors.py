"""Weighted profile identities and the complete result-file lifecycle."""

import csv
import math
import re
from itertools import starmap
from pathlib import Path

import numpy as np
import pytest

from tests.fixtures.saved_spelling.profile_bounds import (
    assert_factor_rounding,
    factor_errors,
    polynomial_error,
    polynomial_values,
)
from tests.integration.py.test_anisotropic_adps import loop_rows
from tests.integration.py.test_e05_t1_fit_result import scalars
from tests.system.py.test_latest_fit_uncertainty import ENGINE, vehicle

PROFILE_FIELDS = (
    'prof_r_factor',
    'prof_wr_factor',
    'prof_wr_expected',
    'prof_cr_factor',
    'prof_cwr_factor',
)


def factors(observed, calculated, sigma, background, nfree):
    weight = 1 / sigma**2
    diff = observed - calculated
    chi = np.sum(weight * diff**2)
    norm = np.sum(weight * observed**2)
    corrected = observed - background
    return {
        'prof_r_factor': np.sum(np.abs(diff)) / np.sum(np.abs(observed)),
        'prof_wr_factor': math.sqrt(chi / norm),
        'prof_wr_expected': math.sqrt((len(observed) - nfree) / norm),
        'prof_cr_factor': np.sum(np.abs(diff)) / np.sum(np.abs(corrected)),
        'prof_cwr_factor': math.sqrt(chi / np.sum(weight * corrected**2)),
        'chi_square': chi,
    }


def record(project, root):
    project.save_as(root)
    text = (root / 'analysis/analysis.edi').read_text()
    return text, loop_rows(text, '_fit_result_bank')


def measured_rows(path):
    body = path.read_text().split('_data.intensity_meas_su\n', 1)[1]
    return np.asarray([
        list(map(float, line.split())) for line in body.splitlines() if line.strip()
    ])


def write_rows(path, rows):
    header = path.read_text().split('_data.intensity_meas_su\n', 1)[0]
    path.write_text(
        header
        + '_data.intensity_meas_su\n'
        + ''.join(' '.join(f'{value:.17g}' for value in row) + '\n' for row in rows)
    )


def weighted_vehicle(root, mode):
    vehicle(root, mode)
    declared = {}
    for index, path in enumerate(sorted((root / 'experiments').glob('*.edi'))):
        rows = measured_rows(path)
        rows[:, 2] = np.asarray([0.45, 1.8, 0.7, 2.4, 1.1, 0.55, 2.1, 0.9, 1.4])
        if index:
            rows = rows[:7].copy()
            rows[:, 1] = 1.9 * rows[:, 1] + np.asarray([0.1, -0.3, 0.2, 0.5, -0.1, 0.4, -0.2])
            rows[:, 2] *= 1.7
        write_rows(path, rows)
        declared[path.stem] = rows.copy()
    if mode in {'sequential', 'independent'}:
        # ADR-0035: persist the selected template, here the middle file.
        for index in range(3):
            path = root / 'experiments/scan' / f'{index}.dat'
            rows = declared['bank'].copy()
            rows[:, 1] += (index - 1) * np.asarray([
                0.3,
                -0.1,
                0.2,
                -0.4,
                0.1,
                -0.2,
                0.4,
                -0.3,
                0.2,
            ])
            path.write_text(
                'XYDATA\n'
                + ''.join(' '.join(f'{value:.17g}' for value in row) + '\n' for row in rows)
            )
        with (root / 'analysis/analysis.edi').open('a') as stream:
            stream.write('\n_sequential_fit.template_file 1.dat\n')
    return ENGINE.Project.load(root), declared


def assert_metrics(row, prefix, expected):
    for field, value in expected.items():
        assert prefix + field in row, (
            (
                'Each result must retain prof_cr_factor and prof_cwr_factor '
                'alongside every declared profile metric: '
            )
            + prefix
            + field
        )
        assert float(row[prefix + field]) == pytest.approx(value, rel=1e-12, abs=1e-14), (
            'Profile metrics including prof_cr_factor and prof_cwr_factor '
            'must use the independent inclusion mask and weighted sums: ' + prefix + field
        )


def scan_template_background(project, saved, inputs, *, constrained=True):
    # Fitted per-file parameters are inputs; the independent polynomial evaluates their pattern.
    # The caller's model can hold another file's parameters after the scan.
    with (saved / 'analysis/results.csv').open(newline='') as stream:
        rows = list(csv.DictReader(stream))
    selected = [row for row in rows if Path(row['file_path']).name == '1.dat']
    assert len(selected) == 1, 'The scan ledger must hold exactly one fitted middle-file template'
    experiment = project.experiments[0]
    values = []
    for ordinal in (1, 2):
        key = f'{experiment.name}.background.{ordinal}.coef'
        values.append(
            float(selected[0].get(key, experiment.background_terms[ordinal - 1].coef.value))
        )
    assert all(math.isfinite(value) for value in values), (
        'The template background input coefficients must be finite'
    )
    t = inputs[:, 0] / 40 - 1
    a, b = values
    # The scale-zero vehicle declares c = a - b; the phase vehicle fixes c = 0.
    return a + b * t + ((a - b) * t**2 if constrained else 0)


def saved_profile(saved, name):
    rows = loop_rows((saved / f'experiments/{name}.edi').read_text(), '_data')
    assert rows, 'Every fitted bank must save its own complete observation and calculation columns'
    return tuple(
        np.asarray([
            float(row['_data.' + field]) if row['_data.' + field] not in {'.', '?'} else np.nan
            for row in rows
        ])
        for field in ('intensity_meas', 'intensity_calc', 'intensity_meas_su', 'intensity_bkg')
    )


def assert_profile_rounding(project, saved, declared, *, constrained, used_by_bank=None):  # noqa: PLR0914
    loaded = ENGINE.Project.load(saved)
    loaded.analysis.calculate()
    for experiment in loaded.experiments:
        bank_constraint = constrained and experiment.name == 'bank'
        inputs = declared[experiment.name]
        used = inputs[:, 2] > 0 if used_by_bank is None else used_by_bank[experiment.name]
        yo, yc, sigma, background = [
            values[used] for values in saved_profile(saved, experiment.name)
        ]
        source = (saved / f'experiments/{experiment.name}.edi').read_text()
        coefficients = [row['_background.coef'] for row in loop_rows(source, '_background')]
        radius = polynomial_error(coefficients, inputs[:, 0], constrained=bank_constraint)[used]
        actual_yc = np.asarray(experiment.data.intensity_calc)[used]
        actual_bg = np.asarray(experiment.data.intensity_bkg)[used]
        np.testing.assert_allclose(
            actual_bg,
            polynomial_values(coefficients, inputs[:, 0], constrained=bank_constraint)[used],
            rtol=1e-12,
            atol=1e-14,
            err_msg='The reloaded background must equal the independent written-token polynomial',
        )
        np.testing.assert_allclose(
            actual_yc - actual_bg,
            yc - background,
            rtol=1e-12,
            atol=1e-14,
            err_msg='Background rounding must retain every fixed phase intensity',
        )
        assert np.all(abs(actual_yc - yc) <= radius + 1e-12), (
            'Recalculation must stay within the independently propagated background digits'
        )
        assert np.all(abs(actual_bg - background) <= radius + 1e-12), (
            'A reloaded background may move only by the authored polynomial rounding envelope'
        )
        nfree = len(project.free_parameters)
        expected = factors(yo, yc, sigma, background, nfree)
        actual = factors(yo, actual_yc, sigma, actual_bg, nfree)
        errors = factor_errors(yo, yc, sigma, background, radius, expected)
        assert_factor_rounding(actual, expected, errors)


def profile_checks(  # noqa: PLR0914
    project, text, declared, free_by_bank, backgrounds=None, net_pattern=None, *, saved=None
):
    rows = loop_rows(text, '_fit_result_bank')
    identities = [row['_fit_result_bank.experiment_id'] for row in rows]
    assert len(identities) == len(declared), (
        '_fit_result_bank must have exactly one row per _fit_result_bank.experiment_id'
    )
    assert set(identities) == set(declared), (
        '_fit_result_bank.experiment_id must retain every actual experiment key'
    )
    pooled = []
    bank_factors = []
    for experiment in project.experiments:
        inputs = declared[experiment.name]
        used = inputs[:, 2] > 0
        yo, sigma = inputs[used, 1], inputs[used, 2]
        if saved is not None and backgrounds is None:
            saved_yo, saved_yc, saved_sigma, saved_bg = saved_profile(saved, experiment.name)
            np.testing.assert_array_equal(
                saved_yo,
                inputs[:, 1],
                err_msg='Saved observations must retain every declared measured value',
            )
            np.testing.assert_array_equal(
                saved_sigma,
                inputs[:, 2],
                err_msg='Saved fit weights must retain every independently declared uncertainty',
            )
            yc, background = saved_yc[used], saved_bg[used]
            if backgrounds is not None:
                np.testing.assert_allclose(
                    background,
                    backgrounds[experiment.name][used],
                    rtol=1e-12,
                    atol=1e-14,
                    err_msg='The scan background must retain its independent ledger polynomial',
                )
            if net_pattern is not None:
                np.testing.assert_allclose(
                    yc - background,
                    net_pattern[used],
                    rtol=1e-12,
                    atol=1e-14,
                    err_msg='The net pattern must retain the independent phase contributions',
                )
        elif backgrounds is None:
            yc = np.asarray(experiment.data.intensity_calc)[used]
            background = np.asarray(experiment.data.intensity_bkg)[used]
        else:
            background = backgrounds[experiment.name][used]
            yc = background + (0 if net_pattern is None else net_pattern[used])
        assert np.all(np.isfinite(yc)), 'Every independently included point must be calculated'
        arrays = (yo, yc, sigma, background)
        expected = factors(*arrays, sum(free_by_bank.values()))
        if net_pattern is not None:
            unweighted = factors(
                yo, yc, np.ones(len(sigma)), background, sum(free_by_bank.values())
            )
            assert not math.isclose(
                expected['prof_cwr_factor'], unweighted['prof_cwr_factor'], rel_tol=1e-5
            ), 'Nonzero phase intensity and unequal sigma must distinguish weighted corrected Rwp'
        row = next(row for row in rows if row['_fit_result_bank.experiment_id'] == experiment.name)
        assert int(row['_fit_result_bank.n_data_points']) == int(used.sum()), (
            'Only independently included observations contribute degrees of freedom'
        )
        assert_metrics(row, '_fit_result_bank.', expected)
        pooled.append(arrays)
        bank_factors.append(expected)
    arrays = [np.concatenate([bank[index] for bank in pooled]) for index in range(4)]
    expected = factors(*arrays, sum(free_by_bank.values()))
    assert_metrics(
        scalars(text), '_fit_result.', {field: expected[field] for field in PROFILE_FIELDS}
    )
    return bank_factors, expected


@pytest.mark.parametrize('mode', ['single', 'joint', 'multiphase', 'sequential', 'independent'])
def test_every_fit_records_per_experiment_profile_factors_from_used_points(tmp_path, mode):
    project, declared = weighted_vehicle(tmp_path / 'input', mode)
    project.analysis.fit()
    text, _ = record(project, tmp_path / 'saved')
    backgrounds = None
    if mode in {'sequential', 'independent'}:
        backgrounds = {
            'bank': scan_template_background(project, tmp_path / 'saved', declared['bank'])
        }
    banks, pooled = profile_checks(
        project, text, declared, dict.fromkeys(declared, 2), backgrounds, saved=tmp_path / 'saved'
    )
    if mode not in {'sequential', 'independent'}:
        assert_profile_rounding(project, tmp_path / 'saved', declared, constrained=True)
    for experiment in project.experiments:
        inputs = declared[experiment.name]
        if backgrounds is None:
            _yo, yc, _sigma, background = saved_profile(tmp_path / 'saved', experiment.name)
        else:
            background = backgrounds[experiment.name]
            yc = background
        unweighted = factors(inputs[:, 1], yc, np.ones(len(yc)), background, 2)
        weighted = factors(inputs[:, 1], yc, inputs[:, 2], background, 2)
        # Zero phase scales give yc == background, hence cRp == cRwp == 1 for any weights.
        assert weighted['prof_cwr_factor'] == pytest.approx(1.0, abs=1e-12), (
            '_fit_result_bank.prof_cwr_factor must be 1 (100%) for this scale-zero fixture'
        )
        assert weighted['prof_cr_factor'] == pytest.approx(1.0, abs=1e-12), (
            '_fit_result_bank.prof_cr_factor must be 1 (100%) for this scale-zero fixture'
        )
        assert not math.isclose(
            unweighted['prof_wr_factor'], weighted['prof_wr_factor'], rel_tol=1e-5
        ), 'Unequal uncertainties must distinguish weighted from unweighted Rwp'
    if mode == 'joint':
        average = np.mean([bank['prof_wr_factor'] for bank in banks])
        assert not math.isclose(pooled['prof_wr_factor'], average, rel_tol=1e-5), (
            'Unequal banks must distinguish pooled sums from an average of bank ratios'
        )


@pytest.mark.parametrize('mutation', ['excluded-outlier', 'zero-sigma'])
def test_excluded_or_zero_weight_outlier_cannot_enter_any_metric_sum(tmp_path, mutation):
    root = tmp_path / 'input'
    _, declared = weighted_vehicle(root, 'single')
    rows = declared['bank'].copy()
    rows[0, 1] = 1e9
    if mutation == 'zero-sigma':
        rows[0, 2] = 0
    path = root / 'experiments/bank.edi'
    write_rows(path, rows)
    if mutation == 'excluded-outlier':
        with path.open('a') as stream:
            stream.write(
                '\nloop_\n_excluded_region.id\n_excluded_region.start\n'
                '_excluded_region.end\n1 39 41\n'
            )
    refusal = None
    try:
        project = ENGINE.Project.load(root)
        project.analysis.fit()
    except ValueError as error:
        refusal = str(error)
    if refusal is not None:
        assert mutation == 'zero-sigma', 'A valid excluded positive-weight outlier must fit'
        assert re.search(r'(?i)sigma|intensity_meas_su|uncertaint', refusal), (
            'Only an explicit invalid-sigma refusal may replace zero-weight metric evaluation'
        )
        return
    text, bank_rows = record(project, tmp_path / 'saved')
    assert len(bank_rows) == 1, 'The mutated single fit must retain its bank result'
    assert int(bank_rows[0]['_fit_result_bank.n_data_points']) == 8, (
        'The excluded or zero-weight outlier must contribute no degree of freedom'
    )
    yo, yc, sigma, background = saved_profile(tmp_path / 'saved', 'bank')
    np.testing.assert_array_equal(
        yo, rows[:, 1], err_msg='Excluded observations must retain their original measured values'
    )
    np.testing.assert_array_equal(
        sigma, rows[:, 2], err_msg='Excluded observations must retain their original weights'
    )
    expected = factors(yo[1:], yc[1:], sigma[1:], background[1:], 2)
    assert_profile_rounding(
        project,
        tmp_path / 'saved',
        {'bank': rows},
        constrained=True,
        used_by_bank={'bank': np.arange(len(rows)) > 0},
    )
    assert_metrics(bank_rows[0], '_fit_result_bank.', expected)
    assert_metrics(
        scalars(text), '_fit_result.', {field: expected[field] for field in PROFILE_FIELDS}
    )


def planted_metrics(root, extended):
    project = vehicle(root, 'joint')
    project.save_as(root.parent / 'planted')
    path = root.parent / 'planted/analysis/analysis.edi'
    text = path.read_text()
    text = re.sub(r'(?m)^_fit_result\..*\n', '', text)
    text = re.sub(r'(?ms)^loop_\n_fit_result_(?:bank|phase)\..*?(?=^loop_|\Z)', '', text)
    text += '\n_fit_result.result_kind deterministic\n_fit_result.success true\n'
    text += '_fit_result.prof_wr_factor 0.23456789123\n_fit_result.reduced_chi_square 3.56\n'
    values = {
        'prof_r_factor': 0.123456789123,
        'prof_wr_expected': 0.098765432123,
        'prof_cr_factor': 0.246813579123,
        'prof_cwr_factor': 0.357924681123,
    }
    if extended:
        text += ''.join(f'_fit_result.{key} {value:.17g}\n' for key, value in values.items())
    fields = ['experiment_id', 'n_data_points', 'prof_wr_factor', 'chi_square']
    if extended:
        fields += list(values)
    banks = []
    phases = []
    for index, name in enumerate(('bank', 'other')):
        row = {
            'experiment_id': name,
            'n_data_points': '9',
            'prof_wr_factor': str(0.16 + index * 0.13),
            'chi_square': str(1.8 + index * 2.3),
        }
        if extended:
            row.update({key: f'{value + index * 0.041:.17g}' for key, value in values.items()})
        banks.append({'_fit_result_bank.' + key: str(value) for key, value in row.items()})
        phases.append({
            '_fit_result_phase.experiment_id': name,
            '_fit_result_phase.structure_id': 'phase',
            '_fit_result_phase.bragg_r_factor': f'{0.07123456789 + index * 0.081:.17g}',
            '_fit_result_phase.f_r_factor': f'{0.03234567891 + index * 0.091:.17g}',
        })
    text += 'loop_\n' + ''.join('_fit_result_bank.' + field + '\n' for field in fields)
    text += ''.join(
        ' '.join(row['_fit_result_bank.' + field] for field in fields) + '\n' for row in banks
    )
    if extended:
        text += 'loop_\n' + '\n'.join(phases[0]) + '\n'
        text += ''.join(' '.join(row.values()) + '\n' for row in phases)
    path.write_text(text)
    return root.parent / 'planted', values, banks, phases


@pytest.mark.parametrize('extended', [True, False])
def test_powder_metrics_survive_two_saves_and_actual_legacy_files_load(tmp_path, extended):
    current, values, banks, phases = planted_metrics(tmp_path / 'input', extended)
    source = (current / 'analysis/analysis.edi').read_text()
    if not extended:
        assert '_fit_result.prof_r_factor' not in source, (
            'The legacy input must omit extension scalars'
        )
        assert '_fit_result_bank.prof_r_factor' not in source, (
            'The legacy bank loop must omit new columns'
        )
        assert '_fit_result_phase.' not in source, (
            'The legacy input must omit the phase-result loop'
        )
    for generation in range(2):
        loaded = ENGINE.Project.load(current)
        target = tmp_path / f'roundtrip-{generation}'
        loaded.save_as(target)
        output = (target / 'analysis/analysis.edi').read_text()
        actual_banks = loop_rows(output, '_fit_result_bank')
        keyed = {row['_fit_result_bank.experiment_id']: row for row in actual_banks}
        assert len(actual_banks) == len(banks), (
            'Repeated saves must preserve bank cardinality without duplicates'
        )
        assert set(keyed) == {'bank', 'other'}, (
            'Repeated saves must preserve the distinct experiment identities'
        )
        for expected in banks:
            actual = keyed[expected['_fit_result_bank.experiment_id']]
            assert set(expected) <= set(actual), 'Every bank extension field must survive loading'
            for field, value in expected.items():
                if field.endswith('experiment_id'):
                    assert actual[field] == value, (
                        'A bank result must retain its owning experiment key'
                    )
                else:
                    assert float(actual[field]) == pytest.approx(float(value), rel=1e-12), (
                        'Every old and new bank value must survive two read/write boundaries'
                    )
        if extended:
            actual = scalars(output)
            assert all('_fit_result.' + field in actual for field in values), (
                'Every pooled extension field must survive loading'
            )
            for field, value in values.items():
                assert float(actual['_fit_result.' + field]) == pytest.approx(value, rel=1e-12), (
                    'Every extended scalar must survive repeated read/write boundaries'
                )
            actual_phases = loop_rows(output, '_fit_result_phase')
            keys = [
                (row['_fit_result_phase.experiment_id'], row['_fit_result_phase.structure_id'])
                for row in actual_phases
            ]
            assert len(keys) == len(set(keys)) == 2, (
                'Phase results must preserve both composite identities'
            )
            for expected in phases:
                row = next(
                    row
                    for row in actual_phases
                    if row['_fit_result_phase.experiment_id']
                    == expected['_fit_result_phase.experiment_id']
                )
                assert row['_fit_result_phase.structure_id'] == 'phase', (
                    'The repeated phase must retain its structure key'
                )
                for field in ('bragg_r_factor', 'f_r_factor'):
                    key = '_fit_result_phase.' + field
                    assert float(row[key]) == pytest.approx(float(expected[key]), rel=1e-12), (
                        'Each bank-specific phase value must survive repeated read/write '
                        'boundaries'
                    )
        assert len(loaded.free_parameters) == 4, (
            'Legacy and extended records must preserve the joint model free set'
        )
        current = target


@pytest.mark.parametrize(
    'escape',
    [
        'unweighted',
        'unweighted-corrected',
        'averaged-pool',
        'excluded-outlier',
        'retained-zero-sigma',
    ],
)
def test_the_profile_oracle_rejects_each_exercised_numeric_escape(escape):
    left = tuple(
        np.asarray(values, dtype=float)
        for values in (
            [10, 12, 14, 16, 18, 20],
            [9, 12.5, 13, 17, 16, 21],
            [0.5, 1.5, 0.8, 2, 1, 2.5],
            [3, 3.2, 3.4, 3.6, 3.8, 4],
        )
    )
    expected = factors(*left, 2)
    actual = dict(expected)
    if escape in {'unweighted', 'unweighted-corrected'}:
        wrong = factors(left[0], left[1], np.ones(len(left[0])), left[3], 2)
        field = 'prof_cwr_factor' if escape == 'unweighted-corrected' else 'prof_wr_factor'
        actual[field] = wrong[field]
    elif escape == 'averaged-pool':
        right = tuple(
            np.asarray(values, dtype=float)
            for values in (
                [20, 35, 26, 38, 32, 45, 36],
                [21, 33, 27, 35, 35, 44, 37],
                [1.2, 0.6, 2, 1.7, 0.8, 1.3, 0.9],
                [10, 10, 10, 10, 10, 10, 10],
            )
        )
        expected = factors(*[np.concatenate((a, b)) for a, b in zip(left, right, strict=True)], 4)
        actual = dict(expected)
        actual['prof_wr_factor'] = (
            factors(*left, 2)['prof_wr_factor'] + factors(*right, 2)['prof_wr_factor']
        ) / 2
    elif escape == 'excluded-outlier':
        actual = factors(
            *list(starmap(np.append, zip(left, (1000000000.0, 20, 1, 4), strict=True))),
            2,
        )
    else:
        expected = factors(*[values[1:] for values in left], 2)
        actual = factors(*left, 2)
    row = {'_fit_result_bank.' + key: str(value) for key, value in actual.items()}
    with pytest.raises(AssertionError, match='independent inclusion mask and weighted sums'):
        assert_metrics(row, '_fit_result_bank.', expected)
    errors = factor_errors(*left, np.full_like(left[0], 0.005), factors(*left, 2))
    expected = factors(*left, 2)
    assert_factor_rounding(expected, expected, errors)
    for field in expected:
        beyond = dict(expected)
        beyond[field] += errors[field] + 2e-12
        with pytest.raises(AssertionError, match='independent triangle-inequality rounding bound'):
            assert_factor_rounding(beyond, expected, errors)
