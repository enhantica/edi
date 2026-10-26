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
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path
from unittest.mock import patch

from tests.fixtures.scan_app.build_probe import fingerprint


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command, **kwargs):
    return subprocess.check_output(command, text=True, **kwargs)


def build(root, native, output):  # noqa: PLR0914, PLR0915 - source, linker and boundary identities are distinct
    root, native, output = (path.resolve() for path in (root, native, output))
    output.mkdir(parents=True, exist_ok=True)
    prefix = Path(os.environ.get('EDI_TRANSACTION_APP_ENV', root / '.pixi/envs/app'))
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
    symbols = [
        ''.join(re.findall(r'"([^"]*)"', literal)).removeprefix('__wrap_')
        for literal in re.findall(r'__asm__\(\s*((?:"[^"]*"\s*)+)\)', source.read_text())
    ]
    if len(symbols) != 6 or len(set(symbols)) != 6:
        raise RuntimeError('Every declared browser boundary must be linked exactly once')
    library = next(arg for arg in tokens if arg.endswith('/libedi_app_module.a'))
    observed = output / 'libedi_app_observed.a'
    shutil.copy2(native / library, observed)
    names = {symbol: ('_' if sys.platform == 'darwin' else '') + symbol for symbol in symbols}
    reached = set()
    for member in ('web_storage.cpp.o', 'web_files.cpp.o'):
        selected = output / member
        with selected.open('wb') as stream:
            subprocess.run(
                [str(prefix / 'bin/llvm-ar'), 'p', str(observed), member],
                stdout=stream,
                check=True,
            )
        defined = run([str(prefix / 'bin/llvm-nm'), '--defined-only', str(selected)])
        replacements = [
            name
            for name in names.values()
            if name in {line.split()[-1] for line in defined.splitlines() if line.split()}
        ]
        reached.update(replacements)
        subprocess.run(
            [
                str(prefix / 'bin/llvm-objcopy'),
                *(f'--redefine-sym={name}=transaction_real_{name}' for name in replacements),
                str(selected),
            ],
            check=True,
        )
        subprocess.run(
            [str(prefix / 'bin/llvm-ar'), 'r', str(observed), str(selected)], check=True
        )
    if reached != set(names.values()):
        raise RuntimeError('Every boundary must replace an actual compiled method definition')
    core_library = next(arg for arg in tokens if arg.endswith('/libedi_core.a'))
    core_observed = output / 'libedi_core_observed.a'
    shutil.copy2(native / core_library, core_observed)
    member = output / 'project_archive.cpp.o'
    with member.open('wb') as stream:
        subprocess.run(
            [str(prefix / 'bin/llvm-ar'), 'p', str(core_observed), member.name],
            stdout=stream,
            check=True,
        )
    defined = run([str(prefix / 'bin/llvm-nm'), '--defined-only', str(member)])
    archive_names = {}
    for spelling, replacement in [
        ('write_project_archive', 'transaction_real_archive'),
        ('fresh_archive_directory', 'transaction_real_directory'),
    ]:
        matches = [
            line.split()[-1]
            for line in defined.splitlines()
            if len(line.split()) >= 3 and line.split()[-2] == 'T' and spelling in line.split()[-1]
        ]
        if len(matches) != 1:
            raise RuntimeError('Each archive observation delegates exactly one real definition')
        archive_names[matches[0]] = ('_' if sys.platform == 'darwin' else '') + replacement
    subprocess.run(
        [
            str(prefix / 'bin/llvm-objcopy'),
            *(f'--redefine-sym={old}={new}' for old, new in archive_names.items()),
            str(member),
        ],
        check=True,
    )
    subprocess.run([str(prefix / 'bin/llvm-ar'), 'r', str(core_observed), str(member)], check=True)
    adapted = output / 'probe.cpp'
    text = source.read_text()
    for literal in re.findall(r'__asm__\(\s*((?:"[^"]*"\s*)+)\)', text):
        label = ''.join(re.findall(r'"([^"]*)"', literal)).removeprefix('__wrap_')
        text = text.replace(literal, '"' + names[label] + '"')
    adapted.write_text(text)
    subprocess.run(
        [*compile_args, '-O0', '-o', str(observer), '-c', str(adapted)],
        cwd=native,
        env=environment,
        check=True,
    )
    command = [
        str(observed) if arg == library else str(core_observed) if arg == core_library else arg
        for arg in tokens
    ]
    command.insert(command.index(str(observed)), str(observer))
    subprocess.run(command, cwd=native, env=environment, check=True)
    linked = {
        str((native / token).resolve()): digest((native / token).resolve())
        for token in command
        if token.endswith(('.a', '.o')) and (native / token).is_file()
    }
    if fingerprint(root) != before:
        raise RuntimeError('Production source changed while linking the transaction observer')
    sdk = (
        Path(
            re.search(
                r'^crysta_DIR:[^=]*=(.+)$', (native / 'CMakeCache.txt').read_text(), re.MULTILINE
            )[1]
        )
        .resolve()
        .parents[2]
    )
    receipt = {
        'production': before,
        'source_sha': os.environ.get('EDI_TRANSACTION_SOURCE_SHA')
        or run(['git', '-C', str(root), 'rev-parse', 'HEAD']).strip(),
        'tracked_changes': os.environ.get('EDI_TRANSACTION_ARCHIVE_NOTE')
        or run(['git', '-C', str(root), 'diff', 'HEAD', '--stat']),
        'binary': str(binary),
        'binary_sha256': digest(binary),
        'fixture': {path.name: digest(path) for path in source.parent.iterdir() if path.is_file()},
        'linked': linked,
        'original_app_library': {
            'path': str(native / library),
            'sha256': digest(native / library),
        },
        'original_core_library': {
            'path': str(native / core_library),
            'sha256': digest(native / core_library),
        },
        'archive_boundary': archive_names,
        'sdk': {
            str(path): digest(path)
            for parent in ('include', 'share/crysta-sdk')
            for path in (sdk / parent).rglob('*')
            if path.is_file()
        },
        'boundary': symbols,
        'limit': 'Native Session with held browser I/O; not a browser UI or OS-picker measurement',
    }
    (output / 'receipt.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    return receipt


def prepare(root, output, sdk):
    root, output, sdk = (path.resolve() for path in (root, output, sdk))
    source = output / 'source'
    source.mkdir(parents=True)
    archive = output / 'source.tar'
    with archive.open('wb') as stream:
        subprocess.run(['git', '-C', str(root), 'archive', 'HEAD'], stdout=stream, check=True)
    with tarfile.open(archive) as stream:
        stream.extractall(source, filter='data')
    if fingerprint(source) != fingerprint(root):
        raise RuntimeError('Private transaction builds refuse uncommitted production changes')
    fixture = Path(__file__).parent
    shutil.copytree(fixture, source / 'tests/fixtures/project_transactions', dirs_exist_ok=True)
    native = output / 'native'
    prefix = root / '.pixi/envs/app'
    environment = dict(os.environ, PATH=str(prefix / 'bin') + os.pathsep + os.environ['PATH'])
    command = [
        str(prefix / 'bin/cmake'),
        '-S',
        str(source),
        '-B',
        str(native),
        '-G',
        'Ninja',
        '-DCMAKE_BUILD_TYPE=Release',
        '-DEDI_BUILD_APP=ON',
        '-DEDI_BUILD_BINDINGS=OFF',
        '-DCMAKE_PREFIX_PATH=' + str(prefix),
        '-Dcrysta_DIR=' + str(sdk / 'lib/cmake/crysta'),
    ]
    gui = root / 'build/app/_deps/gui_components-src'
    if gui.is_dir():
        command.append('-DFETCHCONTENT_SOURCE_DIR_GUI_COMPONENTS=' + str(gui))
    subprocess.run(command, env=environment, check=True)
    with patch.dict(
        os.environ,
        {
            'EDI_TRANSACTION_APP_ENV': str(prefix),
            'EDI_TRANSACTION_SOURCE_SHA': run([
                'git',
                '-C',
                str(root),
                'rev-parse',
                'HEAD',
            ]).strip(),
            'EDI_TRANSACTION_ARCHIVE_NOTE': 'Committed snapshot; separate observer fixture',
        },
    ):
        return build(source, native, output / 'observer')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument('--native', type=Path)
    parser.add_argument('--sdk', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.native:
        build(args.root, args.native, args.output)
    elif args.sdk:
        prepare(args.root, args.output, args.sdk)
    else:
        parser.error('requires either an existing native build or the pinned SDK')
