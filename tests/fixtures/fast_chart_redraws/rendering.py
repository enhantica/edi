"""Bounded native captures and Qt's independent renderer observation."""

import json
import os
import signal
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def capture(arguments, *, env=None, timeout=45):
    command = ['bash', str(ROOT / 'tests/fixtures/scan_views/run.sh'), *map(str, arguments)]
    env = dict(os.environ if env is None else env)
    env['XDG_CACHE_HOME'] = str(ROOT / 'build/fast-chart-cache')
    process = subprocess.Popen(
        command,
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    try:
        output, _ = process.communicate(timeout=timeout)
        status = process.returncode
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGTERM)
        try:
            output, _ = process.communicate(timeout=3)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            output, _ = process.communicate()
        status = 124
        output += '\nThe native actor exceeded its bounded process watchdog'
    print('Native renderer capture: ' + str(status) + '\n' + output, flush=True)
    return status, output


def actor(case, *, env=None):
    binary = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    return capture(
        [
            binary,
            '-input',
            ROOT / 'tests/system/app/RenderingSetup.qml',
            '-o',
            '-,txt',
            'RenderingSetup::' + case,
        ],
        env=env,
    )


def qt_reference(output):
    observations = [
        json.loads(line.split('RENDERING_REFERENCE ', 1)[1])
        for line in output.splitlines()
        if 'RENDERING_REFERENCE ' in line
    ]
    if not observations or any(item != observations[0] for item in observations):
        raise ValueError('A renderer reference requires one consistent actual Qt API and renderer')
    return observations[0]
