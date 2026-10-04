"""Process-tree cancellation and the documented Actions per-job temp boundary.

Reference: GitHub Actions variables reference, RUNNER_TEMP: emptied at job start
and end. The fixture removes only its own job directory, never ambient /tmp.
"""

from __future__ import annotations

import os
import select
import shutil
import signal
import subprocess
import sys
from pathlib import Path

from tests.fixtures.e09_t75_commands import assert_no_swallowed_refusal

HOLD = """
def hold():
    marker = Path(os.environ['SCRATCH_OBSERVED'])
    if not marker.exists():
        marker.write_text('external operation reached')
        with open(os.environ['SCRATCH_READY'], 'wb', buffering=0) as ready:
            ready.write(b'READY\\n')
        with open(os.environ['SCRATCH_RELEASE'], 'rb', buffering=0) as release:
            response = release.readline().strip()
        if response == b'fail':
            sys.exit(17)
"""


def observe_tool(path, predicate):
    """Hold only the addressed external operation; retain the original substitute."""
    original = path.with_name(path.name + '.original')
    path.rename(original)
    path.write_text(
        '#!'
        + sys.executable
        + '\nimport os,sys\nfrom pathlib import Path\n'
        + HOLD
        + '\na=sys.argv[1:]\nif '
        + predicate
        + ': hold()\n'
        + 'os.execv('
        + repr(str(original))
        + ', ['
        + repr(str(original))
        + ', *a])\n'
    )
    path.chmod(0o755)


def directories(base, env):
    ambient, job = base / 'ambient-tmp', base / 'runner-job'
    ambient.mkdir()
    job.mkdir()
    env.update(TMPDIR=str(ambient), RUNNER_TEMP=str(job), CI='true')
    return ambient, job


def exercise(command, repo, env, ending, expected=0):
    ambient = Path(env.get('SCRATCH_AMBIENT', env['TMPDIR']))
    job = Path(env['RUNNER_TEMP'])
    ready_path, release_path = job.parent / 'ready.fifo', job.parent / 'release.fifo'
    os.mkfifo(ready_path)
    os.mkfifo(release_path)
    read_fd = os.open(ready_path, os.O_RDWR | os.O_NONBLOCK)
    write_fd = os.open(release_path, os.O_RDWR | os.O_NONBLOCK)
    process = subprocess.Popen(
        command,
        cwd=repo,
        env={
            **env,
            'E09_T75_RECORDS': str(job.parent),
            'SCRATCH_READY_FD': str(read_fd),
            'SCRATCH_READY': str(ready_path),
            'SCRATCH_RELEASE': str(release_path),
            'SCRATCH_OBSERVED': str(job.parent / 'observed'),
        },
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        pass_fds=(read_fd,),
        start_new_session=True,
    )
    try:
        ready, _, _ = select.select([read_fd], [], [], 3)
        if not ready:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
            detail = process.communicate(timeout=2)[0]
            raise AssertionError(
                ' seq44 public scratch operation was not reached: ' + repr(detail)
            )
        assert os.read(read_fd, 100) == b'READY\n', (
            ' seq44 cancellation needs an independently observed operation boundary'
        )
        created = [*ambient.iterdir(), *job.iterdir()]
        assert created, ' seq44 the operation must have actual scratch before cancellation'
        if ending in {'term', 'kill'}:
            os.killpg(process.pid, signal.SIGTERM if ending == 'term' else signal.SIGKILL)
            output = process.communicate(timeout=2)[0]
        else:
            os.write(write_fd, (ending + '\n').encode())
            output = process.communicate((ending + '\n').encode(), timeout=3)[0]
            if ending == 'finish':
                assert process.returncode == expected, (
                    f' seq44 the bounded admitted completion must execute: {output!r}'
                )
            else:
                assert process.returncode != 0, ' seq44 external failure must propagate'
        assert_no_swallowed_refusal(job.parent, ending == 'finish')
        # Independent runner semantics, not cleanup supplied to the product command:
        # the next job starts with only RUNNER_TEMP emptied.
        shutil.rmtree(job)
        job.mkdir()
        assert not list(ambient.iterdir()), (
            ' seq44 job scratch must not survive outside the runner-owned temp: '
            + ', '.join(p.name for p in ambient.iterdir())
        )
    finally:
        os.close(read_fd)
        os.close(write_fd)
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
        process.communicate(timeout=2)
