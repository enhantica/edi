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
