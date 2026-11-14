"""Run actual pre-project CMake launcher selection and native Ninja executable lookup."""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


def run_lookup(root, source, values, *, windows=True, present=True, definitions=None):
    source_prefix = re.split(r'(?m)^project\s*\(', source, maxsplit=1)[0]
    assert source_prefix != source, (
        'The lookup probe exercises the actual pre-project configuration'
    )
    bindir = Path(sys.executable).parent
    cmake = shutil.which('cmake', path=str(bindir) + os.pathsep + os.environ['PATH'])
    ninja = shutil.which('ninja', path=str(bindir) + os.pathsep + os.environ['PATH'])
    assert cmake, 'The lookup protocol requires the actual locked CMake executable'
    assert ninja, 'The lookup protocol requires the actual locked Ninja executable'
    prefix = root / 'locked prefix with spaces'
    program = prefix / 'Library/bin' / ('ccache.exe' if os.name == 'nt' else 'ccache')
    program.parent.mkdir(parents=True)
    if present:
        carrier = os.environ['COMSPEC'] if os.name == 'nt' else shutil.which('echo')
        assert carrier, 'The executable probe uses an actual native host command'
        shutil.copy2(carrier, program)
    project = root / 'source'
    project.mkdir()
    body = 'project(launcher_lookup NONE)\n'
    arguments = '/c echo launcher-lookup' if os.name == 'nt' else 'launcher-lookup'
    for language in ['C', 'CXX']:
        variable = 'CMAKE_' + language + '_COMPILER_LAUNCHER'
        body += (
            'if(DEFINED ' + variable + ')\n'
            '  set(observed "${' + variable + '}")\nelse()\n'
            '  set(observed "$ENV{' + variable + '}")\nendif()\n'
            'file(WRITE "${CMAKE_BINARY_DIR}/' + language + '.launcher" "${observed}")\n'
            'if(NOT observed STREQUAL "")\n'
            'add_custom_target(lookup_'
            + language
            + ' COMMAND ${observed} '
            + arguments
            + ' VERBATIM)\nendif()\n'
        )
    (project / 'CMakeLists.txt').write_text(
        'set(CMAKE_HOST_WIN32 '
        + ('TRUE' if windows else 'FALSE')
        + ')\n'
        + source_prefix
        + '\n'
        + body,
        encoding='utf-8',
    )
    environment = {
        **os.environ,
        'PATH': str(root / 'empty-path'),
        'CONDA_PREFIX': str(prefix),
        'CMAKE_C_COMPILER_LAUNCHER': values.get('C', ''),
        'CMAKE_CXX_COMPILER_LAUNCHER': values.get('CXX', ''),
    }
    for variable in [
        'CMAKE_PROGRAM_PATH',
        'CMAKE_PREFIX_PATH',
        'CMAKE_GENERATOR_PLATFORM',
        'CMAKE_GENERATOR_TOOLSET',
        'CMAKE_GENERATOR_INSTANCE',
    ]:
        environment.pop(variable, None)
    tree = root / 'tree'
    command = [
        cmake,
        '-G',
        'Ninja',
        '-S',
        str(project),
        '-B',
        str(tree),
        '-DCMAKE_MAKE_PROGRAM=' + ninja,
        '-DCMAKE_FIND_USE_SYSTEM_ENVIRONMENT_PATH=FALSE',
        '-DCMAKE_FIND_USE_CMAKE_SYSTEM_PATH=FALSE',
        '-DCMAKE_FIND_USE_INSTALL_PREFIX=FALSE',
    ]
    command += [
        '-DCMAKE_' + language + '_COMPILER_LAUNCHER=' + value
        for language, value in (definitions or {}).items()
    ]
    configured = subprocess.run(
        command, env=environment, capture_output=True, text=True, check=False, timeout=10
    )
    observed = {
        language: (tree / (language + '.launcher')).read_text()
        for language in ['C', 'CXX']
        if (tree / (language + '.launcher')).is_file()
    }
    return configured, observed, program, tree, ninja, environment


def execute_lookup(result, language):
    _configured, _observed, _program, tree, ninja, environment = result
    return subprocess.run(
        [ninja, '-C', str(tree), 'lookup_' + language],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )


def native_probe_tools():
    search = str(Path(sys.executable).parent) + os.pathsep + os.environ['PATH']
    tools = {name: shutil.which(name, path=search) for name in ['cmake', 'ninja', 'ccache']}
    if tools['ccache'] is None and os.name == 'nt':
        candidate = Path(sys.executable).parent / 'Library/bin/ccache.exe'
        tools['ccache'] = str(candidate) if candidate.is_file() else None
    assert all(tools.values()), 'Native compiler probes require the actual locked build tools'
    return tools


def native_cache_alias(root, cache):
    alias = root / 'native cache prefix with spaces/Library/bin'
    alias.parent.mkdir(parents=True)
    if os.name == 'nt':
        made = subprocess.run(
            [
                os.environ['COMSPEC'],
                '/d',
                '/c',
                'mklink',
                '/J',
                str(alias),
                str(Path(cache).parent),
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        assert made.returncode == 0, 'The cache directory alias retains native DLL dependencies'
    else:
        alias.symlink_to(Path(cache).parent, target_is_directory=True)
    return alias / Path(cache).name


def native_probe_environment(root, languages, program):
    environment = {
        **os.environ,
        'CONDA_PREFIX': str(program.parent.parent.parent),
        'CCACHE_DIR': str(root / 'cache'),
        'CCACHE_LOGFILE': str(root / 'cache.log'),
        'CCACHE_RECACHE': 'true',
    }
    environment.update({
        'CMAKE_' + language + '_COMPILER_LAUNCHER': 'ccache' if language in languages else ''
        for language in ['C', 'CXX']
    })
    for name in [
        'CFLAGS',
        'CXXFLAGS',
        'CPPFLAGS',
        'LDFLAGS',
        'CMAKE_PROGRAM_PATH',
        'CMAKE_PREFIX_PATH',
        'CMAKE_GENERATOR_PLATFORM',
        'CMAKE_GENERATOR_TOOLSET',
        'CMAKE_GENERATOR_INSTANCE',
        'CCACHE_DISABLE',
    ]:
        environment.pop(name, None)
    if os.name == 'nt':
        directories = [
            item
            for item in os.environ['PATH'].split(os.pathsep)
            if not (Path(item) / 'ccache.exe').exists()
        ]
        environment['PATH'] = os.pathsep.join(directories)
        compilers = dict.fromkeys(languages, shutil.which('cl'))
    else:
        directory = root / 'safe-tools'
        directory.mkdir()
        for name in ['as', 'ld', 'ar', 'ranlib', 'strip', 'objdump']:
            tool = shutil.which(name, path=os.defpath)
            if tool:
                (directory / name).symlink_to(tool)
        environment['PATH'] = str(directory)
        compilers = {
            language: shutil.which('cc' if language == 'C' else 'c++', path=os.defpath)
            for language in languages
        }
    assert all(compilers.values()), 'Each enabled language has an actual native compiler'
    assert shutil.which('ccache', path=environment['PATH']) is None, (
        'Compiler children cannot recover a bare cache launcher from the test PATH'
    )
    return environment, compilers


def native_probe_project(root, source, languages):
    declaration = re.search(r'(?m)^project\s*\([^\n]*\)', source)
    assert declaration, 'The native probe retains the actual declared project language boundary'
    project = root / 'source'
    project.mkdir()
    names = []
    combined = len(languages) == 2
    for language in languages:
        name = 'probe.' + ('c' if language == 'C' else 'cpp')
        code = (
            (
                'int probe_c(void) { return 0; }\n'
                if language == 'C'
                else 'extern "C" int probe_c(void); int main() { return probe_c(); }\n'
            )
            if combined
            else 'int main(void) { return 0; }\n'
        )
        (project / name).write_text(code, encoding='utf-8')
        names.append('"${CMAKE_CURRENT_SOURCE_DIR}/' + name + '"')
    # One real child project compiles both languages and links the C/C++ boundary.
    # Separate child configurations repeated the same CMake bootstrap for each language.
    body = (
        'try_compile(NATIVE_OK "${CMAKE_BINARY_DIR}/nested-native" SOURCES '
        + ' '.join(names)
        + ' OUTPUT_VARIABLE NATIVE_OUTPUT)\n'
        'if(NOT NATIVE_OK)\n'
        'message(FATAL_ERROR "Nested native compiler failed: ${NATIVE_OUTPUT}")\nendif()\n'
    )
    for language in languages:
        body += (
            'file(WRITE "${CMAKE_BINARY_DIR}/' + language + '.launcher" '
            '"${CMAKE_' + language + '_COMPILER_LAUNCHER}")\n'
            'file(WRITE "${CMAKE_BINARY_DIR}/' + language + '.environment" '
            '"$ENV{CMAKE_' + language + '_COMPILER_LAUNCHER}")\n'
        )
    (project / 'CMakeLists.txt').write_text(
        'set(CMAKE_HOST_WIN32 TRUE)\n'
        'set(CMAKE_TRY_COMPILE_PLATFORM_VARIABLES USER_PROBE_WITNESS)\n'
        'set(USER_PROBE_WITNESS "retained-toolchain-value")\n'
        + source[: declaration.start()]
        + '\n'
        'set(CMAKE_HOST_WIN32 '
        + ('TRUE' if os.name == 'nt' else 'FALSE')
        + ')\n'
        + declaration[0]
        + '\n'
        + body,
        encoding='utf-8',
    )
    return project


def run_compiler_probe(root, source, languages, selection='default'):
    tools = native_probe_tools()
    program = native_cache_alias(root, tools['ccache'])
    choice = {
        'empty': '',
        'absolute': program.as_posix(),
        'list': program.as_posix() + ';compiler_check=content',
    }.get(selection)
    definitions = {} if choice is None else dict.fromkeys(languages, choice)
    environment, compilers = native_probe_environment(root, languages, program)
    project = native_probe_project(root, source, languages)
    tree = root / 'tree'
    command = [
        tools['cmake'],
        '--debug-trycompile',
        '-G',
        'Ninja',
        '-S',
        str(project),
        '-B',
        str(tree),
        '-DCMAKE_MAKE_PROGRAM=' + tools['ninja'],
    ]
    command += [
        '-DCMAKE_' + language + '_COMPILER=' + compiler for language, compiler in compilers.items()
    ]
    command += [
        '-DCMAKE_' + language + '_COMPILER_LAUNCHER=' + value
        for language, value in definitions.items()
    ]
    configured = subprocess.run(
        command, env=environment, capture_output=True, text=True, check=False, timeout=25
    )
    return configured, tree, program, definitions
