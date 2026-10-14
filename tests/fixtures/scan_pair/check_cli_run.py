"""Require done status and one successful CLI result per expected input file."""

import csv
import pathlib
import sys

project, record = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
expected = int(sys.argv[3])
text = record.read_text(encoding='utf-8', errors='replace')
if 'status=done' not in text.splitlines():
    sys.exit('the record does not say status=done')
with (project / 'analysis' / 'results.csv').open(encoding='utf-8') as stream:
    rows = list(csv.DictReader(stream))
files = sorted(p.name for p in (project / 'experiments' / 'd20_scan').glob('*.dat'))
if len(rows) != expected or len(files) != expected:
    sys.exit(f'{len(rows)} result rows and {len(files)} data files, not {expected}')
if sorted(pathlib.Path(r['file_path']).name for r in rows) != files:
    sys.exit('the result rows are not one per data file')
bad = [r['file_path'] for r in rows if r['fit_result.success'] != 'True']
if bad:
    sys.exit(f'{len(bad)} files did not succeed, first {bad[0]}')
