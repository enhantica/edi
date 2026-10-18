"""Filesystem witnesses authored independently of the output writers."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


def plant(path, selected, alias, parent, target):
    external = path.parent / 'outside'
    external.mkdir()
    if parent == 'linked':
        relocated = external / selected.parent.name
        shutil.move(selected.parent, relocated)
        selected.parent.symlink_to(relocated, target_is_directory=True)
    selected.parent.mkdir(exist_ok=True)
    if not selected.exists():
        selected.write_bytes(b'previous published bytes\n')
    sentinel = external / 'sentinel'
    sentinel.write_bytes(b'independent outside bytes\n')
    temporary = (
        path / ('.' + selected.name + '.tmp')
        if parent == 'linked'
        else selected.with_name(selected.name + '.tmp')
    )
    temporary.unlink(missing_ok=True)
    reference = selected if target == 'published' else sentinel
    if alias == 'none':
        return external, temporary
    if alias == 'hard':
        os.link(reference, temporary)
    else:
        temporary.symlink_to(reference)
    return external, temporary


@pytest.fixture(scope='module')
def alias_failure(tmp_path_factory):
    folder = tmp_path_factory.mktemp('temporary-rename-failure')
    library = folder / 'failure.so'
    compiler = shutil.which('cc')
    assert compiler, 'The boundary witness requires the pinned native C compiler'
    result = subprocess.run(
        [
            compiler,
            '-shared',
            '-fPIC',
            str(ROOT / 'tests/fixtures/report_storage/temporary_failure.c'),
            '-o',
            str(library),
            *([] if sys.platform == 'darwin' else ['-ldl']),
        ],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, (
        'The independent rename-failure witness compiles: ' + result.stderr
    )
    return library


def environment(library, selected, receipt, failed):
    result = os.environ.copy()
    if failed:
        result['DYLD_INSERT_LIBRARIES' if sys.platform == 'darwin' else 'LD_PRELOAD'] = str(
            library
        )
        result['TEMPORARY_FAILURE_TARGET'] = str(selected)
        result['TEMPORARY_FAILURE_RECEIPT'] = str(receipt)
    return result
