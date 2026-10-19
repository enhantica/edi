"""Capture the bounded stream-split change as regression inputs."""

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
COMMIT = '24e8fd821b61eaf80327c817f5d0a9454172561b'
PATH = 'tools/ci/crysta-source.sh'


def read(ref):
    return subprocess.check_output(['git', '-C', str(ROOT), 'show', ref + ':' + PATH], text=True)


Path(__file__).with_name('accepted-remote-streams.json').write_text(
    json.dumps(
        {
            'role': 'regression pin for the stdout/stderr split; '
            'lookup behavior is tested separately',
            'commit': COMMIT,
            'path': PATH,
            'before': read(COMMIT + '^'),
            'after': read(COMMIT),
        },
        indent=2,
    )
    + '\n'
)
