"""Review18 F06: execute the consumed SDK's real CLI outside its producer prefix.

Measured accident: build-2ac75018's downloaded CLI cannot find libsleef.so.3.
The positive control supplies the declared consumer libraries; the foreign run
gets neither loader overrides nor the producer's current working directory.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys


def invoke(executable, arguments, cwd, env):
    return subprocess.run(
        [str(executable), *arguments],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=3,
    )


def test_consumed_sdk_cli_runs_from_a_foreign_prefix_without_producer_libraries(tmp_path):
    from conftest import crysta_reference_prefix  # noqa: PLC0415

    prefix = crysta_reference_prefix()
    source = prefix / 'bin/crysta'
    assert source.is_file(), ' review18 F06 the consumed SDK must carry its actual CLI'
    foreign = tmp_path / 'consumer-prefix'
    (foreign / 'bin').mkdir(parents=True)
    cli = foreign / 'bin/crysta'
    shutil.copy2(source, cli)
    runtime = prefix / 'lib/crysta-runtime'
    if runtime.is_dir():
        shutil.copytree(runtime, foreign / 'lib/crysta-runtime', symlinks=False)
    assert cli.read_bytes() == source.read_bytes(), (
        ' I23 relocation must exercise the packaged bytes without patching them'
    )
    clean = {'PATH': '/usr/bin:/bin', 'HOME': str(tmp_path)}
    loader = 'DYLD_LIBRARY_PATH' if sys.platform == 'darwin' else 'LD_LIBRARY_PATH'
    control = invoke(cli, ['--build-commit'], tmp_path, {**clean, loader: sys.prefix + '/lib'})
    assert control.returncode == 0, (
        ' review18 F06 the actual CLI control with declared consumer libraries must run: '
        + control.stderr
    )
    expected = (prefix / '.crysta-sha').read_text().strip()
    assert control.stdout.strip() == expected, (
        ' review18 F06 the executed bytes must identify the SDK linked by this consumer'
    )
    for arguments in (
        ['--build-commit'],
        ['--perf-info'],
        ['fit', '--list-descents', '--version'],
    ):
        result = invoke(cli, arguments, tmp_path, clean)
        assert result.returncode == 0, (
            ' review18 F06 the real relocated CLI must load without producer libraries: '
            + result.stderr
        )
    # Execution alone on the producer machine can accidentally find an absolute
    # RPATH. Inspect the native loader's declaration, independently of sdk.py.
    command = (
        ['otool', '-l', str(cli)] if sys.platform == 'darwin' else ['readelf', '-d', str(cli)]
    )
    inspection = subprocess.run(command, capture_output=True, text=True, check=False, timeout=2)
    assert inspection.returncode == 0, (
        ' review18 F06 native loader declarations must be independently inspectable'
    )
    paths = (
        re.findall(r'cmd LC_RPATH\s+cmdsize \d+\s+path (\S+)', inspection.stdout)
        if sys.platform == 'darwin'
        else re.findall(r'\((?:RPATH|RUNPATH)\).*?\[([^]]*)\]', inspection.stdout)
    )
    assert all(
        part.startswith(('$ORIGIN', '@loader_path', '@executable_path'))
        for value in paths
        for part in value.split(os.pathsep)
    ), ' review18 F06 no absolute producer loader search may make relocation pass locally'
