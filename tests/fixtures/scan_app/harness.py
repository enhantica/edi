"""Visible producers for actual app/core/worker observations and synthetic inputs."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import shutil
import struct
import subprocess
import sys
from pathlib import Path

from tests.conftest import crysta_reference_prefix, crysta_reference_source
from tests.fixtures.scan_app.build_probe import (
    fingerprint,
    fingerprint_headers,
    fixture_fingerprint,
)

ROOT = Path(__file__).resolve().parents[3]
FULL = ROOT / 'docs/user/cli/pd-neut-cwl_cosio-d20_scan-162f/project'
SMALL = ROOT / 'tests/fixtures/scan_template/project'


def read_csv(text):
    return list(csv.DictReader(io.StringIO(text)))


def csv_text(rows, fields=None):
    output = io.StringIO(newline='')
    writer = csv.DictWriter(output, fieldnames=fields or list(rows[0]), lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def copy_project(source, destination, mode='sequential', iterations=None):
    shutil.copytree(source, destination)
    for path in (destination / 'analysis').glob('results*.csv'):
        path.unlink()
    analysis = destination / 'analysis/analysis.edi'
    text = analysis.read_text().replace(
        '_fitting_mode.type sequential', '_fitting_mode.type ' + mode
    )
    if iterations is not None:
        text = text.replace(
            '_minimizer.max_iterations 1000', '_minimizer.max_iterations ' + str(iterations)
        )
    analysis.write_text(text)
    return destination


def measured(path):
    columns = []
    for line in path.read_text().splitlines():
        try:
            values = tuple(map(float, line.split()))
        except ValueError:
            continue
        if len(values) == 3:
            columns.append((
                round(values[0], 4),
                values[1],
                max(1.0, values[2]) if values[2] < 0.0001 else values[2],
            ))
    return columns


def template_measured(path):
    lines = path.read_text().split('loop_\n_data.two_theta\n', 1)[1].splitlines()
    tags = ['_data.two_theta']
    while lines and lines[0].startswith('_data.'):
        tags.append(lines.pop(0))
    wanted = [
        tags.index(name)
        for name in ('_data.two_theta', '_data.intensity_meas', '_data.intensity_meas_su')
    ]
    columns = []
    for line in lines:
        if not line.strip():
            break
        values = list(map(float, line.split()))
        if len(values) != len(tags):
            raise ValueError('Follow: saved template data must match their declared columns')
        x, y, sigma = [values[index] for index in wanted]
        columns.append((round(x, 4), y, max(1.0, sigma) if sigma < 0.0001 else sigma))
    if not columns:
        raise ValueError('Follow: the independent saved template must contain measured data')
    return columns


def columns_hash(columns):
    flattened = [point[column] for column in range(3) for point in columns]
    return hashlib.sha256(struct.pack('=' + 'd' * len(flattened), *flattened)).hexdigest()


def measured_hash(path):
    return columns_hash(measured(path))


def files(path):
    return sorted((path / 'experiments/d20_scan').glob('*.dat'))


def work_rows(path):
    records = [line.split('\t') for line in path.read_text().splitlines()] if path.exists() else []
    entries = {row[2]: [row[1], '', row[3]] for row in records if row[0] == 'entry'}
    for row in records:
        if row[0] == 'receipt' and row[2] in entries:
            entries[row[2]][1] = row[3]
    return list(entries.values())


class Harness:
    def __init__(self, scratch, library=None, preload=None):
        self.scratch = scratch
        self.library, self.preload = library, preload
        self.serial = 0
        existing = os.environ.get('EDI_SCAN_APP_PROBE_RECEIPT')
        if existing:
            record_path = Path(existing)
        else:
            sdk, source = crysta_reference_prefix(), crysta_reference_source()
            directory = scratch / 'host'
            fixture = ROOT / 'tests/fixtures/scan_app'
            gui = os.environ.get('EDI_SCAN_APP_GUI_SOURCE')
            command = [
                'pixi',
                'run',
                '-e',
                'app',
                'python',
                str(fixture / 'build_probe.py'),
                '--root',
                str(ROOT),
                '--build',
                str(directory),
                '--sdk',
                str(sdk),
                '--engine-source',
                str(source),
            ]
            if gui:
                command.extend(['--gui-source', gui])
            subprocess.run(command, cwd=ROOT, check=True)
            record_path = directory / 'receipt.json'
        self.receipt = json.loads(record_path.read_text())
        if self.receipt['production'] != fingerprint(ROOT):
            raise RuntimeError(
                'Scan execution: observer production bytes differ from the tested tree'
            )
        fixture = ROOT / 'tests/fixtures/scan_app'
        if self.receipt['fixture'] != fixture_fingerprint(fixture):
            raise RuntimeError(
                'Scan execution: observer fixture bytes differ from the tested fixture'
            )
        self.executable = Path(self.receipt['executable'])
        self.reference_package = Path(self.receipt['reference_package'])
        reference_binary = {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in self.reference_package.glob('crysta/_crysta.*')
            if path.is_file()
        }
        if not reference_binary or reference_binary != self.receipt['reference_binary']:
            raise RuntimeError(
                'Scan execution: actual Python reference binding differs from its receipt'
            )
        if self.receipt['binary'] != hashlib.sha256(self.executable.read_bytes()).hexdigest():
            raise RuntimeError('Scan execution: observer binary digest differs from its receipt')
        io_library = self.receipt.get('io_fault_library')
        if (
            not io_library
            or io_library['sha256']
            != hashlib.sha256(Path(io_library['path']).read_bytes()).hexdigest()
        ):
            raise RuntimeError(
                'Output transaction: storage actor library differs from its receipt'
            )
        sdk_override = os.environ.get('EDI_SCAN_APP_SDK')
        sdk = Path(sdk_override) if sdk_override else crysta_reference_prefix()
        if self.receipt['sdk_headers'] != fingerprint_headers(sdk / 'include'):
            raise RuntimeError('Scan execution: observer headers differ from the declared SDK')
        if (
            self.receipt['sdk_library']
            != hashlib.sha256((sdk / 'lib/libcrysta_core.a').read_bytes()).hexdigest()
        ):
            raise RuntimeError('Scan execution: observer library differs from the declared SDK')
        if self.receipt['engine_sha'] != (sdk / '.crysta-sha').read_text().strip():
            raise RuntimeError(
                'Scan execution: observed engine source differs from the linked SDK identity'
            )

    def python_reference(self, project):
        producer = ROOT / 'tests/fixtures/scan_app/python_reference.py'
        command = [
            sys.executable,
            str(producer),
            str(self.reference_package),
            str(project),
            self.receipt['engine_sha'],
            '--sdk-digest',
            self.receipt['sdk_library'],
        ]
        if cache := os.environ.get('EDI_SCAN_APP_REFERENCE_CACHE'):
            command.extend(['--cache', cache])
        result = subprocess.run(
            command,
            env={**os.environ, 'OMP_NUM_THREADS': '1'},
            text=True,
            check=False,
            capture_output=True,
            timeout=7200,
        )
        if result.returncode:
            raise RuntimeError(
                'Scan run, consistency: public Python reference failed: ' + result.stderr
            )
        return json.loads(result.stdout.strip().splitlines()[-1])

    def invoke(self, command, project, *arguments, observe=False, deadline=7200):
        self.serial += 1
        if progress := os.environ.get('SCAN_CONTRACT_PROGRESS_LOG'):
            with Path(progress).open('a', encoding='utf-8') as log_stream:
                log_stream.write('Begin actual app ' + command + ' on ' + str(project) + '\n')
        stem = self.scratch / ('observation-' + str(self.serial))
        log, trace = stem.with_suffix('.work'), stem.with_suffix('.io')
        environment = {
            **os.environ,
            'OMP_NUM_THREADS': '1',
            'QT_QPA_PLATFORM': 'offscreen',
            'QSG_RHI_BACKEND': 'null',
            'SCAN_CONTRACT_WORK': str(log),
        }
        environment.pop('QT_QUICK_BACKEND', None)
        environment.pop('EDI_C08_NATIVE_OBSERVER_LOG', None)
        environment.pop('EDI_C08_NATIVE_OBSERVER_ACTIVE', None)
        if observe:
            environment.update({
                self.preload: str(self.library),
                'EDI_C08_NATIVE_OBSERVER_LOG': str(trace),
                'EDI_C08_NATIVE_OBSERVER_ACTIVE': '1',
            })
            if sys.platform == 'darwin':
                environment['DYLD_FORCE_FLAT_NAMESPACE'] = '1'
        with stem.with_suffix('.stderr').open('w', encoding='utf-8') as error_log:
            result = subprocess.run(
                [str(self.executable), command, str(project), *map(str, arguments)],
                env=environment,
                text=True,
                check=False,
                stdout=subprocess.PIPE,
                stderr=error_log,
                timeout=deadline,
            )
        if result.returncode:
            raise RuntimeError(
                'Scan execution: actual host failed: ' + stem.with_suffix('.stderr').read_text()
            )
        answer = json.loads(result.stdout.strip().splitlines()[-1])
        answer['work'] = work_rows(log)
        answer['trace'] = trace.read_text().splitlines() if trace.exists() else []
        return answer


def scale_project(harness, destination, count):
    project = copy_project(SMALL, destination, iterations=1)
    experiment = project / 'experiments/d20.edi'
    text = experiment.read_text()
    prefix = text[: text.index('loop_\n_data.two_theta')]
    grid = [(8.125 + 0.125 * index, 4.5 + index / 10, 1.7) for index in range(11)]
    text = prefix + 'loop_\n_data.two_theta\n_data.intensity_meas\n_data.intensity_meas_su\n'
    text += ''.join(f'{x} {y} {su}\n' for x, y, su in grid)
    experiment.write_text(text)
    prepared = harness.invoke('prepare-scale', project)
    if not prepared.get('prepared'):
        raise RuntimeError('Scale: a real one-variable fit must be prepared: ' + str(prepared))
    scan = project / 'experiments/d20_scan'
    for path in scan.glob('*.dat'):
        path.unlink()
    payload = 'TEMP 137.25\n' + ''.join(f'{x} {y} {su}\n' for x, y, su in grid)
    for index in range(count):
        if index % 10000 == 0:
            seed = project / f'synthetic-{index // 10000}.dat'
            seed.write_text(payload)
        os.link(seed, scan / f'{index:06d}.dat')
    return project


def projection_csv(project, count):
    # Independent closed form; values and uncertainties vary at non-identity magnitudes.
    header = [
        'file_path',
        'fit_result.success',
        'fit_result.reduced_chi_square',
        'fit_result.iterations',
        'temperature',
        'cosio.cell.length_a',
        'cosio.cell.length_a.uncertainty',
    ]
    with (project / 'analysis/results.csv').open('w', newline='') as stream:
        writer = csv.writer(stream, lineterminator='\n')
        writer.writerow(header)
        for index in range(count):
            value = 10.125 + ((index * 37) % 1001) / 100000
            su = 0.000125 + (index % 7) / 1000000
            writer.writerow([
                f'{index:06d}.dat',
                'True',
                1.125 + index / 100000,
                1,
                137.25,
                value,
                su,
            ])
    return header
