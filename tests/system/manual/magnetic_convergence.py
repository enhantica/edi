"""Offline ADR-0111 gates on disposable copies of the actual D20 projects.

Run `python tests/system/manual/magnetic_convergence.py frame` or `scan`.
For `nuclear`, pass `--before-extension` with the edi extension directory linked
against crysta immediately before the change. Use the same build configuration.
The full scans belong here because their runtime exceeds the system test budget.
"""

import argparse
import csv
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import edi
import numpy as np

CLI = Path(__file__).resolve().parents[3] / 'docs/user/cli'
MAGNETIC = 'pd-neut-cwl_cosio-d20_scan-213f'
NUCLEAR = 'pd-neut-cwl_cosio-d20_scan'
PARAMAGNETIC_FILE = '01_124_082p1890.dat'
MOMENTS = {
    f'structure.atom_site_moment[{site}].crystalaxis_{axis}'
    for site, axis in [('Co1', 'x'), ('Co1', 'y'), ('Co1', 'z'), ('Co2', 'y')]
}


def stage(name, scratch):
    destination = Path(scratch) / 'project'
    shutil.copytree(CLI / name / 'project', destination)
    return destination


def parameter_at(project, path):
    node = project
    for segment in path.split('.'):
        name, bracket, key = segment.partition('[')
        node = getattr(node, name)
        if bracket:
            key = key.removesuffix(']')
            # Fit paths carry one-based background row IDs. The public view indexes from zero.
            node = node[int(key) - 1] if name == 'background' else node[key]
    return node


def square_covariance(project, paths):
    """Construct J in u = M² from profile evaluations and invert with a weighted QR solve."""
    project.analysis.calculate()
    data = project.experiment.data
    included = np.asarray(data.calc_status) == 'incl'
    observed = np.asarray(data.intensity_meas)[included]
    sigma = np.asarray(data.intensity_meas_su)[included]

    def calculate():
        project.analysis.calculate()
        return np.asarray(project.experiment.data.intensity_calc)[included]

    at_zero = calculate()
    columns = []
    for path in paths:
        parameter = parameter_at(project, path)
        value = parameter.value
        if path in MOMENTS:
            # All other moments are zero. The profile is linear in this component's square.
            parameter.value = 1
            derivative = calculate() - at_zero
        else:
            step = 1e-5 * max(abs(value), 1.0)
            parameter.value = value + step
            plus = calculate()
            parameter.value = value - step
            derivative = (plus - calculate()) / (2 * step)
        parameter.value = value
        columns.append(derivative / sigma)
    triangular = np.linalg.qr(np.column_stack(columns), mode='r')
    inverse = np.linalg.solve(triangular, np.eye(len(paths)))
    reduced_chi_square = np.sum(np.square((at_zero - observed) / sigma)) / (
        len(observed) - len(paths)
    )
    return reduced_chi_square, reduced_chi_square * (inverse @ inverse.T)


def check_frame():
    with tempfile.TemporaryDirectory(prefix='magnetic-frame-') as scratch:
        project = edi.Project.load(stage(MAGNETIC, scratch))
        project.analysis.template_file = PARAMAGNETIC_FILE
        project.analysis.fitting_mode = 'single'
        assert all(parameter_at(project, path).free for path in MOMENTS), (
            'The paramagnetic fit must free all four cobalt components'
        )
        result = project.analysis.fit()
        assert result.success, 'The isolated paramagnetic frame converges'
        assert 1 <= result.iterations <= 12, (
            f'The 82.189 K frame converges in a handful of iterations, got {result.iterations}'
        )
        assert all(result.values[path] == 0 for path in MOMENTS), (
            f'All four free moments reach exact zero: {[result.values[path] for path in MOMENTS]}'
        )
        paths = list(result.uncertainty)
        reduced_chi_square, covariance = square_covariance(project, paths)
        assert math.isclose(reduced_chi_square, result.reduced_chi_square, rel_tol=1e-10), (
            'The independent covariance uses the same included observations and weights'
        )
        for path in sorted(MOMENTS):
            index = paths.index(path)
            bound = result.uncertainty[path]
            expected = covariance[index, index] ** 0.25
            assert math.isfinite(bound) and bound > 0, f'{path} has a finite positive size bound'
            assert math.isclose(bound, expected, rel_tol=2e-5), (
                f'{path} reports {bound} μB, independent sqrt(sigma(u)) is {expected} μB'
            )
            print(f'{path}: {bound:.9g} μB, independent {expected:.9g} μB')
        print(f'82.189 K: {result.iterations} iterations, reduced χ² {reduced_chi_square:.9g}')


def check_moment_trend(rows):
    temperatures = [float(row['diffrn.ambient_temperature']) for row in rows]
    assert min(temperatures) < 3, 'The fitted sequence includes the measured low-temperature data'
    assert all(int(row['fit_result.iterations']) >= 0 for row in rows), (
        'Every fitted file records its iteration count'
    )
    columns = []
    for axis in 'xyz':
        matching = [key for key in rows[0] if key.endswith('Co1.crystalaxis_' + axis)]
        assert len(matching) == 1, 'Every free Co1 component has one recorded result column'
        columns.append(matching[0])
    moments = [sum(float(row[key]) ** 2 for key in columns) ** 0.5 for row in rows]
    cold = [
        moment
        for temperature, moment in zip(temperatures, moments, strict=True)
        if temperature < 10
    ]
    warm = [
        moment
        for temperature, moment in zip(temperatures, moments, strict=True)
        if 50 <= temperature <= 60
    ]
    assert cold and warm, (
        'The fitted scan samples the ordered state and the reported transition region'
    )
    assert sum(warm) / len(warm) < sum(cold) / len(cold), (
        'The fitted ordered moment falls towards zero near the reported Neel temperature'
    )


def fit_scan(cold_first):
    with tempfile.TemporaryDirectory(prefix='magnetic-scan-') as scratch:
        directory = stage(MAGNETIC, scratch)
        analysis = directory / 'analysis/analysis.edi'
        text = analysis.read_text()
        assert text.count('_sequential_fit.reverse true') == 1, (
            'The published scan declares cold-to-hot order explicitly'
        )
        if not cold_first:
            analysis.write_text(
                text.replace('_sequential_fit.reverse true', '_sequential_fit.reverse false')
            )
        project = edi.Project.load(directory)
        assert all(parameter_at(project, path).free for path in MOMENTS), (
            'Each scan direction starts with all four components free'
        )
        result = project.analysis.fit()
        assert result.success, 'The scan reaches a successful terminal state'
        with (directory / 'analysis/results.csv').open(newline='') as stream:
            rows = list(csv.DictReader(stream))
        files = {Path(row['file_path']).name for row in rows}
        source = {path.name for path in (directory / 'experiments/d20_scan').glob('*.dat')}
        assert len(rows) == len(source) == 213, 'The comparison fits all 213 observations'
        assert files == source, 'The scan fits each declared data file exactly once'
        temperatures = [float(row['diffrn.ambient_temperature']) for row in rows]
        assert temperatures == sorted(temperatures, reverse=not cold_first), (
            'Each replay follows the intended temperature direction'
        )
        assert all(row['fit_result.success'].lower() == 'true' for row in rows), (
            'Every frame contributes a converged objective'
        )
        check_moment_trend(rows)
        return {
            Path(row['file_path']).name: float(row['fit_result.reduced_chi_square'])
            for row in rows
        }


def check_scan():
    cold = fit_scan(cold_first=True)
    hot = fit_scan(cold_first=False)
    cold_sum = math.fsum(cold.values())
    hot_sum = math.fsum(hot.values())
    print(
        f'213 frames in each direction. Summed reduced chi-square: {cold_sum:.9f} / {hot_sum:.9f}'
    )
    differences = sorted(
        ((abs(cold[file] - hot[file]), file, cold[file], hot[file]) for file in cold),
        reverse=True,
    )
    # ADR-0111 reports a 0.007 difference at the shown precision.
    assert abs(cold_sum - hot_sum) <= 0.02, (
        'Both directions agree within 0.02 in summed reduced chi-square. '
        f'Largest frame differences (delta, file, cold, hot): {differences[:5]}'
    )


def nuclear_snapshot():
    with tempfile.TemporaryDirectory(prefix='nuclear-control-') as scratch:
        directory = stage(NUCLEAR, scratch)
        project = edi.Project.load(directory)
        assert not project.structure.atom_site_moment, 'The comparison is a nuclear-only project'
        result = project.analysis.fit()
        assert result.success, 'The nuclear control fit converges'
        outputs = sorted(directory.rglob('*.edi')) + sorted(directory.rglob('*.csv'))
        assert (directory / 'analysis/results.csv') in outputs, 'The control produces fit bytes'
        return {
            'iterations': result.iterations,
            'reduced_chi_square': result.reduced_chi_square.hex(),
            'rwp': result.rwp.hex(),
            'files': {
                str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in outputs
            },
        }


def check_nuclear(before_extension):
    before = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), 'nuclear-snapshot'],
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, 'EDI_EXTENSION_DIR': str(before_extension.resolve())},
    )
    expected = json.loads(before.stdout)
    actual = nuclear_snapshot()
    assert actual == expected, (
        'The nuclear fit retains byte-identical files and binary fit metrics'
    )
    print(f'Nuclear control: {len(actual["files"])} matching files and identical fit metrics')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('case', choices=('frame', 'scan', 'nuclear', 'nuclear-snapshot'))
    parser.add_argument('--before-extension', type=Path)
    args = parser.parse_args()
    if args.case == 'frame':
        check_frame()
    elif args.case == 'scan':
        check_scan()
    elif args.case == 'nuclear-snapshot':
        print(json.dumps(nuclear_snapshot()))
    elif args.before_extension is None:
        parser.error('nuclear requires --before-extension')
    else:
        check_nuclear(args.before_extension)


if __name__ == '__main__':
    main()
