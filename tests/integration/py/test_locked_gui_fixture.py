"""GUI prerequisite transport checks; the real consumer still validates the pinned tree."""

import subprocess
from pathlib import Path

import pytest

from tests.fixtures.locked_gui import gui_source


@pytest.fixture
def namespace(tmp_path, monkeypatch):
    root, prefix, scratch = [tmp_path / name for name in ('root', 'prefix', 'acquisition')]
    adapter = root / 'cmake/EdiGuiBase.cmake'
    adapter.parent.mkdir(parents=True)
    adapter.write_text('transport pin/acquisition recipe')
    calls = []

    def acquire(command, **kwargs):
        calls.append(command)
        assert command[0] == str(prefix / 'bin/cmake') and kwargs['check'], (
            'GUI prerequisites use the selected locked CMake and fail on acquisition errors'
        )
        project = Path(command[command.index('-S') + 1])
        assert f'include("{adapter.as_posix()}")' in (project / 'CMakeLists.txt').read_text(), (
            'GUI prerequisites must execute the actual adapter and its archive/tree identity rules'
        )
        build = Path(command[command.index('-B') + 1])
        source = build / '_deps/gui_components-src'
        source.mkdir(parents=True)
        (build / 'selected-source.txt').write_text(str(source))
        return subprocess.CompletedProcess(command, 0, '', '')

    monkeypatch.setattr(subprocess, 'run', acquire)
    return root, prefix, scratch, calls


@pytest.mark.parametrize('selection', ['existing', 'cold', 'changed-recipe'])
def test_locked_gui_acquisition_keeps_selected_source_or_uses_the_actual_pin(namespace, selection):
    root, prefix, scratch, calls = namespace
    if selection == 'existing':
        selected = root / 'build/app/_deps/gui_components-src'
        selected.mkdir(parents=True)
    first = gui_source(root, scratch, prefix)
    if selection == 'existing':
        assert first == selected and not calls, (
            'The real consumer revalidates an existing GUI source without rebuilding'
        )
    else:
        assert first.is_relative_to(scratch) and len(calls) == 1, (
            'Cold app configure acquires only its own pinned GUI prerequisite'
        )
    if selection == 'changed-recipe':
        (root / 'cmake/EdiGuiBase.cmake').write_text('changed transport acquisition recipe')
        assert gui_source(root, scratch, prefix) != first and len(calls) == 2, (
            'A changed GUI acquisition/pin recipe cannot select a stale prerequisite build tree'
        )


@pytest.mark.parametrize('escape', ['outside', 'relative', 'missing', 'failed'])
def test_locked_gui_acquisition_refuses_unqualified_source_results(namespace, escape, monkeypatch):
    root, prefix, scratch, _calls = namespace

    def escape_acquisition(command, **_kwargs):
        if escape == 'failed':
            raise subprocess.CalledProcessError(1, command)
        build = Path(command[command.index('-B') + 1])
        build.mkdir(parents=True)
        selected = root / 'outside'
        selected.mkdir()
        value = (
            str(selected)
            if escape == 'outside'
            else 'relative'
            if escape == 'relative'
            else str(build / 'missing')
        )
        (build / 'selected-source.txt').write_text(value)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(subprocess, 'run', escape_acquisition)
    with pytest.raises((RuntimeError, subprocess.CalledProcessError)):
        gui_source(root, scratch, prefix)
    assert not (root / 'build/app').exists(), (
        'Failed or unqualified prerequisite acquisition cannot manufacture a completed app build'
    )


@pytest.mark.parametrize('selection', ['core', 'cold-app', 'explicit-app'])
def test_locked_consumer_stages_only_a_missing_app_gui_prerequisite(
    namespace, selection, monkeypatch, tmp_path
):
    from tests.fixtures import locked_configure  # noqa: PLC0415

    root, prefix, _scratch, _calls = namespace
    (root / 'core').mkdir()
    (root / 'core/CMakeLists.txt').touch()
    monkeypatch.setenv('CONDA_PREFIX', str(prefix))
    prepared, configured = [], []
    source = root / 'prepared-gui'

    def prepare(*args):
        prepared.append(args)
        return source

    def configure(command, **_kwargs):
        configured.append(command)
        (tmp_path / 'consumer/CMakeCache.txt').touch()
        return subprocess.CompletedProcess(command, 0, '', '')

    monkeypatch.setattr(locked_configure, 'gui_source', prepare)
    monkeypatch.setattr(locked_configure, 'macos_sdk', lambda: tmp_path / 'platform sdk')
    monkeypatch.setattr(subprocess, 'run', configure)
    extra = [] if selection == 'core' else ['-DEDI_BUILD_APP=ON']
    explicit = root / 'explicit-gui'
    if selection == 'explicit-app':
        extra += ['-DFETCHCONTENT_SOURCE_DIR_GUI_COMPONENTS=' + str(explicit)]
    locked_configure.configure(root, tmp_path / 'consumer', system=False, extra=extra)
    assert '-DFETCHCONTENT_FULLY_DISCONNECTED=ON' in configured[0], (
        'The real consumer keeps dependency network fallback disabled after GUI preparation'
    )
    assert len(prepared) == (selection == 'cold-app'), (
        'Only an app without an explicit GUI source requests the dedicated pinned prerequisite'
    )
    selected = [
        arg for arg in configured[0] if arg.startswith('-DFETCHCONTENT_SOURCE_DIR_GUI_COMPONENTS=')
    ]
    expected = (
        []
        if selection == 'core'
        else [
            '-DFETCHCONTENT_SOURCE_DIR_GUI_COMPONENTS='
            + str(source if selection == 'cold-app' else explicit)
        ]
    )
    assert selected == expected, (
        'The consumer retains explicit GUI selection or uses exactly its prepared private source'
    )
