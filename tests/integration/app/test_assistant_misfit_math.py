"""Independent scalar references for the actual native powder summary."""

import copy
import json
import os
import subprocess
from operator import itemgetter
from pathlib import Path

import pytest

from tests.integration.py.assistant_misfit_reference import peak, population, synthetic, weighted

ROOT = Path(__file__).resolve().parents[3]


def actual(data):
    binary = Path(
        os.environ.get(
            'EDI_MISFIT_PROBE', ROOT / 'build/app/assistant-ui-probe/assistant_misfit_probe'
        )
    )
    result = subprocess.run(
        [str(binary)], input=json.dumps(data) + '\n', capture_output=True, text=True, check=True
    )
    return json.loads(result.stdout)


def close(actual_value, expected, requirement):
    assert actual_value == pytest.approx(expected, rel=2e-11, abs=2e-11), (
        f'Independent scalar summary follows the original arrays: {requirement}'
    )


def test_weighted_regions_and_background_use_the_same_array_population():
    data, _ = synthetic()
    data['excluded'] = [[data['x'][20], data['x'][22]]]
    result = actual(data)
    used = population(data)
    assert result['dataset_id'] == data['dataset_id'] and result['points'] == len(used), (
        'The summary names its dataset and counts the finite included positive-sigma population'
    )
    close(
        result['weighted_rms'],
        weighted(data, used)[1],
        'Overall weighted RMS follows the closed-form residual sum',
    )
    covered = []
    assert len(result['regions']) == 8, (
        'The powder summary partitions its usable data into eight regions'
    )
    for region in result['regions']:
        indices = [i for i in used if region['x_from'] <= data['x'][i] <= region['x_to']]
        assert region['points'] == len(indices) and indices, (
            'Each region counts its actual included source rows'
        )
        mean, rms = weighted(data, indices)
        close(
            region['weighted_mean'],
            mean,
            'Region signed mean uses the original residual and sigma values',
        )
        close(
            region['weighted_rms'],
            rms,
            'Region RMS uses the original squared weighted residual values',
        )
        covered += indices
    assert covered == used, (
        'The ordered regions cover every usable row exactly once without overlap'
    )
    quiet = [
        i for i in used if data['calculated'][i] - data['background'][i] < data['sigma'][i] / 2
    ]
    assert result['background']['quiet_points'] == len(quiet), (
        'Quiet background samples have calculated peak height below half sigma'
    )
    mean, rms = weighted(data, quiet, 'background')
    close(
        result['background']['weighted_mean'],
        mean,
        'Background bias uses measured minus background over the original sigma',
    )
    close(
        result['background']['weighted_rms'],
        rms,
        'Background RMS uses the closed-form quiet-region weighted square sum',
    )


def test_five_worst_reflections_preserve_ratios_shifts_and_widths():
    data, windows = synthetic()
    result = actual(data)
    expected = sorted(
        (peak(data, *window) for window in windows),
        key=itemgetter('weighted_square_sum'),
        reverse=True,
    )[:5]
    assert len(result['worst_peaks']) == 5, (
        'Exactly the five worst distinct authored reflection supports are reported'
    )
    for observed, reference in zip(result['worst_peaks'], expected, strict=True):
        assert observed['phase_id'] == reference['phase_id'], (
            'A reflection retains its actual phase identity after ranking'
        )
        for field in (
            'position',
            'weighted_square_sum',
            'intensity_ratio',
            'centroid_shift',
            'width_ratio',
        ):
            close(
                observed[field],
                reference[field],
                f'Reflection {field} follows independent weighted sums and spatial moments',
            )


def test_invalid_supplied_sigma_is_omitted_instead_of_inventing_weights():
    data, _ = synthetic()
    data = copy.deepcopy(data)
    data['sigma'][9:12] = [0, -1, None]
    result = actual(data)
    used = population(data)
    assert result['points'] == len(used), (
        'Nonpositive and nonfinite supplied sigmas cannot be replaced by invented Poisson weights'
    )
    close(
        result['weighted_rms'],
        weighted(data, used)[1],
        'Weighted residual statistics use only the original usable supplied sigmas',
    )


def test_quiet_background_excludes_the_half_sigma_boundary():
    data = {
        'dataset_id': 'threshold',
        'x': [1, 2, 3],
        'measured': [12, 14, 19],
        'calculated': [10, 11, 13],
        'background': [10, 10, 10],
        'sigma': [2, 2, 2],
        'phases': [],
    }
    result = actual(data)
    assert result['background']['quiet_points'] == 1, (
        'Under half sigma is strict; a calculated peak exactly at half sigma is excluded'
    )
    close(
        result['background']['weighted_mean'],
        1,
        'The strict quiet population contains only its independently known '
        'weighted background residual',
    )


def authored_peak():
    return {
        'dataset_id': 'isolated-peak',
        'axis_kind': 'data.twotheta',
        'current': True,
        'x': [10, 11, 12, 13, 14, 15, 16],
        'background': [10] * 7,
        'measured': [10, 13, 15, 17, 18, 13, 10],
        'calculated': [10, 13, 15, 20, 15, 13, 10],
        'sigma': [2] * 7,
        'phases': [{'phase_id': 'alpha', 'positions': [13]}],
    }


def test_peak_below_background_has_no_measured_direction():
    data = authored_peak()
    data['measured'] = [9, 10, 9, 10, 9, 10, 9]
    expected = peak(data, [1, 2, 3, 4, 5], 13, 'alpha')
    assert 'centroid_shift' not in expected, (
        'The independently authored observations have no positive net intensity'
    )
    for reported in actual(data).get('worst_peaks', []):
        assert reported.get('centroid_shift') is None and reported.get('width_ratio') is None, (
            'A calculated peak with no observed centroid cannot publish measured zero direction'
        )


def test_peak_support_cannot_cross_or_center_in_a_mask():
    data = authored_peak()
    data['excluded'] = [[12, 12]]
    expected = peak(data, [3, 4, 5], 13, 'alpha')
    for reported in actual(data).get('worst_peaks', []):
        if reported.get('centroid_shift') is not None:
            close(reported['centroid_shift'], expected['centroid_shift'], 'mask splits support')
        if reported.get('weighted_square_sum') is not None:
            close(
                reported['weighted_square_sum'],
                expected['weighted_square_sum'],
                'points beyond the mask are outside this peak support',
            )

    data['excluded'] = [[13, 13]]
    for reported in actual(data).get('worst_peaks', []):
        assert reported.get('centroid_shift') is None, (
            'A reflection centered in an excluded interval has no observed direction'
        )


def test_coincident_phases_do_not_inherit_one_phases_peak_direction():
    data = authored_peak()
    data['phases'].append({'phase_id': 'beta', 'positions': [13]})
    for reported in actual(data).get('worst_peaks', []):
        if reported.get('centroid_shift') is not None:
            assert reported.get('phase_id') not in {'alpha', 'beta'}, (
                'A shared observed support cannot identify one coincident phase as its owner'
            )
            expected = peak(data, [1, 2, 3, 4, 5], 13, 'combined')
            close(
                reported['centroid_shift'], expected['centroid_shift'], 'combined support moment'
            )

    data['excluded'] = [[10, 16]]
    result = actual(data)
    assert result.get('points', 0) == 0 and not result.get('worst_peaks'), (
        'A fully masked pattern has no usable points or directional peak diagnostics'
    )
