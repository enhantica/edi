"""Refresh the schema regression seed; integer-domain expectations use C++ limits."""

import json
from pathlib import Path

import edi

ROOT = Path(__file__).resolve().parents[3]
project = edi.Project.load(ROOT / 'docs/user/cli/pd-neut-cwl_lbco-hrpt_start-2/project')
document = json.loads(project.report.model().to_json())
scene = document['structures'][0]['scene']
drawing = document['structures'][0]['drawing']
label = {'atom': 0, 'anchor': [0, 0, 0], 'text': 'independent label'}
scene['labels'] = [label]
document['structures'][0]['labels'] = [label]
drawing['shared'] = [0]
if not drawing['cylinders']:
    drawing['cylinders'] = [drawing['spheres'][0]]
if not scene['bonds']:
    scene['bonds'] = [
        {
            'row': 0,
            'atom_1': 0,
            'atom_2': 0,
            'start': [0, 0, 0],
            'end': [1, 0, 0],
            'distance': 1,
            'color_1': '#123456',
            'color_2': '#123456',
        }
    ]
document['correlations'] = {
    'labels': ['a', 'b'],
    'values': [1, 0, 0, 1],
    'level': 0,
    'available': 2,
    'empty_text': '',
}
for structure in document['structures']:
    structure['categories'] = []
    for key in ('atoms', 'bonds', 'labels'):
        structure['scene'][key] = structure['scene'][key][:1]
    for key in ('spheres', 'cylinders', 'shared'):
        structure['drawing'][key] = structure['drawing'][key][:1]
for experiment in document['experiments']:
    experiment['categories'] = []
    for series in experiment['pattern']['series']:
        for key in ('x', 'y', 'rows', 'bar_low', 'bar_high'):
            series[key] = series[key][:1]
document['generated'] = '2026-10-14 00:00 UTC'
Path(__file__).with_name('schema-seed.json').write_text(
    json.dumps(document, indent=2, ensure_ascii=False, allow_nan=False) + '\n'
)
