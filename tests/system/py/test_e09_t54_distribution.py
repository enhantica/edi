from __future__ import annotations

import email.parser
import subprocess
import sys
import zipfile
from pathlib import Path


def test_e09_t54_built_edi_wheel_has_no_crysta_runtime_dependency(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[3]
    destination = tmp_path / 'dist'
    result = subprocess.run(
        [
            sys.executable,
            '-m',
            'build',
            '--wheel',
            '--no-isolation',
            '--outdir',
            str(destination),
        ],
        cwd=repo_root,
        text=True,
        capture_output=True,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, 'the edi wheel build must complete successfully:\n' + (
        result.stdout + result.stderr
    )
    wheels = list(destination.glob('*.whl'))
    assert len(wheels) == 1, 'the build must produce exactly one edi wheel artifact'
    with zipfile.ZipFile(wheels[0]) as archive:
        metadata_paths = [
            name for name in archive.namelist() if name.endswith('.dist-info/METADATA')
        ]
        assert len(metadata_paths) == 1, (
            'the edi wheel must contain exactly one distribution metadata file'
        )
        metadata = email.parser.Parser().parsestr(archive.read(metadata_paths[0]).decode('utf-8'))
    requirements = metadata.get_all('Requires-Dist', [])
    assert not [value for value in requirements if value.split()[0].casefold() == 'crysta'], (
        'the edi wheel must not declare crysta as a runtime dependency'
    )
