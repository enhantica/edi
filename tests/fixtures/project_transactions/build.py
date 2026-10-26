"""Link an observation host to freshly built production app objects, wrapping only browser I/O.

The existing app build must use the selected SDK. No production source is patched.
The receipt binds source, SDK headers/library and all linked local objects.
"""

import argparse
import hashlib
import json
import os
import re
import shlex
import subprocess
from pathlib import Path

from tests.fixtures.scan_app.build_probe import fingerprint


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command, **kwargs):
    return subprocess.check_output(command, text=True, **kwargs)


def build(root, native, output):  # noqa: PLR0914 - source, linker and boundary identities are distinct
    root, native, output = (path.resolve() for path in (root, native, output))
    output.mkdir(parents=True, exist_ok=True)
    prefix = root / '.pixi/envs/app'
    environment = dict(os.environ, PATH=str(prefix / 'bin') + os.pathsep + os.environ['PATH'])
    before = fingerprint(root)
    # A fresh incremental build makes the observed source and linked object relation explicit.
    subprocess.run(
        [
            str(prefix / 'bin/cmake'),
            '--build',
            str(native),
            '--target',
            'edi_app_tests',
            '-j',
            '4',
        ],
        check=True,
        env=environment,
    )
    commands = run([
        str(prefix / 'bin/ninja'),
        '-C',
        str(native),
        '-t',
        'commands',
        'edi_app_tests',
    ])
    tokens = shlex.split(commands.splitlines()[-1])
    tokens = tokens[2:-2]  # Ninja's ': && <link> && :' envelope.
    if not tokens or not tokens[0].endswith('c++'):
        raise RuntimeError('The observer requires the actual native C++ app link command')
    compile_commands = run([
        str(prefix / 'bin/ninja'),
        '-C',
        str(native),
        '-t',
        'commands',
        'app/CMakeFiles/edi_app_module.dir/src/session.cpp.o',
    ])
    compile_args = shlex.split(compile_commands.splitlines()[-1])
    for flag in ('-o', '-c', '-MF', '-MT'):
        if flag in compile_args:
            index = compile_args.index(flag)
            del compile_args[index : index + 2]
    compile_args = [arg for arg in compile_args if arg != '-MD']
    source = Path(__file__).with_name('probe.cpp').resolve()
    observer = output / 'probe.o'
    subprocess.run(
        [*compile_args, '-O0', '-o', str(observer), '-c', str(source)],
        cwd=native,
        env=environment,
        check=True,
    )
    tokens = [arg for arg in tokens if not arg.startswith('-Wl,--dependency-file=')]
    # Retain the real app/plugin/core/resource objects, replacing only the test runner/support.
    tokens = [
        arg
        for arg in tokens
        if not (
            arg.startswith('app/CMakeFiles/edi_app_tests.dir/')
            and not arg.endswith('/edi_app_build_commit.cpp.o')
        )
    ]
    index = tokens.index('-o')
    binary = output / 'probe'
    tokens[index + 1] = str(binary)
    symbols = re.findall(r'__wrap_([^"\n]+)"', source.read_text())
    if len(symbols) != 6 or len(set(symbols)) != 6:
        raise RuntimeError('Every declared browser boundary must be linked exactly once')
    command = [*tokens, str(observer), *(f'-Wl,--wrap={symbol}' for symbol in symbols)]
    subprocess.run(command, cwd=native, env=environment, check=True)
    linked = {
        str((native / token).resolve()): digest((native / token).resolve())
        for token in command
        if token.endswith(('.a', '.o')) and (native / token).is_file()
    }
    if fingerprint(root) != before:
        raise RuntimeError('Production source changed while linking the transaction observer')
    receipt = {
        'production': before,
        'source_sha': run(['git', '-C', str(root), 'rev-parse', 'HEAD']).strip(),
        'tracked_changes': run(['git', '-C', str(root), 'diff', 'HEAD', '--stat']),
        'binary': str(binary),
        'binary_sha256': digest(binary),
        'fixture': {path.name: digest(path) for path in source.parent.iterdir() if path.is_file()},
        'linked': linked,
        'boundary': symbols,
        'limit': 'Native Session with held browser I/O; not a browser UI or OS-picker measurement',
    }
    (output / 'receipt.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument('--native', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    build(args.root, args.native, args.output)
