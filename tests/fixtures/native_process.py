"""Launch fixture scripts with the environment's real interpreter on every host."""

import os
import shlex
import shutil
import sys
import tempfile
from functools import cache
from pathlib import Path

from tools.ci.native_shell import expose


@cache
def environment_bash():
    """Use Git Bash on Windows and validate the selected file through the CI shell helper."""
    if os.name != 'nt':
        candidates = [shutil.which('bash')]
    else:
        git = shutil.which('git')
        root = Path(git).resolve().parent.parent if git else None
        candidates = [os.environ.get('BASH'), os.environ.get('SHELL')]
        if root:
            candidates.extend(str(root / name) for name in ['bin/bash.exe', 'usr/bin/bash.exe'])
        for key in ['ProgramFiles', 'ProgramW6432']:
            if os.environ.get(key):
                candidates.append(str(Path(os.environ[key]) / 'Git/bin/bash.exe'))
    for candidate in filter(None, candidates):
        if os.name == 'nt' and any(
            part.lower() in {'system32', 'sysnative'} for part in Path(candidate).parts
        ):
            continue
        try:
            with tempfile.TemporaryDirectory() as folder:
                return str(expose(str(candidate), Path(folder) / 'path'))
        except (OSError, ValueError):
            continue
    raise RuntimeError(
        'The fixture requires the selected native Bash; WSL is not a Git Bash fallback'
    )


def fixture_program(path):
    """Explicitly interpret an authored script instead of asking Windows to execute its shebang."""
    path = Path(path)
    first = path.read_bytes().split(b'\n', 1)[0].rstrip(b'\r')
    interpreter = (
        sys.executable if first == ('#!' + sys.executable).encode() else environment_bash()
    )
    return [interpreter, path.as_posix()]


def native_executable(path):
    """Locate a declared executable in its native single- or multi-configuration spelling."""
    path = Path(path)
    if os.name != 'nt':
        return path
    if path.suffix.lower() != '.exe':
        path = path.with_name(path.name + '.exe')
    return next((p for p in [path.parent / 'Release' / path.name, path] if p.is_file()), path)


def python_program(path, source):
    """Publish an authored Python spy behind a shell entrypoint Git Bash can execute."""
    path = Path(path)
    program = path.with_name(path.name + '.py')
    program.write_text(source, encoding='utf-8', newline='\n')
    path.write_text(
        '#!/bin/sh\nexec '
        + shlex.quote(Path(sys.executable).as_posix())
        + ' '
        + shlex.quote(program.as_posix())
        + ' "$@"\n',
        encoding='utf-8',
        newline='\n',
    )
    path.chmod(0o755)
    return path


def fixture_shell(directory, command):
    """Put the actual fixture directory first after Bash's own native startup edits."""
    prefix = (
        'fixture_bin="$(cd -- "$1" && pwd -P)"; shift; export PATH="$fixture_bin:$PATH"; hash -r; '
    )
    return [
        environment_bash(),
        '-eu',
        '-c',
        prefix + command,
        'fixture-shell',
        Path(directory).as_posix(),
    ]


def native_static_library(path):
    """Keep the actual consumer archive in its native spelling and configuration."""
    path = Path(path)
    if os.name != 'nt':
        return path
    stem = path.name.removeprefix('lib').removesuffix('.a')
    native = path if path.suffix.casefold() == '.lib' else path.with_name(stem + '.lib')
    return next(
        (p for p in [native, native.parent / 'Release' / native.name] if p.is_file()), native
    )


def fresh_pixi_environment():
    """Let a new Pixi environment supply its own paths without repeating the active prefix."""
    environment = os.environ.copy()
    if os.name != 'nt':
        return environment
    prefix = Path(sys.prefix).resolve()
    kept, seen = [], set()
    for entry in environment.get('PATH', '').split(os.pathsep):
        if not entry:
            continue
        path = Path(entry)
        key = os.path.normcase(os.path.normpath(entry))
        if path.is_relative_to(prefix) or key in seen:
            continue
        seen.add(key)
        kept.append(entry)
    environment['PATH'] = os.pathsep.join(kept)
    return environment
