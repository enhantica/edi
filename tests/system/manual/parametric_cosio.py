"""Compare full no-sharing Joint and Independent fits on the staged CoSiO 213f project."""

import argparse
import csv
import math
import shutil
import tempfile
from pathlib import Path
from time import perf_counter

import edi


def fit(source, destination, mode):
    shutil.copytree(source, destination)
    analysis = destination / 'analysis/analysis.edi'
    text = analysis.read_text()
    assert text.count('_fitting_mode.type sequential') == 1, (
        'The reference starts with the shipped CoSiO sequential project'
    )
    assert '_parametric_fit_shared.' not in text, 'The two runs have no shared degrees of freedom'
    analysis.write_text(
        text.replace('_fitting_mode.type sequential', f'_fitting_mode.type {mode}')
    )
    (destination / 'analysis/results.csv').unlink(missing_ok=True)
    project = edi.Project.load(destination)
    started = perf_counter()
    project.analysis.fit()
    elapsed = perf_counter() - started
    with (destination / 'analysis/results.csv').open(newline='') as stream:
        rows = list(csv.DictReader(line for line in stream if not line.startswith('#')))
    by_file = {Path(row['file_path']).name: row for row in rows}
    expected = {path.name for path in (destination / 'experiments/d20_scan').glob('*.dat')}
    assert len(rows) == len(expected) == 213 and by_file.keys() == expected, (
        'Each published table contains exactly one result for every CoSiO observation'
    )
    return by_file, elapsed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        'project', type=Path, help='CoSiO 213f project with its measurements staged'
    )
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='parametric-cosio-') as scratch:
        root = Path(scratch)
        reference, reference_time = fit(args.project, root / 'independent', 'independent')
        actual, actual_time = fit(args.project, root / 'joint', 'joint')
    print(f'Independent {reference_time:.2f} s, Joint {actual_time:.2f} s', flush=True)
    metric = 'fit_result.reduced_chi_square'
    exhausted = [
        name
        for name, row in actual.items()
        if row['fit_result.termination'] == 'max_iter_exhausted'
        and reference[name]['fit_result.success'] == 'True'
    ]
    deviations = [
        name
        for name, row in actual.items()
        if not math.isclose(float(row[metric]), float(reference[name][metric]), rel_tol=0.01)
    ]
    assert not exhausted and not deviations and actual_time <= 2 * reference_time, (
        'No-sharing Joint must keep the Independent agreement within 1%, avoid introducing '
        f'maximum-iteration stops, and take at most twice as long. Exhausted: {exhausted}; '
        f'agreement differences: {deviations}'
    )


if __name__ == '__main__':
    main()
