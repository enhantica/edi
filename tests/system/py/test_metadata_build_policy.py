"""A target's executed dependency graph, not its spelling, owns build permission."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from tests.fixtures.fast_ci.policy import app_command, metadata_graph
from tests.fixtures.fast_ci.processes import process_guard

ROOT = Path(__file__).resolve().parents[3]
CMAKE = str(ROOT / '.pixi/envs/app/bin/cmake')
NINJA = str(ROOT / '.pixi/envs/app/bin/ninja')


def graph(tmp_path, target='edi_app'):
    """Declare an independent Ninja closure with one metadata producer."""
    source, build = tmp_path / 'source', tmp_path / 'app'
    source.mkdir()
    build.mkdir()
    script = source / 'producer.cmake'
    shutil.copyfile(ROOT / 'cmake/build_version.cmake', script)
    command = f'{CMAKE} -DSOURCE_DIR={source} -DOUT={build}/version.cpp -P {script}'
    (build / 'CMakeCache.txt').write_text(
        f'CMAKE_MAKE_PROGRAM:FILEPATH={NINJA}\nCMAKE_GENERATOR:INTERNAL=Ninja\n'
        f'CMAKE_PROJECT_NAME:STATIC=metadata\nCMAKE_HOME_DIRECTORY:INTERNAL={source}\n'
    )
    (build / 'build.ninja').write_text(
        'rule produce\n  command = ' + command + '\n'
        'build metadata: produce\n'
        f'build {target}: phony metadata\n'
        'build build.ninja: phony\n'
    )
    return source, build, script


@pytest.mark.parametrize('target', ['edi_app', 'edi_app_module', 'unrelated_metadata'])
@pytest.mark.parametrize('launcher', ['cmake', 'ninja'])
def test_metadata_permission_follows_commands_even_with_an_app_target_name(
    tmp_path, target, launcher
):
    _, build, _ = graph(tmp_path, target)
    command = (
        [CMAKE, '--build', str(build), '--target', target]
        if launcher == 'cmake'
        else [NINJA, '-C', str(build), target]
    )
    assert metadata_graph(command), 'The selected closure contains only reviewed metadata work'
    assert not app_command(command), 'App-like target and folder names do not imply compilation'
    with process_guard(ROOT) as observed:
        result = subprocess.run(command, capture_output=True, text=True, check=False, timeout=5)
    assert result.returncode == 0 and not observed['blocked'], (
        'The process guard permits the proven metadata closure to execute'
    )
    assert (build / 'version.cpp').is_file(), 'The approved graph really runs its producer'


@pytest.mark.parametrize(
    'escape',
    [
        'compiler',
        'transitive-compiler',
        'shell-wrapper',
        'unknown-command',
        'modified-producer',
        'missing-producer',
        'extra-cmake-option',
        'outside-output',
        'empty-graph',
        'missing-graph',
        'unknown-target',
        'pending-regeneration',
    ],
)
def test_metadata_permission_refuses_changed_work_before_building(tmp_path, escape):
    source, build, script = graph(tmp_path)
    ninja_file = build / 'build.ninja'
    text = ninja_file.read_text()
    marker = build / 'must-not-run'
    if escape in {'compiler', 'transitive-compiler', 'shell-wrapper', 'unknown-command'}:
        commands = {
            'compiler': f'c++ {source}/app.cpp -o {marker}',
            'transitive-compiler': f'c++ {source}/app.cpp -o {marker}',
            'shell-wrapper': f'sh -c "touch {marker}"',
            'unknown-command': f'{CMAKE} -E touch {marker}',
        }
        text += f'rule unsafe\n  command = {commands[escape]}\nbuild unsafe: unsafe\n'
        text = text.replace('phony metadata', 'phony metadata unsafe')
        if escape == 'transitive-compiler':
            text = text.replace('phony metadata unsafe', 'phony intermediate')
            text += 'build intermediate: phony metadata unsafe\n'
    elif escape == 'modified-producer':
        script.write_text(script.read_text() + f'\nexecute_process(COMMAND touch {marker})\n')
    elif escape == 'missing-producer':
        script.unlink()
    elif escape == 'extra-cmake-option':
        text = text.replace(' -P ', ' -DCMAKE_PROJECT_INCLUDE=unexpected.cmake -P ')
    elif escape == 'outside-output':
        text = text.replace(f'-DOUT={build}/version.cpp', f'-DOUT={source}/version.cpp')
    elif escape == 'empty-graph':
        text = text.replace('phony metadata', 'phony')
    elif escape == 'unknown-target':
        text = text.replace('build edi_app:', 'build other:')
    elif escape == 'pending-regeneration':
        text = text.replace('build build.ninja: phony', f'build build.ninja: phony {script}')
    ninja_file.write_text(text)
    if escape == 'pending-regeneration':
        stamp = ninja_file.stat().st_mtime_ns + 1_000_000_000
        os.utime(script, ns=(stamp, stamp))
    if escape == 'missing-graph':
        ninja_file.unlink()
    command = [CMAKE, '--build', str(build), '--target', 'edi_app']
    assert not metadata_graph(command), (
        'A changed dependency closure must lose metadata permission before any build runs'
    )
    with (
        process_guard(ROOT) as observed,
        pytest.raises(RuntimeError, match='private app build'),
    ):
        subprocess.run(command, check=False, timeout=5)
    assert observed['blocked'] and not marker.exists(), (
        'Accidentally adding compilation or unknown work is refused before execution'
    )


@pytest.mark.parametrize('launcher', ['cmake', 'ninja'])
def test_an_innocently_named_target_cannot_hide_app_compilation(tmp_path, launcher):
    source, build, _ = graph(tmp_path, 'metadata')
    ninja_file = build / 'build.ninja'
    text = ninja_file.read_text().replace('build metadata: produce', 'build producer: produce')
    text = text.replace('build metadata: phony metadata', 'build metadata: phony producer unsafe')
    text += (
        f'rule compile_app\n  command = c++ {source}/app/main.cpp -o {build}/forbidden\n'
        'build unsafe: compile_app\n'
    )
    ninja_file.write_text(text)
    command = (
        [CMAKE, '--build', str(build), '--target', 'metadata']
        if launcher == 'cmake'
        else [NINJA, '-C', str(build), 'metadata']
    )
    assert app_command(command), (
        'A renamed target still builds the app when its transitive commands compile app sources'
    )
    with process_guard(ROOT) as observed, pytest.raises(RuntimeError, match='private app build'):
        subprocess.run(command, check=False, timeout=5)
    assert observed['blocked'] and not (build / 'forbidden').exists(), (
        'Target renaming never evades the graph-based refusal before compilation'
    )
