"""The magnetic worked examples retain their declared execution and fit records."""

import csv
import json
from pathlib import Path

import edi
import numpy as np
import pytest
import yaml

from tests.fixtures.magnetic_pnma import reference

ROOT = Path(__file__).resolve().parents[3]
CLI = ROOT / 'docs/user/cli'


@pytest.mark.parametrize(
    ('name', 'execution'),
    [
        ('pd-neut-cwl_cosio-d20_2k', 'executing'),
        ('pd-neut-cwl_cosio-d20_scan-213f', 'offline'),
    ],
)
def test_magnetic_examples_have_records_and_documentation(name, execution):
    directory = CLI / name
    assert directory.is_dir(), 'Both promised magnetic cobalt examples must be delivered'
    registry = yaml.safe_load((CLI / 'projects.yml').read_text())['projects']
    rows = [row for row in registry if row.get('id') == name]
    assert len(rows) == 1, 'Every magnetic example has exactly one registered identity'
    assert any((directory / name).is_file() for name in ['README.md', 'index.md']), (
        'Each magnetic example explains its inputs and scope'
    )
    assert (directory / 'expected.json').is_file(), (
        'Each magnetic fit carries its recorded outcomes'
    )
    record = json.loads((directory / 'expected.json').read_text())
    assert record.get('source'), 'Magnetic fit records name the calculation that produced them'
    quantities = record.get('quantities', {})
    assert quantities, 'Magnetic examples carry nonempty fit-result records'
    assert any(value.get('kind') == 'regression-pin' for value in quantities.values()), (
        'Fit outcomes must distinguish regression pins from independent correctness references'
    )
    if execution == 'offline':
        assert rows[0].get('offline') is True, (
            'The extended temperature scan explicitly records its offline execution status'
        )
    else:
        assert rows[0].get('executing') is True and not rows[0].get('offline', False), (
            'The single low-temperature magnetic fit belongs to the executing example set'
        )


def test_low_temperature_fit_record_has_independent_moment_sanity_bounds():
    # Packet gate 10: these are broad physical sanity bounds, never powder-moment correctness pins.
    path = CLI / 'pd-neut-cwl_cosio-d20_2k/expected.json'
    assert path.is_file(), 'The low-temperature fit delivers a machine result record'
    record = json.loads(path.read_text())
    assert 'crysta' in record['source']['engine'].lower(), (
        'The example records its actual engine fit rather than relabelling FullProf results'
    )
    quantities = record['quantities']
    components = []
    for axis in 'xyz':
        value = quantities[f'param.Co1.crystalaxis_{axis}.value']
        assert value['kind'] == 'regression-pin', (
            'Powder moment fit outputs are regression pins, not independent correctness references'
        )
        components.append(float(value['value']))
    magnitude = sum(value * value for value in components) ** 0.5
    assert 2.68 <= magnitude <= 3.87, (
        'Co1 magnitude lies between the declared report minimum and single-crystal value'
    )
    second = quantities['param.Co2.crystalaxis_y.value']
    assert second['kind'] == 'regression-pin', 'The fitted Co2 component is a regression pin'
    assert 2.620 <= float(second['value']) <= 3.35, (
        'The fitted Co2 moment lies within the packet declared physical sanity interval'
    )


def test_extended_magnetic_scan_records_every_temperature_in_ascending_order():
    directory = CLI / 'pd-neut-cwl_cosio-d20_scan-213f'
    path = directory / 'project/analysis/results.csv'
    assert path.is_file(), 'The offline magnetic scan retains its per-file fit result record'
    with path.open(newline='') as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 213, 'The extended magnetic scan records every declared data file'
    assert len({row['file_path'] for row in rows}) == 213, 'No fitted scan file is repeated'
    temperatures = [float(row['diffrn.ambient_temperature']) for row in rows]
    assert temperatures == sorted(temperatures), (
        'Sequential fitting starts at the lowest temperature'
    )
    assert temperatures[0] < 3, (
        'The magnetic scan includes the independently recorded low-temperature data'
    )
    assert all(int(row['fit_result.iterations']) >= 0 for row in rows), (
        'Every scan row records its fit iteration count'
    )
    columns = []
    for axis in 'xyz':
        matching = [key for key in rows[0] if key.endswith('Co1.crystalaxis_' + axis)]
        assert len(matching) == 1, 'Every free Co1 component has one recorded result column'
        columns.append(matching[0])
    moments = [sum(float(row[key]) ** 2 for key in columns) ** 0.5 for row in rows]
    cold = [m for t, m in zip(temperatures, moments, strict=True) if t < 10]
    warm = [m for t, m in zip(temperatures, moments, strict=True) if 50 <= t <= 60]
    assert cold and warm, (
        'The scan samples both the ordered state and temperatures around the reported transition'
    )
    assert sum(warm) / len(warm) < sum(cold) / len(cold), (
        'The fitted ordered moment falls towards zero near the reported Neel temperature'
    )


@pytest.mark.parametrize('name', ['pd-neut-cwl_cosio-d20_2k', 'pd-neut-cwl_cosio-d20_scan-213f'])
def test_magnetic_examples_share_cobalt_displacements_and_exclude_only_dead_cell(name, tmp_path):
    directory = CLI / name / 'project'
    assert directory.is_dir(), 'Each magnetic example delivers a loadable native project'
    model = edi.Project.load(directory)
    model.analysis.calculate()
    structure = model.structure
    structure.atom_sites['Co1'].adp_iso.value = 0.42
    model.analysis.calculate()
    assert structure.atom_sites['Co2'].adp_iso.value == pytest.approx(0.42), (
        'The magnetic examples tie both cobalt displacement parameters to one shared value'
    )
    moments = structure.atom_site_moment
    independent = [('Co1', 'x'), ('Co1', 'y'), ('Co1', 'z'), ('Co2', 'y')]
    assert all(getattr(moments[site], 'crystalaxis_' + axis).free for site, axis in independent), (
        'The magnetic examples free all four symmetry-independent moment components'
    )
    grid = np.asarray(model.experiment.data.two_theta)
    status = model.experiment.data.calc_status
    for angle, expected in [(64.5953, 'incl'), (64.6953, 'excl'), (64.7953, 'incl')]:
        index = np.flatnonzero(np.abs(grid - angle) < 1e-5)
        assert len(index) == 1, 'The mask controls occur on each examples own observed point list'
        assert str(status[int(index[0])]) == expected, (
            'Each example excludes the dead cell and retains both neighbours'
        )
    model.save_as(tmp_path / 'saved')
    original = reference.columns((directory / 'structures/cosio.edi').read_text())
    saved = reference.columns((tmp_path / 'saved/structures/cosio.edi').read_text())
    for key, values in original.items():
        if key.startswith(('_parent_', '_space_group_symop_magn')):
            assert saved.get(key) == values, (
                'The delivered fit record retains its validated magnetic symmetry and propagation'
            )


def test_extended_scan_retains_the_original_files_and_reverses_the_full_sequence():
    before = CLI / 'pd-neut-cwl_cosio-d20_scan-162f/project/experiments/d20_scan'
    after = CLI / 'pd-neut-cwl_cosio-d20_scan-213f/project'
    original = sorted(before.glob('*.dat'))
    extended = sorted((after / 'experiments/d20_scan').glob('*.dat'))
    assert len(original) == 162 and len(extended) == 213, (
        'The magnetic scan adds the declared low-temperature files to the complete earlier scan'
    )
    for source in original:
        assert (
            after / 'experiments/d20_scan' / source.name
        ).read_bytes() == source.read_bytes(), (
            'Extending the scan preserves every original observed file byte for byte'
        )
    analysis = reference.columns((after / 'analysis/analysis.edi').read_text())
    assert analysis['_sequential_fit.reverse'] == ['true'], (
        'The full magnetic sequence reverses the file ordering to start at the lowest temperature'
    )


def test_preview_example_background_leaves_the_first_magnetic_peak_unpinned():
    path = CLI / 'pd-neut-cwl_cosio-d20_2k/project/experiments/d20.edi'
    values = reference.columns(path.read_text())
    positions = [float(value.split('(')[0]) for value in values['_background.position']]
    assert not any(8 <= position <= 12 for position in positions), (
        'The preview background has no interpolation point in the first magnetic peak and rise'
    )
    assert sum(6 <= x < 8 for x in positions) >= 2 and sum(12 < x <= 16 for x in positions) >= 2, (
        'Background control points bracket the first magnetic peak on both sides'
    )
    assert values['_excluded_region.start'][0] == '0', 'The first exclusion starts at zero degrees'
    assert float(values['_excluded_region.end'][0]) == 6, (
        'The first example exclusion ends at six degrees instead of the preview eight'
    )


@pytest.mark.parametrize('name', ['pd-neut-cwl_cosio-d20_2k', 'pd-neut-cwl_cosio-d20_scan-213f'])
def test_magnetic_worked_examples_are_in_documentation_navigation(name):
    assert name in (ROOT / 'mkdocs.yml').read_text(), (
        'Both magnetic worked examples are reachable through the documentation navigation'
    )
