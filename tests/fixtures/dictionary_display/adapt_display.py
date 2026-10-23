"""Extend the existing input oracle with dictionary-owned display expectations."""

import argparse
import importlib.util
import json
import re
from functools import cache
from pathlib import Path

import yaml
from reference import display

ROOT = Path(__file__).resolve().parents[3]
AXES = {
    'sampleForm': 'sample_form',
    'beamMode': 'beam_mode',
    'radiationProbe': 'radiation_probe',
    'scatteringType': 'scattering_type',
}


@cache
def input_rows(path):
    spec = importlib.util.spec_from_file_location(
        'display_inputs', ROOT / 'tests/fixtures/e04_t1/generate.py'
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    text = path.read_text()
    axis = 'time_of_flight' if re.search(r'_peak.type\s+tof-', text) else 'two_theta'
    return axis, module.tables(path, ('_data',)).get('data', [])


def numeric_expectation(case, field, items, categories):
    name, value, kind = field
    path = ROOT / case['path'] / 'experiments' / (case['selection'] + '.edi')
    axis, rows = input_rows(path)
    leaf = name.split('.')[1]
    uid = (
        'data.' + axis
        if rows
        else 'data_range.'
        + axis
        + '_'
        + {'minimum': 'min', 'maximum': 'max', 'step': 'step'}[leaf]
    )
    row = items[uid]
    mode, digits = (row.get('format') or categories[row['category']]['format']).split()
    if kind == 'number':
        return float(display(float(value), mode, int(digits)))
    values = [row[axis]['value'] for row in rows]
    steps = [right - left for left, right in zip(values, values[1:], strict=False)]
    low, high = [display(value, mode, int(digits)) for value in (min(steps), max(steps))]
    return low if low == high else low + '\N{EN DASH}' + high


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('dictionary', type=Path)
    args = parser.parse_args()
    source = yaml.safe_load(args.dictionary.read_text())
    items = {row['uid']: row for row in source['parameters'] + source.get('items', [])}
    categories = {row['id']: row for row in source['categories']}
    frozen = json.loads(
        (ROOT / 'tests/fixtures/e04_t1/display_oracle.js')
        .read_text()
        .split('var frozen = ', 1)[1]
        .removesuffix(';\n')
    )
    expected = {}
    for case in frozen['cases']:
        for name, value, kind in case['fields']:
            key = case['tag'] + '::' + name
            if name.startswith('experimentType.'):
                row = items['experiment_type.' + AXES[name.split('.')[1]]]
                expected[key] = next(
                    option['display_name'] for option in row['options'] if option['token'] == value
                )
            elif name.startswith('range.') and name != 'range.points':
                expected[key] = numeric_expectation(case, (name, value, kind), items, categories)
    output = '// Input values remain frozen; display text follows the dictionary.\nvar expected = '
    Path(__file__).with_name('display_expectations.js').write_text(
        output + json.dumps(expected, indent=2, ensure_ascii=False) + ';\n'
    )


if __name__ == '__main__':
    main()
