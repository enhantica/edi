"""Offline scan invariants from ADR-0112/0113 and the held-Y owner decision.

Long scans run here, outside collected test budgets. Every correctness value is
an invariant or the owner's per-file 0.01 bound; snapshots are labelled regressions.
"""

import argparse
import csv
import ctypes
import hashlib
import importlib
import json
import math
import re
import shutil
import struct
import tempfile
from pathlib import Path


def prepare(source, root, ladder, free_c2):
    shutil.copytree(source, root)
    analysis = root / 'analysis/analysis.edi'
    if ladder:
        analysis.write_text(analysis.read_text().replace('_minimizer.descent fast_descent\n', ''))
    if free_c2:
        for path in (root / 'experiments/d20_scan').glob('*.dat'):
            if path.name not in {
                '01_213_002p3440.dat',
                '01_212_002p3560.dat',
                '01_211_002p3630.dat',
            }:
                path.unlink()
        structure = root / 'structures/cosio.edi'
        text, count = re.subn(
            r'(?ms)^loop_\n_magnetic_form_factor.type_symbol\n.*?(?=\n\n)',
            'loop_\n_magnetic_form_factor.type_symbol\n_magnetic_form_factor.ion\n'
            '_magnetic_form_factor.approximation\n_magnetic_form_factor.j2_coefficient\n'
            'Co Co2+ dipole 0.2()',
            structure.read_text(),
        )
        assert count == 1, 'The witness replaces the one declared cobalt form-factor loop'
        structure.write_text(text)


def choose_workers(api, workers, run_options):
    setter = getattr(api, '_set_scan_workers', None)
    if setter is not None:
        setter(workers)
        assert api._scan_workers() == max(1, workers), (
            'The run option clamps below one to one worker'
        )
    elif run_options is not None:
        bridge = ctypes.CDLL(str(run_options.resolve()))
        bridge.set_workers.argtypes = [ctypes.c_int]
        bridge.set_workers.restype = None
        bridge.get_workers.restype = ctypes.c_int
        bridge.set_workers(workers)
        assert bridge.get_workers() == max(1, workers), (
            'The public C++ run option applies the requested worker count'
        )
    else:
        assert workers == 1, 'Parallel workers must be accepted as a run option by the engine'


def scan_rows(root, free_c2):
    if not (root / 'analysis/results.csv').exists():
        return []
    with (root / 'analysis/results.csv').open(newline='') as stream:
        rows = list(csv.DictReader(stream))
    with (root / 'analysis/results-provenance.csv').open(newline='') as stream:
        provenance = list(csv.DictReader(stream))
    source_files = {p.name for p in (root / 'experiments/d20_scan').glob('*.dat')}
    assert len(rows) == len(source_files), 'Every measured file appears once in the executed scan'
    assert {Path(row['file_path']).name for row in rows} == source_files, (
        'The scan omits no measured file'
    )
    assert [r['file_path'] for r in rows] == [r['file_path'] for r in provenance], (
        'Each fitted row retains its own ordered termination provenance'
    )
    stalled = [
        (Path(r['file_path']).name, r['termination'])
        for r in provenance
        if r['termination'] != 'chi_converged'
    ]
    assert not stalled, f'Every parallel scan file reaches chi_converged: {stalled}'
    if free_c2:
        expected = 'cosio.magnetic_form_factor.Co.j2_coefficient'
        assert expected in rows[0], 'A sequential scan publishes the free C2 result column'
        assert expected + '.uncertainty' in rows[0], (
            'The C2 column has its own fitted uncertainty column'
        )
        assert all(math.isfinite(float(r[expected])) for r in rows), (
            'Every file publishes its fitted C2 value'
        )
    return rows


def fit(api, source, workers, *, ladder=False, free_c2=False, run_options=None):
    with tempfile.TemporaryDirectory(prefix='parallel-scan-') as scratch:
        root = Path(scratch) / 'project'
        prepare(source, root, ladder, free_c2)
        choose_workers(api, workers, run_options)
        project = api.Project.load(root)
        if free_c2:
            assert sum(p.name == 'j2_coefficient' for p in project.free_parameters) == 1, (
                'The witness admits exactly one free C2 parameter'
            )
        result = project.analysis.fit()
        rows = scan_rows(root, free_c2)
        assert result.success, 'The scan completes successfully'
        original = {
            str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob('*.edi')) + sorted((root / 'analysis').glob('*.csv'))
        }
        project.save_as(root / 'saved')
        assert all(
            '_sequential_fit.max_workers' not in p.read_text() for p in root.rglob('*.edi')
        ), 'The machine worker count is never serialized into a project'
        project.analysis.calculate()
        calculated = hashlib.sha256(
            b''.join(struct.pack('>d', v) for v in project.experiment.data.intensity_calc)
        ).hexdigest()
        return {
            'rows': rows,
            'files': original,
            'iterations': result.iterations,
            'chi2': result.reduced_chi_square.hex(),
            'calculated': calculated,
            'values': {name: value.hex() for name, value in getattr(result, 'values', {}).items()},
            'uncertainty': {
                name: value.hex() for name, value in getattr(result, 'uncertainty', {}).items()
            },
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--engine', choices=('crysta', 'edi'), required=True)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--case', choices=('parallel', 'snapshot', 'free-c2'), required=True)
    parser.add_argument('--run-options', type=Path)
    parser.add_argument('--ladder', action='store_true')
    parser.add_argument('--snapshot', type=Path)
    args = parser.parse_args()
    api = importlib.import_module(args.engine)
    if args.case != 'parallel':
        actual = fit(
            api,
            args.project,
            1,
            ladder=args.ladder,
            free_c2=args.case == 'free-c2',
            run_options=args.run_options,
        )
        if args.snapshot:
            args.snapshot.write_text(json.dumps(actual, sort_keys=True) + '\n')
        print(
            json.dumps({
                'case': args.case,
                'rows': len(actual['rows']),
                'iterations': actual['iterations'],
                'chi2': actual['chi2'],
            })
        )
        return
    assert hasattr(api, '_set_scan_workers') or args.run_options is not None, (
        'The parallel gate requires an engine run-option control, never a project item'
    )
    serial = fit(api, args.project, 1, run_options=args.run_options)
    repeated = fit(api, args.project, 1, run_options=args.run_options)
    assert serial == repeated, (
        'One worker gives byte-identical files and binary fit metrics on repeated runs'
    )
    summaries = []
    for workers in (2, 5):
        actual = fit(api, args.project, workers, run_options=args.run_options)
        before = {
            row['file_path']: float(row['fit_result.reduced_chi_square']) for row in serial['rows']
        }
        after = {
            row['file_path']: float(row['fit_result.reduced_chi_square']) for row in actual['rows']
        }
        assert before.keys() == after.keys(), (
            'Every worker count fits the same declared measured files'
        )
        differences = [(abs(before[name] - after[name]), Path(name).name) for name in before]
        maximum, file = max(differences)
        print(
            json.dumps({
                'workers': workers,
                'files': len(after),
                'max_per_file_delta': maximum,
                'file': file,
            }),
            flush=True,
        )
        assert maximum <= 0.01, (
            'The Y-held scan stays within 0.01 per file for every parallel worker count'
        )
        summaries.append({
            'workers': workers,
            'files': len(after),
            'max_per_file_delta': maximum,
            'file': file,
        })
    if args.snapshot:
        args.snapshot.write_text(
            json.dumps({'serial_identical': True, 'comparisons': summaries}, indent=2) + '\n'
        )


if __name__ == '__main__':
    main()
