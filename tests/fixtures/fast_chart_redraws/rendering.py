"""Bounded native captures and Qt's independent renderer observation."""

import atexit
import hashlib
import json
import os
import shutil
import signal
import stat
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
_NATIVE_SNAPSHOTS = {}


def _artifact_identity(info):
    return info.st_ino, info.st_size, info.st_mtime_ns, info.st_mode


def _copy_artifact(source, snapshot, before):
    shutil.copy2(source, snapshot)
    if _artifact_identity(before) != _artifact_identity(source.stat()):
        raise RuntimeError('The native artifact changed while its capture snapshot was copied')
    return hashlib.sha256(snapshot.read_bytes()).hexdigest()


def native_arguments(arguments):
    """Keep one checked native artifact despite a concurrent build relinking it."""
    result = list(map(str, arguments))
    overrides = {os.environ.get('EDI_APP_TEST_RUNNER'), os.environ.get('EDI_APP_BINARY')}
    for index, argument in enumerate(result):
        source = Path(argument)
        if (
            source.name not in {'edi_app_tests', 'edi_app', 'edi_app_tests.exe', 'edi_app.exe'}
            and argument not in overrides
        ):
            continue
        source = source.resolve()
        if source not in _NATIVE_SNAPSHOTS:
            before = source.stat()
            if not stat.S_ISREG(before.st_mode) or (
                os.name != 'nt' and not before.st_mode & 0o111
            ):
                raise RuntimeError(
                    'The native artifact is not a completed executable; a link may be active'
                )
            descriptor, name = tempfile.mkstemp(
                prefix=source.name + '.capture-', dir=source.parent
            )
            os.close(descriptor)
            snapshot = Path(name)
            try:
                digest = _copy_artifact(source, snapshot, before)
            except BaseException:
                snapshot.unlink(missing_ok=True)
                raise
            _NATIVE_SNAPSHOTS[source] = snapshot
            atexit.register(snapshot.unlink, missing_ok=True)
            print('Native artifact ' + source.name + ' sha256=' + digest, flush=True)
        result[index] = str(_NATIVE_SNAPSHOTS[source])
        break
    return result


def capture(arguments, *, env=None, timeout=45):
    command = [
        'bash',
        str(ROOT / 'tests/fixtures/scan_views/run.sh'),
        *native_arguments(arguments),
    ]
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
