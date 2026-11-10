"""Link an observation host to real app objects at declared asynchronous and file boundaries.

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


def global_function_symbols(defined, scope, spelling, *, kind='T'):
    """Select the public namespace/name, excluding nested helpers and cold fragments."""
    encoded = ''.join(str(len(part)) + part for part in scope.split('::'))
    prefixes = tuple(
        f'ZN{qualifier}{encoded}{len(spelling)}{spelling}E' for qualifier in ('', 'K')
    )
    return [
        words[-1]
        for line in defined.splitlines()
        if len(words := line.split()) >= 2
        and words[-2] == kind
        and words[-1].lstrip('_').startswith(prefixes)
        and '.' not in words[-1]
    ]


def observed_function_symbols(defined, probe_defined, scope, spelling):
    """Every public overload must have its typed observer counterpart, with no extras."""
    actual = global_function_symbols(defined, scope, spelling)
    expected = global_function_symbols(probe_defined, scope, spelling)
    if not actual or set(actual) != set(expected):
        raise RuntimeError(
            f'Public overloads and typed observer definitions differ: {scope}::{spelling}'
        )
    return actual


def observe_fallible_core(prefix, output, core_observed, probe_defined):
    # Observe fallible read/write/adoption boundaries in copied core objects only.
    # The actual definitions still run before publication; the observer can refuse
    # any attempted call afterwards without damaging the published snapshot files.
    io_names = {}
    for member_name, spellings in (
        (
            'io.cpp.o',
            (
                'load_project',
                'save_project',
                'save_project_as',
                'adopt_saved_values',
                'adopt_saved_project',
            ),
        ),
        ('adapter.cpp.o', ('save_report_settings', 'read_scan_dataset')),
    ):
        io_member = output / member_name
        with io_member.open('wb') as stream:
            subprocess.run(
                [str(prefix / 'bin/llvm-ar'), 'p', str(core_observed), member_name],
                stdout=stream,
                check=True,
            )
        defined = run([str(prefix / 'bin/llvm-nm'), '--defined-only', str(io_member)])
        replacements = {}
        for spelling in spellings:
            matches = observed_function_symbols(defined, probe_defined, 'edi', spelling)
            if len(matches) > 1 and spelling != 'load_project':
                raise RuntimeError(
                    'Every fallible observation must delegate one actual core boundary'
                )
            for symbol in matches:
                role = (
                    '_mode'
                    if spelling == 'load_project' and '15ProjectLoadModeE' in symbol
                    else ''
                )
                alias = (
                    ('_' if sys.platform == 'darwin' else '')
                    + 'transaction_real_'
                    + spelling
                    + role
                )
                if alias in replacements.values():
                    raise RuntimeError(
                        'Public overloads require distinct typed observer delegates'
                    )
                replacements[symbol] = alias
        io_names.update(replacements)
        subprocess.run(
            [
                str(prefix / 'bin/llvm-objcopy'),
                *(f'--redefine-sym={old}={new}' for old, new in replacements.items()),
                str(io_member),
            ],
            check=True,
        )
        subprocess.run(
            [str(prefix / 'bin/llvm-ar'), 'r', str(core_observed), str(io_member)], check=True
        )
    # Redirect only the adapter's undefined native writer call. The actual SDK
    # writer remains untouched and is called unless the authored refusal is armed.
    adapter = output / 'adapter.cpp.o'
    symbols = run([str(prefix / 'bin/llvm-nm'), '--undefined-only', str(adapter)])
    names = [
        line.split()[-1]
        for line in symbols.splitlines()
        if line.split() and line.split()[-1].lstrip('_').startswith('ZN6crysta12save_projectE')
    ]
    if len(names) != 1:
        raise RuntimeError('The write refusal must reach exactly the delegated SDK writer')
    target = ('_' if sys.platform == 'darwin' else '') + 'transaction_native_write'
    subprocess.run(
        [
            str(prefix / 'bin/llvm-objcopy'),
            '--redefine-sym=' + names[0] + '=' + target,
            str(adapter),
        ],
        check=True,
    )
    subprocess.run(
        [str(prefix / 'bin/llvm-ar'), 'r', str(core_observed), str(adapter)], check=True
    )
    io_names[names[0]] = target
    return io_names


def observe_file_writes(prefix, observed, observer):
    """Bind each Qt call to the actual relocation made by its compiled typed delegate."""
    undefined = run([str(prefix / 'bin/llvm-nm'), '--undefined-only', str(observed)])
    actual = set()
    for scope, name in [
        ('QFile', 'open'),
        ('QIODevice', 'write'),
        ('QFile', 'copy'),
        ('QFile', 'rename'),
        ('QDir', 'rename'),
    ]:
        actual.update(global_function_symbols(undefined, scope, name, kind='U'))
    names = {}
    for scope, method, receiver in [
        ('QFile', 'open', 'operation_file_open'),
        ('QFile', 'open', 'operation_file_open_fd'),
        ('QFile', 'open', 'operation_file_open_stream'),
        ('QFile', 'open', 'operation_file_open_permissions'),
        ('QIODevice', 'write', 'operation_file_write_span'),
        ('QIODevice', 'write', 'operation_file_write_array'),
        ('QIODevice', 'write', 'operation_file_write_cstring'),
        ('QFile', 'copy', 'operation_file_copy'),
        ('QFile', 'rename', 'operation_file_rename'),
        ('QFile', 'rename', 'operation_file_rename_static'),
        ('QDir', 'rename', 'operation_dir_rename'),
    ]:
        alias = ('_' if sys.platform == 'darwin' else '') + receiver
        trace = run([
            str(prefix / 'bin/llvm-objdump'),
            '-dr',
            '--disassemble-symbols=' + alias,
            str(observer),
        ])
        prefix_name = f'ZNK?{len(scope)}{scope}{len(method)}{method}E'
        typed = set(re.findall(r'_+' + prefix_name + r'[A-Za-z0-9_]+', trace))
        if len(typed) != 1:
            raise RuntimeError(
                'Each typed file delegate must reference exactly its actual Qt method'
            )
        symbol = next(iter(typed))
        if symbol in actual:
            names[symbol] = alias
    if not actual or set(names) != actual:
        raise RuntimeError('Every app file-call overload requires a complete typed observer')
    subprocess.run(
        [
            str(prefix / 'bin/llvm-objcopy'),
            *(f'--redefine-sym={old}={new}' for old, new in names.items()),
            str(observed),
        ],
        check=True,
    )
    return names


def observe_publication_files(prefix, command, output, observer, native):
    """Redirect the actual filesystem imports in private copies of every static input."""
    names = {}
    for receiver, method in [
        ('publication_copy', 'copy'),
        ('publication_copy_file', 'copy_file'),
        ('publication_rename', 'rename'),
        ('publication_hard_link', 'create_hard_link'),
    ]:
        alias = ('_' if sys.platform == 'darwin' else '') + receiver
        trace = run([
            str(prefix / 'bin/llvm-objdump'),
            '-dr',
            '--disassemble-symbols=' + alias,
            str(observer),
        ])
        typed = set(
            re.findall(
                r'_+ZN[A-Za-z0-9_]*filesystem[A-Za-z0-9_]*'
                + str(len(method))
                + method
                + r'E[A-Za-z0-9_]+',
                trace,
            )
        )
        if len(typed) != 1:
            raise RuntimeError('Every filesystem observer has exactly its compiler-typed delegate')
        names[next(iter(typed))] = alias
    actual = set()
    originals = {}
    result = list(command)
    for index, token in enumerate(command):
        path = Path(token)
        if not path.is_absolute():
            path = native / path
        if path.suffix != '.a':
            continue
        if not path.is_file():
            raise RuntimeError('A static publication input is absent; its imports are unprovable')
        undefined = run([str(prefix / 'bin/llvm-nm'), '--undefined-only', str(path)])
        used = set(
            re.findall(
                r'_+ZN[A-Za-z0-9_]*filesystem[A-Za-z0-9_]*'
                r'(?:4copy|9copy_file|6rename|16create_hard_link)E[A-Za-z0-9_]+',
                undefined,
            )
        )
        actual.update(used)
        if not used:
            continue
        if not used <= names.keys():
            raise RuntimeError('A linked filesystem overload has no typed publication observer')
        selected = output / ('publication-' + str(index) + '-' + path.name)
        shutil.copy2(path, selected)
        originals[str(path)] = digest(path)
        subprocess.run(
            [
                str(prefix / 'bin/llvm-objcopy'),
                *(f'--redefine-sym={old}={names[old]}' for old in sorted(used)),
                str(selected),
            ],
            check=True,
        )
        result[index] = str(selected)
    if not actual or not actual <= names.keys():
        raise RuntimeError('The publication observer reaches the real linked filesystem calls')
    return result, originals, names


def browser_staging_source(root):
    """Compile the real portable serialization statements, injecting only their I/O sink."""
    text = (root / 'app/src/web_storage.cpp').read_text()
    try:
        body = text.split('void WebStorage::write(', 1)[1].split('#else', 1)[0]
        start = body.index('    if (kind == QStringLiteral("zip")')
        end = body.index('    edi_storage_write(', start)
    except (IndexError, ValueError) as error:
        raise RuntimeError(
            'The actual browser serialization boundary requires an observed mapping'
        ) from error
    stage = body[start:end]
    if 'edi_storage_stage(' not in stage or 'queueSerial(' in stage:
        raise RuntimeError(
            'The actual browser staging statements require their complete transport mapping'
        )
    stage = stage.replace('edi_storage_stage(', 'observed_browser_stage(')
    return (
        '// Real serialization statements; only staging and refusal delivery are injected.\n'
        'namespace {\n'
        'Image* browserStage = nullptr;\n'
        'void observed_browser_stage(int, const char* name, const char* data, int size) {\n'
        '    need(browserStage && size >= 0, "The actual serializer stages a bounded payload");\n'
        '    (*browserStage)[QString::fromUtf8(name)] = QByteArray(data, size);\n'
        '}\n'
        'void observe_browser_serialization(const QString& kind, const QString& folder,\n'
        '    bool recovery, Image& staged, QString& error, bool& ready) {\n'
        '    const int job = 0;\n'
        '    auto* previous = browserStage; browserStage = &staged;\n'
        '    struct Reset { Image* previous; ~Reset() { browserStage = previous; } };\n'
        '    Reset reset{previous};\n'
        '    const auto refusal = [](const QString& message) { return message; };\n'
        '    const auto finish = [&](int, const QString& message) {\n'
        '        error = message; ready = false; };\n' + stage + '}\n}\n'
    )


def observe_native_publication(prefix, member):
    """The archive object's atomic no-replace import is observed even inside its helpers."""
    original = 'syscall' if sys.platform == 'linux' else '_renameatx_np'
    alias = 'publication_syscall' if sys.platform == 'linux' else '_publication_renameatx'
    undefined = run([str(prefix / 'bin/llvm-nm'), '--undefined-only', str(member)])
    imports = {line.split()[-1] for line in undefined.splitlines() if line.split()}
    if original not in imports:
        raise RuntimeError('The actual native atomic publication import must be observed')
    subprocess.run(
        [
            str(prefix / 'bin/llvm-objcopy'),
            '--redefine-sym=' + original + '=' + alias,
            str(member),
        ],
        check=True,
    )
    return {original: alias}


def observe_fit_constructor(prefix, observed, probe_defined):
    """Bind the app import to a typed seam delegate; retain the actual constructor."""
    imported = run([str(prefix / 'bin/llvm-nm'), '--undefined-only', str(observed)])
    originals = {
        words[-1]
        for line in imported.splitlines()
        if (words := line.split()) and words[-1].lstrip('_').startswith('ZN3edi6FitJobC1E')
    }
    targets = {
        words[-1]
        for line in probe_defined.splitlines()
        if len(words := line.split()) >= 2
        and words[-2] == 'T'
        and words[-1].lstrip('_').startswith('Z22operation_fit_job_ctor')
        and '.' not in words[-1]
    }
    if len(originals) != 1 or len(targets) != 1:
        raise RuntimeError(
            'Fit observation requires one actual app constructor import and typed delegate'
        )
    original, target = next(iter(originals)), next(iter(targets))
    actual = run([str(prefix / 'bin/llvm-cxxfilt'), original]).strip()
    wrapper = run([str(prefix / 'bin/llvm-cxxfilt'), target]).strip()
    actual_args = actual.partition('(')[2]
    wrapper_args = wrapper.partition('(')[2]
    receiver = 'edi::FitJob*, '
    if not wrapper_args.startswith(receiver) or wrapper_args[len(receiver) :] != actual_args:
        raise RuntimeError(
            'Fit constructor observation refuses a compiler-typed signature mismatch'
        )
    subprocess.run(
        [
            str(prefix / 'bin/llvm-objcopy'),
            '--redefine-sym=' + original + '=' + target,
            str(observed),
        ],
        check=True,
    )
    return {'import': original, 'delegate': target, 'actual': actual, 'typed_delegate': wrapper}


def build(root, native, output, *, frozen_inputs=None):  # noqa: PLR0912, PLR0914, PLR0915 - source, linker and boundary identities are distinct
    root, native, output = (path.resolve() for path in (root, native, output))
    output.mkdir(parents=True, exist_ok=True)
    prefix = Path(os.environ.get('EDI_TRANSACTION_APP_ENV', root / '.pixi/envs/app'))
    environment = dict(os.environ, PATH=str(prefix / 'bin') + os.pathsep + os.environ['PATH'])
    before = fingerprint(root)
    if frozen_inputs is None:
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
    else:
        frozen = json.loads(Path(frozen_inputs).read_text(encoding='utf-8'))
        actual_source = Path(
            re.search(
                r'^CMAKE_HOME_DIRECTORY:[^=]*=(.+)$',
                (native / 'CMakeCache.txt').read_text(encoding='utf-8'),
                re.MULTILINE,
            )[1]
        )
        if frozen['production'] != before or fingerprint(actual_source) != before:
            raise RuntimeError('Frozen app reuse requires its exact compiled production source')
        for name, expected in frozen['artifacts'].items():
            if not Path(name).is_file() or digest(Path(name)) != expected:
                raise RuntimeError('Frozen app reuse refuses changed compiled inputs: ' + name)
        print(
            'Reuse the unchanged independently recorded app/core/SDK inputs; no rebuild',
            flush=True,
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
    if tokens[:2] == [':', '&&'] and tokens[-2:] == ['&&', ':']:
        tokens = tokens[2:-2]
    cache = (native / 'CMakeCache.txt').read_text()
    compiler = re.search(r'^CMAKE_CXX_COMPILER:[^=]*=(.+)$', cache, re.MULTILINE)
    if not tokens or compiler is None or tokens[0] != compiler[1]:
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
    if len(symbols) != 7 or len(set(symbols)) != 7:
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
    adapted = output / 'probe.cpp'
    text = source.read_text()
    for literal in re.findall(r'__asm__\(\s*((?:"[^"]*"\s*)+)\)', text):
        label = ''.join(re.findall(r'"([^"]*)"', literal)).removeprefix('__wrap_')
        text = text.replace(literal, '"' + names[label] + '"')
    adapted.write_text(text)
    browser_stage = output / 'browser_stage.hpp'
    browser_stage.write_text(browser_staging_source(root))
    subprocess.run(
        [*compile_args, '-I', str(source.parent), '-O0', '-o', str(observer), '-c', str(adapted)],
        cwd=native,
        env=environment,
        check=True,
    )
    public_access = output / 'public_access.o'
    subprocess.run(
        [
            *compile_args,
            '-O0',
            '-o',
            str(public_access),
            '-c',
            str(source.with_name('public_access.cpp')),
        ],
        cwd=native,
        env=environment,
        check=True,
    )
    probe_defined = run([str(prefix / 'bin/llvm-nm'), '--defined-only', str(observer)])
    fit_constructor = observe_fit_constructor(prefix, observed, probe_defined)
    # Hold actual collection transports, retaining checked indexing and all receivers.
    fetch_member = output / 'online_fetch.cpp.o'
    with fetch_member.open('wb') as stream:
        subprocess.run(
            [str(prefix / 'bin/llvm-ar'), 'p', str(observed), fetch_member.name],
            stdout=stream,
            check=True,
        )
    defined = run([str(prefix / 'bin/llvm-nm'), '--defined-only', str(fetch_member)])
    fetch_names = {}
    for spelling in ('fetch_from', 'fetch_url'):
        matches = observed_function_symbols(defined, probe_defined, 'edi_app', spelling)
        if len(matches) != 1:
            raise RuntimeError('Every actual collection transport has one typed observer')
        fetch_names[matches[0]] = (
            ('_' if sys.platform == 'darwin' else '') + 'transaction_real_' + spelling
        )
    subprocess.run(
        [
            str(prefix / 'bin/llvm-objcopy'),
            *(f'--redefine-sym={old}={new}' for old, new in fetch_names.items()),
            str(fetch_member),
        ],
        check=True,
    )
    subprocess.run(
        [str(prefix / 'bin/llvm-ar'), 'r', str(observed), str(fetch_member)], check=True
    )
    file_names = observe_file_writes(prefix, observed, observer)
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
    native_names = observe_native_publication(prefix, member)
    defined = run([str(prefix / 'bin/llvm-nm'), '--defined-only', str(member)])
    archive_names = {}
    for scope, spelling, replacement in [
        ('edi', 'write_project_archive', 'transaction_real_archive'),
        ('edi', 'fresh_archive_directory', 'transaction_real_directory'),
        ('edi::detail', 'publish_fresh_project_path', 'transaction_real_publish_fresh'),
        ('edi::detail', 'write_project_archive_fresh', 'transaction_real_fresh_archive'),
        ('edi', 'project_archive_bytes', 'transaction_real_archive_bytes'),
    ]:
        matches = observed_function_symbols(defined, probe_defined, scope, spelling)
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
    io_names = observe_fallible_core(prefix, output, core_observed, probe_defined)
    command = [
        str(observed) if arg == library else str(core_observed) if arg == core_library else arg
        for arg in tokens
    ]
    command.insert(command.index(str(observed)), str(observer))
    command.insert(command.index(str(observed)), str(public_access))
    command, publication_originals, publication_names = observe_publication_files(
        prefix, command, output, observer, native
    )
    subprocess.run(command, cwd=native, env=environment, check=True)
    linked = {
        str((native / token).resolve()): digest((native / token).resolve())
        for token in command
        if token.endswith(('.a', '.o')) and (native / token).is_file()
    }
    linked.update(publication_originals)
    linked[str(browser_stage)] = digest(browser_stage)
    if fingerprint(root) != before:
        raise RuntimeError('Production source changed while linking the transaction observer')
    sdk = Path(re.search(r'^crysta_DIR:[^=]*=(.+)$', cache, re.MULTILINE)[1]).resolve().parents[2]
    receipt = {
        'production': before,
        'frozen_inputs': (
            {'path': str(frozen_inputs), 'sha256': digest(Path(frozen_inputs))}
            if frozen_inputs is not None
            else None
        ),
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
        'native_publication_boundary': native_names,
        'fallible_core_boundary': io_names,
        'operation_fetch_boundary': fetch_names,
        'fit_constructor_boundary': fit_constructor,
        'operation_file_boundary': file_names,
        'publication_file_boundary': publication_names,
        'sdk': {
            str(path): digest(path)
            for parent in ('include', 'share/crysta-sdk')
            for path in (sdk / parent).rglob('*')
            if path.is_file()
        },
        'boundary': symbols,
        'limit': 'Native Session with held I/O/dataset reads and authored file refusals; '
        'not a browser UI or OS-picker measurement',
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
