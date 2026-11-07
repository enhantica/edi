# SPDX-License-Identifier: BSD-3-Clause
"""Exercise Git's actual Windows-style checkout against checksum-bound text."""

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_checkout_preserves_every_committed_byte_with_autocrlf_enabled(tmp_path):
    source, target = tmp_path / 'source', tmp_path / 'checkout'
    source.mkdir()
    subprocess.run(['git', 'init', '-q', str(source)], check=True)
    subprocess.run(['git', '-C', str(source), 'config', 'core.autocrlf', 'false'], check=True)
    (source / '.gitattributes').write_bytes((ROOT / '.gitattributes').read_bytes())
    inputs = {
        'future-skills/new.md': 'A new skill\nCubic Ångström\n'.encode(),
        'records/raw.dat': b'first\r\nsecond\nthird\r\n',
        'assets/opaque.bin': b'\x00\x01raw\r\n',
    }
    for name, content in inputs.items():
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    subprocess.run(['git', '-C', str(source), 'add', '.gitattributes', *inputs], check=True)
    subprocess.run(
        [
            'git',
            '-C',
            str(source),
            '-c',
            'user.name=Checkout Fixture',
            '-c',
            'user.email=fixture@example.invalid',
            '-c',
            'commit.gpgsign=false',
            'commit',
            '-qm',
            'Record byte fixtures',
        ],
        check=True,
    )
    subprocess.run(
        [
            'git',
            '-c',
            'core.autocrlf=true',
            'clone',
            '--quiet',
            '--no-hardlinks',
            str(source),
            str(target),
        ],
        check=True,
    )
    assert {name: (target / name).read_bytes() for name in inputs} == inputs, (
        'Checkout preserves every committed byte with autocrlf enabled.'
    )
