"""Retain the measured opening baseline and its published targets."""

import argparse
import csv
import hashlib
import json
from pathlib import Path
from statistics import median

FOLDER = Path(__file__).resolve().parent
ROUTES = {'folder': 'folder', 'edi': 'project.edi', 'zip': 'zip', 'example': 'example'}


def generate(source):
    raw = source.read_bytes()
    records = {route: {'cold': {}, 'warm': {}} for route in ROUTES.values()}
    for row in csv.reader(raw.decode().splitlines(), delimiter='\t'):
        if len(row) != 6 or row[0] not in ROUTES or row[2] != 'open-probe':
            continue
        route, phase, mark = ROUTES[row[0]], row[3], row[4]
        if phase in {'cold', 'warm'}:
            records[route][phase].setdefault(mark, []).append(float(row[5]))
    routes = {}
    for name, phases in records.items():
        routes[name] = {}
        for phase, values in phases.items():
            if any(len(values.get(mark, [])) != 5 for mark in ('first-frame', 'calculated-frame')):
                raise ValueError('Each route and phase retains all five measured opening runs')
            routes[name][phase] = {
                'baseline_first_display_ms': median(values['first-frame']),
                'baseline_usable_ms': median(values['calculated-frame']),
                'target_first_display_ms': (600 if name == 'example' else 500)
                if phase == 'cold'
                else 800,
                'target_usable_ms': 1000 if phase == 'cold' else 1500,
                'marks_ms': {key: median(rows) for key, rows in sorted(values.items())},
            }
    result = {
        'claim': 'Measured baseline and targets; '
        'current app performance must be measured separately.',
        'machine': 'visa-prod-2224',
        'display': 'Xwayland on headless Weston; Mesa llvmpipe; 1280x768',
        'project': 'sc-neut-tof_taurine_fit',
        'measurement_date': '2026-10-25',
        'source': 'baseline.tsv',
        'raw_sha256': hashlib.sha256(raw).hexdigest(),
        'routes': routes,
    }
    (FOLDER / 'baseline.tsv').write_bytes(raw)
    (FOLDER / 'baseline.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('measurement', type=Path)
    generate(parser.parse_args().measurement)
