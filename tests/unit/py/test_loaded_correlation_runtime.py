"""A native probe uses the runtime selected at link time across environment boundaries."""

from types import SimpleNamespace

import pytest

from tests.fixtures.loaded_correlation_cache import build_probe


def test_windows_probe_prepends_the_configured_qt_directory_and_preserves_parent(
    tmp_path, monkeypatch
):
    directory = tmp_path / 'app environment/Library/bin'
    directory.mkdir(parents=True)
    record = tmp_path / 'cmake/qt-runtime-dir.txt'
    record.parent.mkdir()
    record.write_text(str(directory) + '\n', encoding='utf-8')
    parent = {'PATH': 'default-tools;system-tools', 'KEEP': 'unchanged'}
    monkeypatch.setattr(build_probe, 'os', SimpleNamespace(name='nt', environ=parent, pathsep=';'))
    child = build_probe.probe_environment(tmp_path)
    assert child == {
        'PATH': str(directory) + ';default-tools;system-tools',
        'KEEP': 'unchanged',
    }, 'Windows native probes receive their actual linked Qt DLL directory before default paths'
    assert parent == {'PATH': 'default-tools;system-tools', 'KEEP': 'unchanged'}, (
        'Preparing the probe child must preserve every parent environment value'
    )


def test_posix_probe_keeps_the_environment_without_a_windows_runtime_record(tmp_path, monkeypatch):
    parent = {'PATH': '/default/bin', 'KEEP': 'unchanged'}
    monkeypatch.setattr(build_probe, 'os', SimpleNamespace(name='posix', environ=parent))
    child = build_probe.probe_environment(tmp_path)
    assert child == parent and child is not parent, (
        'POSIX probes retain their linked loader configuration without mutating the parent'
    )


@pytest.mark.parametrize('record_kind', ['empty', 'relative', 'missing-directory'])
def test_windows_probe_refuses_an_unusable_configured_runtime(tmp_path, monkeypatch, record_kind):
    value = {
        'empty': '',
        'relative': 'relative/Library/bin',
        'missing-directory': str(tmp_path / 'uninstalled/Library/bin'),
    }[record_kind]
    record = tmp_path / 'cmake/qt-runtime-dir.txt'
    record.parent.mkdir()
    record.write_text(value, encoding='utf-8')
    monkeypatch.setattr(build_probe, 'os', SimpleNamespace(name='nt', environ={}, pathsep=';'))
    with pytest.raises(RuntimeError, match='requires its configured Qt runtime directory'):
        build_probe.probe_environment(tmp_path)
