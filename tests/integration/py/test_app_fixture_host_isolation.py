"""Fixture transport controls; these observations are never app or numerical evidence."""

import importlib
import subprocess
from types import SimpleNamespace

import pytest

from tests.fixtures import locked_configure
from tests.fixtures.thread_selector.build import ESCAPES


@pytest.mark.parametrize('owner', ['selector', 'screen', 'receipt-selector', 'receipt-screen'])
@pytest.mark.parametrize('selection', ['desktop', 'browser', 'failed-browser-then-desktop'])
def test_app_fixture_prepares_only_the_requested_host(owner, selection, tmp_path, monkeypatch):
    receipt = owner.startswith('receipt-')
    kind = owner.removeprefix('receipt-')
    module = importlib.import_module(
        'tests.system.py.'
        + {
            'selector': 'test_thread_selector',
            'screen': 'test_scan_screen',
            'receipt-selector': 'test_app_receipt_current_inputs',
            'receipt-screen': 'test_app_receipt_current_inputs',
        }[owner]
    )
    calls = []
    failed = selection == 'failed-browser-then-desktop'
    selected = 'desktop' if failed else selection
    receipt_document = {'transport-only': True}
    receipt_path = tmp_path / 'actual host receipt.json'

    class UnavailableBrowserError(RuntimeError):
        pass

    def observe(backend, _scratch, control=None):
        calls.append((backend, control))
        if failed and backend == 'browser':
            raise UnavailableBrowserError('Transport control: browser prerequisite unavailable')
        if backend != selected:
            raise RuntimeError('Transport control: unrequested host was provisioned')
        return {
            'receipt': receipt_document,
            'receipt_path': str(receipt_path),
            'transport-only': True,
        }

    if receipt:
        for harness in module.HOSTS.values():
            monkeypatch.setattr(harness, 'observation', observe)
        for prefix in ('EDI_THREAD_SELECTOR_', 'EDI_SCAN_SCREEN_'):
            for backend in ('DESKTOP', 'BROWSER'):
                monkeypatch.delenv(prefix + backend + '_RECEIPT', raising=False)
        fixture = module.compiled_hosts
    else:
        monkeypatch.setattr(module, 'observation', observe)
        fixture = module.selectors if kind == 'selector' else module.screens

    observations = fixture.__wrapped__(SimpleNamespace(mktemp=lambda _name: tmp_path))
    assert not calls, 'creating a shared app fixture must not provision any host'
    if failed:
        key = (kind, 'browser') if receipt else 'browser'
        for _attempt in range(2):
            with pytest.raises(UnavailableBrowserError):
                observations[key]
        assert key not in observations, (
            'an unavailable host must not leave a cached successful observation'
        )
    key = (kind, selected) if receipt else selected
    if owner == 'screen':
        assert (
            all(
                getattr(module, name)._fixture_function_marker.scope == 'module'
                and not getattr(module, name)._fixture_function_marker.autouse
                for name in ('desktop_screen_capture', 'browser_screen_capture')
            )
            and module.prepare_screen_capture._fixture_function_marker.scope == 'function'
            and module.prepare_screen_capture._fixture_function_marker.autouse
        ), 'Selected screen captures use module setup through automatic per-gate preparation'
        prepared = []

        def prepare(name):
            prepared.append(name)
            fixture = {
                'desktop_screen_capture': module.desktop_screen_capture,
                'browser_screen_capture': module.browser_screen_capture,
            }[name]
            return fixture.__wrapped__(observations)

        module.prepare_screen_capture.__wrapped__(
            SimpleNamespace(
                node=SimpleNamespace(callspec=SimpleNamespace(params={'backend': selected})),
                getfixturevalue=prepare,
            )
        )
        assert prepared == [selected + '_screen_capture'] and key in observations, (
            'Screen setup requests only its selected backend module fixture'
        )
    first = observations[key]
    if receipt:
        assert first == (receipt_document, receipt_path), (
            'compiled receipt fixtures preserve the observed document and its actual path'
        )
    assert observations[key] is first, (
        'repeated gates reuse the actual completed observation for their selected host'
    )
    controls = [None, *ESCAPES] if owner == 'selector' else [None]
    expected = [('browser', None)] * 2 if failed else []
    expected += [(selected, control) for control in controls]
    assert calls == expected, (
        'desktop, browser and failed-browser recovery reach only requested host controls'
    )


@pytest.mark.parametrize('system', [True, False], ids=['system-present', 'system-absent'])
@pytest.mark.parametrize('selection', ['core', 'app', 'explicit-app'])
def test_configure_fixture_passes_the_provisioned_sdk(system, selection, tmp_path, monkeypatch):
    root = tmp_path / 'runner'
    (root / 'core').mkdir(parents=True)
    (root / 'core/CMakeLists.txt').touch()
    prefix = tmp_path / 'locked app prefix'
    monkeypatch.setenv('CONDA_PREFIX', str(prefix))
    monkeypatch.delenv('CRYSTA_SDK_DIR', raising=False)
    sdk = root / 'build/crysta-prefix'
    if selection == 'explicit-app':
        sdk = tmp_path / 'explicit sdk prefix'
        monkeypatch.setenv('CRYSTA_SDK_DIR', str(sdk))
    monkeypatch.setattr(locked_configure, 'system_eigen', lambda *_args: tmp_path / 'external')
    monkeypatch.setattr(locked_configure, 'macos_sdk', lambda: tmp_path / 'platform sdk')
    commands = []

    def dispatch(command, **_kwargs):
        commands.append(command)
        (tmp_path / 'configure/CMakeCache.txt').touch()
        return subprocess.CompletedProcess(command, 0, '', '')

    monkeypatch.setattr(locked_configure.subprocess, 'run', dispatch)
    extra = [] if selection == 'core' else ['-DEDI_BUILD_APP=ON']
    observed = locked_configure.configure(root, tmp_path / 'configure', system, extra)
    assert observed['sdk'] == sdk.resolve(), (
        'core and app configure share the installed SDK unless explicitly overridden'
    )
    assert '-DCMAKE_PREFIX_PATH=' + str(sdk.resolve()) + ';' + str(prefix) in commands[0], (
        'absent system packages cannot hide the selected SDK from real CMake dispatch'
    )
