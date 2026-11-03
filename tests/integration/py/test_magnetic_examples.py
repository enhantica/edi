"""The magnetic worked examples retain their declared execution and fit records."""

import csv
import json
from pathlib import Path

import pytest
import yaml

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
    assert all(int(row['fit_result.iterations']) > 0 for row in rows), (
        'Every scan row records an executed fit rather than a copied initial model'
    )
    moments = [
        sum(float(row[f'cosio.atom_site_moment.Co1.crystalaxis_{axis}']) ** 2 for axis in 'xyz')
        ** 0.5
        for row in rows
    ]
    cold = [m for t, m in zip(temperatures, moments, strict=True) if t < 10]
    warm = [m for t, m in zip(temperatures, moments, strict=True) if 50 <= t <= 60]
    assert cold and warm, (
        'The scan samples both the ordered state and temperatures around the reported transition'
    )
    assert sum(warm) / len(warm) < sum(cold) / len(cold), (
        'The fitted ordered moment falls towards zero near the reported Neel temperature'
    )
