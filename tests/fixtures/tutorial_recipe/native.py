"""Bounded real-host observations; one stuck recipe cannot hide another recipe."""

import hashlib
import json
import subprocess
import time
from pathlib import Path

# Existing walker guards after a step: input, polish, advance, fit idle,
# calculation idle, next progress, page incubation and next target lookup.
STEP_GUARD_SECONDS = 2 + 5 + 60 + 15 + 15 + 5 + 5 + 15


def native_records(raw, prefix):
    marker = prefix.encode('ascii') + b' '
    return [
        json.loads(line.partition(marker)[2].decode('utf-8'))
        for line in raw.splitlines()
        if marker in line
    ]


def native_progress(raw):
    complete = raw[: raw.rfind(b'\n') + 1]
    steps = native_records(complete, 'TUTORIAL_REPLAY_STEP')
    if not steps:
        return None, 0
    step = steps[-1]
    if (
        not isinstance(step, dict)
        or not isinstance(step.get('id'), str)
        or type(step.get('step')) is not int
    ):
        raise ValueError('Native recipe progress requires an actual case and integer step')
    signature = step['id'], step['step']
    waits = native_records(complete, 'TUTORIAL_FIT_WAIT')
    if any(not isinstance(row, dict) for row in waits):
        raise ValueError('Native fit progress records must be structured objects')
    matching = [row for row in waits if (row.get('id'), row.get('step')) == signature]
    if not matching:
        return signature, 0
    milliseconds = matching[-1].get('milliseconds')
    if type(milliseconds) is not int or milliseconds < 0:
        raise ValueError('Native fit progress requires its actual nonnegative work guard')
    return signature, milliseconds / 1000


def _watch_native(process, log_path, overall_deadline):
    signature = None
    anchor = time.monotonic()
    deadline = min(overall_deadline, anchor + STEP_GUARD_SECONDS)
    size = -1
    while process.poll() is None:
        if log_path.stat().st_size != size:
            raw = log_path.read_bytes()
            size = len(raw)
            try:
                actual, fit_guard = native_progress(raw)
            except (ValueError, UnicodeDecodeError) as error:
                return {
                    'reason': 'strict native progress transport: ' + str(error),
                    'last_step': signature,
                }
            if actual != signature:
                signature, anchor = actual, time.monotonic()
            deadline = min(overall_deadline, anchor + STEP_GUARD_SECONDS + fit_guard)
        if time.monotonic() >= deadline:
            return {
                'reason': 'native action stopped progressing within its existing guard envelope',
                'last_step': signature,
                'guard': 'overall' if time.monotonic() >= overall_deadline else 'action',
            }
        time.sleep(0.05)
    return {'reason': None, 'last_step': signature}


def run_native_observation(command, folder, env, overall_deadline, *, cwd=None):
    folder.mkdir(parents=True)
    log_path = folder / 'native.log'
    started = time.monotonic()
    record = {
        'command': command,
        'log': str(log_path),
        'reason': None,
        'started_monotonic': started,
        'runner_sha256': hashlib.sha256(Path(command[0]).read_bytes()).hexdigest(),
    }
    if time.monotonic() >= overall_deadline:
        return {**record, 'returncode': None, 'reason': 'original overall 7200 s guard exhausted'}
    with log_path.open('wb') as output:
        process = subprocess.Popen(
            command, cwd=cwd, env=env, stdout=output, stderr=subprocess.STDOUT
        )
        record['pid'] = process.pid
        try:
            record.update(_watch_native(process, log_path, overall_deadline))
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
        record['returncode'] = process.returncode
    record['elapsed_seconds'] = time.monotonic() - started
    raw = log_path.read_bytes()
    failures = [line for line in raw.splitlines() if line.startswith(b'FAIL!')]
    record['first_failure'] = (
        failures[0].decode('utf-8', errors='backslashreplace') if failures else None
    )
    (folder / 'native.exit').write_text(str(process.returncode) + '\n')
    (folder / 'result.json').write_text(json.dumps(record, indent=2) + '\n')
    return record
