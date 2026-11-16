"""Actual configure/cache permissions are system workflows on every native host."""

import subprocess

import pytest

from tests.fixtures.write_access import unwritable_directory
from tests.unit.py.test_e11_t5_runtime_publication import (
    check_real_runtime_configure_reuses_verified_publication_without_stage_copy,
)


@pytest.mark.parametrize(
    ('system', 'dedicated'), [('Linux', False), ('Darwin', False), ('Linux', True)]
)
def test_real_runtime_configure_reuses_verified_publication_without_stage_copy(
    tmp_path, system, dedicated
):
    check_real_runtime_configure_reuses_verified_publication_without_stage_copy(
        tmp_path, system, dedicated
    )


def test_cache_denial_reaches_actual_cmake_file_and_directory_creation_then_restores(tmp_path):
    directory = tmp_path / 'cache with spaces'
    directory.mkdir()
    existing = directory / 'existing'
    existing.write_bytes(b'original readable bytes')
    scripts = []
    for kind, instruction in [('file', 'WRITE'), ('directory', 'MAKE_DIRECTORY')]:
        target = directory / ('new-' + kind)
        script = tmp_path / (kind + '.cmake')
        script.write_text(
            'file('
            + instruction
            + ' [==['
            + target.as_posix()
            + ']==]'
            + (' "new"' if kind == 'file' else '')
            + ')\n',
            encoding='utf-8',
            newline='\n',
        )
        scripts.append((target, script))
    with unwritable_directory(directory):
        assert existing.read_bytes() == b'original readable bytes', (
            'The denied cache retains read access to its complete original publication'
        )
        for target, script in scripts:
            result = subprocess.run(
                ['cmake', '-P', str(script)], capture_output=True, timeout=5, check=False
            )
            assert result.returncode != 0 and not target.exists(), (
                'The real CMake writer cannot create a file or ordinary directory '
                'in the denied cache'
            )
    for target, script in scripts:
        result = subprocess.run(
            ['cmake', '-P', str(script)], capture_output=True, timeout=5, check=False
        )
        assert result.returncode == 0 and target.exists(), (
            'Restoring the original ACL restores the same actual CMake creation operations'
        )
