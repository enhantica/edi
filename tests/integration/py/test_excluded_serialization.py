"""Excluded-row serialization uses CIF missing values and physical axis conversions."""

import json
import math
import shlex
import shutil
from pathlib import Path

import edi as library
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / 'tests/fixtures/excluded_display'


def data_loop(text):
    items = shlex.split(text, comments=True)
    for i, item in enumerate(items):
        if item != 'loop_' or i + 1 >= len(items) or not items[i + 1].startswith('_data.'):
            continue
        j = i + 1
        columns = []
        while j < len(items) and items[j].startswith('_'):
            columns.append(items[j])
            j += 1
        values = []
        while j < len(items) and not items[j].startswith(('_', 'loop_', 'data_')):
            values.append(items[j])
            j += 1
        assert len(values) % len(columns) == 0, 'Saved data loops must be rectangular CIF tables'
        return columns, [
            dict(zip(columns, values[k : k + len(columns)], strict=True))
            for k in range(0, len(values), len(columns))
        ]
    raise AssertionError('A saved measured experiment must retain its data loop')


def calculated(tmp_path, kind):
    project = library.Project.load(FIXTURES / kind)
    project.analysis.calculate()
    destination = tmp_path / 'saved'
    project.save_as(destination)
    return project, destination


def canonical_saved_rows(root, oracle, *, old_column=None):
    path = root / 'experiments/pattern.edi'
    text = path.read_text()
    columns, rows = data_loop(text)
    for index, row in enumerate(rows):
        if not oracle['included'][index]:
            row['_data.d_spacing'] = format(oracle['d'][index], '.12g')
            for column in ('intensity_calc', 'intensity_bkg'):
                row['_data.' + column] = '.'
            if old_column:
                row['_data.' + old_column] = '0.'
    prefix = text.split('loop_\n' + columns[0], 1)[0]
    # Other loops remain byte-for-byte input; replace only this data loop.
    old = 'loop_\n' + '\n'.join(columns) + '\n'
    start = text.index(old) + len(old)
    tail = text[start:]
    next_loop = tail.find('\nloop_')
    suffix = '' if next_loop < 0 else tail[next_loop:]
    body = ''.join(' '.join(row[column] for column in columns) + '\n' for row in rows)
    path.write_text(prefix + old + body + suffix)


def check_excluded_reflection_tail(tmp_path):
    centre = math.degrees(2 * math.asin(1.54 / (2 * 4))) + 0.29
    positions = [centre - 0.04, centre, centre + 0.04]
    region = (centre - 0.01, centre + 0.01)
    assert region[0] < centre < region[1] < positions[-1], (
        'The closed-form cubic 100 peak is just inside the exclusion beside an included point'
    )
    source = (FIXTURES / 'cw/experiments/pattern.edi').read_text()
    prefix, rest = source.split('loop_\n_excluded_region.id', 1)
    _, data = rest.split('loop_\n_data.two_theta', 1)
    headers = data.split('_data.intensity_meas_su\n', 1)[0]
    rows = ''.join(f'{x:.15g} 100 2\n' for x in positions)
    curves = {}
    for name, scale, excluded in (
        ('full', 1, False),
        ('excluded', 1, True),
        ('background', 0, True),
    ):
        folder = tmp_path / name
        shutil.copytree(FIXTURES / 'cw', folder)
        exclusion = (
            'loop_\n_excluded_region.id\n_excluded_region.start\n_excluded_region.end\n'
            f'1 {region[0]:.15g} {region[1]:.15g}\n'
            if excluded
            else ''
        )
        text = prefix.replace('phase 1\n', f'phase {scale}\n') + exclusion
        text += 'loop_\n_data.two_theta' + headers + '_data.intensity_meas_su\n' + rows
        (folder / 'experiments/pattern.edi').write_text(text)
        project = library.Project.load(folder)
        project.analysis.calculate()
        curves[name] = np.asarray(project.experiment.data.intensity_calc).copy()
    assert np.isfinite(curves['full']).all(), (
        'The control calculates the Bragg peak at every observation before exclusion'
    )
    assert np.isnan(curves['excluded'][1]), (
        'The excluded peak centre has no calculated display value'
    )
    assert curves['full'][1] > max(curves['full'][0], curves['full'][2]), (
        'The Bragg-law centre is a real peak above its adjacent included tails'
    )
    for side in (0, 2):
        assert curves['excluded'][side] > curves['background'][side] + 1, (
            'A reflection centred inside an exclusion still raises calc above '
            'background outside it'
        )
        assert curves['excluded'][side] == pytest.approx(curves['full'][side], rel=1e-12), (
            'Excluding a peak centre preserves its whole contribution at '
            'neighbouring included points'
        )


@pytest.mark.parametrize('kind', ['cw', 'tof'])
def test_excluded_writer_keeps_real_d_and_absent_derived_values(tmp_path, kind):
    if kind == 'cw':
        check_excluded_reflection_tail(tmp_path)
    oracle = json.loads((FIXTURES / f'{kind}.json').read_text())
    project, saved = calculated(tmp_path, kind)
    _, rows = data_loop((saved / 'experiments/pattern.edi').read_text())
    assert len(rows) == len(oracle['x']), (
        'Saving must retain every included and excluded observation'
    )
    for i, row in enumerate(rows):
        assert row['_data.calc_status'] == ('incl' if oracle['included'][i] else 'excl'), (
            'Excluded membership follows the independent closed region bounds'
        )
        assert row['_data.d_spacing'] not in {'.', '?'}, (
            'd-spacing is a unit conversion defined at every physical '
            'observation, including exclusions'
        )
        assert float(row['_data.d_spacing']) == pytest.approx(oracle['d'][i], rel=2e-7), (
            'Saved d-spacing follows Bragg inversion or the nonzero quadratic TOF calibration'
        )
        if not oracle['included'][i]:
            for key in ('intensity_calc', 'intensity_bkg'):
                assert row['_data.' + key] == '.', (
                    'Excluded derived cells use CIF inapplicable dots rather than numeric zeros'
                )
        else:
            assert all(
                math.isfinite(float(row['_data.' + key]))
                for key in ('intensity_calc', 'intensity_bkg')
            ), (
                'Included calculations must remain real values instead of being '
                'dropped with exclusions'
            )
    excluded = np.logical_not(oracle['included'])
    assert np.isnan(np.asarray(project.experiment.data.intensity_calc)[excluded]).all(), (
        'Excluded calculated intensities are absent NaNs in memory'
    )
    assert np.isnan(np.asarray(project.experiment.data.intensity_bkg)[excluded]).all(), (
        'Excluded background intensities are absent NaNs in memory'
    )
    difference = np.asarray(project.experiment.data.intensity_meas) - np.asarray(
        project.experiment.data.intensity_calc
    )
    assert np.isnan(difference[excluded]).all(), (
        'Excluded observed-minus-calculated values remain absent rather than becoming zeros'
    )
    assert np.asarray(project.experiment.data.d_spacing) == pytest.approx(
        oracle['d'], rel=2e-12
    ), 'The in-memory d column is defined over the full measured grid'


@pytest.mark.parametrize('kind', ['cw', 'tof'])
def test_modern_excluded_rows_load_and_round_trip(tmp_path, kind):
    oracle = json.loads((FIXTURES / f'{kind}.json').read_text())
    _, saved = calculated(tmp_path, kind)
    canonical_saved_rows(saved, oracle)
    restored = library.Project.load(saved)
    assert np.asarray(restored.experiment.data.axis()) == pytest.approx(oracle['x']), (
        'Loading modern excluded rows preserves the whole measured grid'
    )
    restored.analysis.calculate()
    again = tmp_path / 'again'
    restored.save_as(again)
    _, rows = data_loop((again / 'experiments/pattern.edi').read_text())
    for i, row in enumerate(rows):
        if not oracle['included'][i]:
            assert row['_data.intensity_calc'] == row['_data.intensity_bkg'] == '.', (
                'Save after loading must preserve the inapplicable excluded intensity convention'
            )
            assert row['_data.d_spacing'] not in {'.', '?'}, (
                'Round-tripping an excluded row must retain its physical d-spacing'
            )


@pytest.mark.parametrize('kind', ['cw', 'tof'])
@pytest.mark.parametrize('column', ['d_spacing', 'intensity_calc', 'intensity_bkg'])
def test_old_zero_on_an_excluded_row_is_refused(tmp_path, kind, column):
    oracle = json.loads((FIXTURES / f'{kind}.json').read_text())
    _, saved = calculated(tmp_path, kind)
    canonical_saved_rows(saved, oracle, old_column=column)
    with pytest.raises(
        ValueError, match=r'(?i)(excl|inapplicable|excluded).*(zero|0|dot|\.)|(zero|0).*excl'
    ):
        library.Project.load(saved)
