"""Stage independently retained successful/failed CSV rows for a real app resume."""

import csv
import shutil
from pathlib import Path

from tests.fixtures.scan_lifecycle.prepare import prepare

ROOT = Path(__file__).resolve().parents[3]
REFERENCE = Path(__file__).with_name('reference.csv')


def freeze_reference(crysta_source):
    source = Path(crysta_source) / (
        'tests/fitting/cosio-d20-scan-3f/diffraction-lib/project/analysis/results.csv'
    )
    shutil.copyfile(source, REFERENCE)


def stage(destination, *, completed=False, success=False):
    destination = Path(destination)
    names = prepare(destination, 3)
    with REFERENCE.open(newline='') as stream:
        reader = csv.DictReader(stream)
        header = reader.fieldnames
        rows = list(reader)
    by_name = {Path(row['file_path']).name: row for row in rows}
    ordered = [dict(by_name[name]) for name in names]
    for index, row in enumerate(ordered):
        row['file_path'] = 'experiments/d20_scan/' + names[index]
        row['fit_result.success'] = 'True' if index == 0 else 'False'
    if completed:
        ordered[-1].update({
            'fit_result.success': 'True' if success else 'False',
            'fit_result.reduced_chi_square': '7.125',
            'fit_result.iterations': '19',
        })
    else:
        ordered = ordered[:2]
    path = destination / 'analysis/results.csv'
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=header)
        writer.writeheader()
        writer.writerows(ordered)
    return names, header, ordered, path.read_bytes()
