"""Explicit nightly timing producer; no app or SDK is built by this file."""

import hashlib
import json
import os
import platform
import shutil
import subprocess
import time
from pathlib import Path

from tests.fixtures.fast_ci.processes import stop_observer_tree
from tests.fixtures.scan_pair.protocol import bundle

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / 'docs/user/cli/pd-neut-cwl_cosio-d20_scan-162f/project'
CONTRACT = json.loads(Path(__file__).with_name('interface.json').read_text())


def context():
    head = (
        os.environ.get('GITHUB_SHA')
        or subprocess.check_output(
            ['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True
        ).strip()
    )
    return {
        'run_id': os.environ.get('GITHUB_RUN_ID', 'local'),
        'attempt': os.environ.get('GITHUB_RUN_ATTEMPT', '1'),
        'head': head,
    }


def input_digest(root):
    result = hashlib.sha256()
    for path in sorted(root.rglob('*')):
        if path.is_file():
            result.update(path.relative_to(root).as_posix().encode() + b'\0')
            result.update(path.read_bytes())
    return result.hexdigest()


def environment():
    return {
        'OMP_NUM_THREADS': '1',
        'OMP_WAIT_POLICY': 'passive',
        'OPENBLAS_NUM_THREADS': '1',
        'QT_QPA_PLATFORM': 'cocoa' if platform.system() == 'Darwin' else 'offscreen',
        'QT_QUICK_BACKEND': 'software',
    }


def cycle(binary, receipt, source, destination, host, settings):
    shutil.copytree(source, destination)
    copied_digest = input_digest(destination)
    output = destination.parent / (destination.name + '-demo')
    output.mkdir()
    command = [str(binary), '--demo', str(output), '--demo-only', 'perf-162f']
    started = time.monotonic_ns()
    with (
        (output / 'stdout.log').open('wb') as stdout,
        (output / 'stderr.log').open('wb') as stderr,
    ):
        process = subprocess.Popen(
            ['pixi', 'run', '--as-is', '-e', 'app', *command],
            env={**os.environ, **settings, 'EDI_DEMO_PERF_PROJECT': str(destination)},
            stdout=stdout,
            stderr=stderr,
            start_new_session=True,
        )
        try:
            code = process.wait(timeout=CONTRACT['timeout_seconds'])
        except subprocess.TimeoutExpired:
            stop_observer_tree(process)
            raise
    finished = time.monotonic_ns()
    if code:
        raise ValueError('The shared demo timing scenario refused or failed its actual work')
    return {
        'receipt': receipt,
        'files': sorted(path.name for path in (source / 'experiments/d20_scan').glob('*.dat')),
        'input_sha256': copied_digest,
        'host': host,
        'environment': settings,
        'scenario': 'perf-162f',
        'command': ['--demo', '--demo-only', 'perf-162f'],
        'returncode': code,
        'timings_tsv': (output / 'timings.tsv').read_text(),
        'process_started_ns': started,
        'process_finished_ns': finished,
    }


def test_produce_actual_back_to_back_scan_measurements(tmp_path):
    # This is an explicitly invoked producer outside acceptance-tier collection.
    if os.environ.get('EDI_DEMO_DELAY_MS'):
        raise ValueError('A real paired measurement must exclude the artificial delay control')
    output = Path(os.environ['EDI_SCAN_PAIR_EVIDENCE']).resolve()
    source = tmp_path / 'source'
    subprocess.run(
        [
            os.sys.executable,
            str(Path(__file__).with_name('strip_fit_state.py')),
            str(SOURCE),
            str(source),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    files = sorted(path.name for path in (source / 'experiments/d20_scan').glob('*.dat'))
    if len(files) != CONTRACT['file_count']:
        raise ValueError('The timing producer must preserve the complete 162-file input')
    host = {
        'node': platform.node(),
        'platform': platform.platform(),
        'affinity': sorted(os.sched_getaffinity(0)) if hasattr(os, 'sched_getaffinity') else None,
    }
    settings = environment()
    subjects = {
        name: bundle(os.environ[f'EDI_SCAN_{name.upper()}_BUNDLE'])
        for name in ('baseline', 'candidate')
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    warmups = {}
    for name, (binary, receipt) in subjects.items():
        warmups[name] = cycle(
            binary, receipt, source, tmp_path / ('warmup-' + name), host, settings
        )
    pairs = []
    for index in range(CONTRACT['pairs']):
        order = ['baseline', 'candidate'] if index % 2 == 0 else ['candidate', 'baseline']
        pair = {'order': order}
        for name in order:
            binary, receipt = subjects[name]
            pair[name] = cycle(
                binary, receipt, source, tmp_path / f'pair-{index}-{name}', host, settings
            )
        pairs.append(pair)
    document = {
        'schema': 1,
        'context': context(),
        'host': host,
        'environment': settings,
        'input_sha256': input_digest(source),
        'files': files,
        'warmups': warmups,
        'pairs': pairs,
    }
    temporary = output.with_suffix('.pending')
    temporary.write_text(json.dumps(document, indent=2) + '\n')
    temporary.replace(output)
