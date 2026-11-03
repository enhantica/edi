"""Compiled-app fixture launches provision their declared cold namespace."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests.fixtures.scan_app import harness as scan
from tests.fixtures.scan_screen import harness as screen
from tests.fixtures.thread_selector import harness as selector
from tests.integration.py.test_app_build_cache import (
    check_delivered_snapshot,
    namespace,  # noqa: F401 - shared fixture
)

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize('entry', ['selector', 'browser-toolchain', 'scan-host'])
def test_compiled_app_launch_provisions_an_absent_app_prefix(entry, tmp_path, monkeypatch):
    cold_root = tmp_path / 'runner'
    (cold_root / '.pixi/envs/default').mkdir(parents=True)
    modules = {'selector': selector, 'screen': screen, 'scan-host': scan}
    module = modules.get(entry, screen)
    monkeypatch.setattr(module, 'ROOT', cold_root)
    for key in (
        'EDI_THREAD_SELECTOR_DESKTOP_RECEIPT',
        'EDI_SCAN_SCREEN_DESKTOP_RECEIPT',
        'EDI_SCAN_APP_PROBE_RECEIPT',
        'EDI_SCAN_APP_GUI_SOURCE',
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(module, 'crysta_reference_prefix', lambda: tmp_path / 'sdk')
    monkeypatch.setattr(module, 'crysta_reference_source', lambda: tmp_path / 'source')
    if entry in {'selector', 'screen'}:
        monkeypatch.setattr(module, 'build_receipt', lambda *_args: _args[-1]())
    original_run = subprocess.run
    records = []

    class ProvisioningObservedError(Exception):
        pass

    def dispatch(command, **kwargs):
        result = original_run(
            [
                sys.executable,
                str(ROOT / 'tests/fixtures/app_environment/pixi_transport.py'),
                str(cold_root),
                *command[1:],
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, (
            'fixture launches provision the cold app prefix before native or wasm work: '
            + result.stderr
        )
        assert Path(kwargs['cwd']) == cold_root, (
            'fixture app provisioning must use the actual tested workspace'
        )
        records.append(json.loads(result.stdout))
        raise ProvisioningObservedError

    monkeypatch.setattr(module.subprocess, 'run', dispatch)

    def launch():
        if entry == 'browser-toolchain':
            module.prepare_browser_toolchain({'EDI_WASM_TOOLCHAIN': str(tmp_path / 'missing')})
        elif entry == 'scan-host':
            module.Harness(tmp_path / 'scratch')
        else:
            module.observation('desktop', tmp_path / 'scratch')

    with pytest.raises(ProvisioningObservedError):
        launch()
    assert records == [
        {
            'kind': 'transport-only',
            'environment': 'app',
            'prefix': str(cold_root / '.pixi/envs/app'),
        }
    ], 'an existing default prefix cannot impersonate the compiled app environment'


def test_browser_live_progress_refuses_terminal_only_and_idle_reports():
    run = subprocess.run(
        ['node', str(ROOT / 'tests/system/manual/web_fit_progress_controls.mjs')],
        capture_output=True,
        text=True,
        check=False,
        timeout=5,
    )
    assert run.returncode == 0, (
        'the progress observer reaches intermediate-count and state refusals: '
        + run.stdout
        + run.stderr
    )


def test_normal_screen_capture_provisions_an_absent_app_prefix(namespace, tmp_path, monkeypatch):  # noqa: F811
    root, sdk, source, _fixture = namespace
    (root / '.pixi/envs/default').mkdir(parents=True)
    monkeypatch.setattr(screen, 'ROOT', root)
    monkeypatch.setattr(screen, 'crysta_reference_prefix', lambda: sdk)
    monkeypatch.setattr(screen, 'crysta_reference_source', lambda: source)
    monkeypatch.delenv('EDI_SCAN_SCREEN_DESKTOP_RECEIPT', raising=False)
    original_run = subprocess.run
    records = []

    class ProvisioningObservedError(Exception):
        pass

    def dispatch(command, **kwargs):
        if command[0] != 'pixi':
            return original_run(command, **kwargs)
        plan = json.loads(Path(command[-1]).read_text(encoding='utf-8'))
        assert plan['executable'] == receipt['executable'], (
            'desktop capture launches its checked delivered-app snapshot without a fixture build'
        )
        result = original_run(
            [
                sys.executable,
                str(ROOT / 'tests/fixtures/app_environment/pixi_transport.py'),
                str(root),
                *command[1:],
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0 and Path(kwargs['cwd']) == root, (
            'the delivered screen app capture provisions its cold app prefix: ' + result.stderr
        )
        records.append(json.loads(result.stdout))
        raise ProvisioningObservedError

    monkeypatch.setattr(screen.subprocess, 'run', dispatch)
    scratch = tmp_path / 'screen'
    scratch.mkdir()
    path = screen.normal_app.receipt(root, scratch / 'desktop', sdk, source)
    receipt = json.loads(path.read_text(encoding='utf-8'))
    check_delivered_snapshot(receipt, root)
    with pytest.raises(ProvisioningObservedError):
        screen.capture(receipt, scratch, dict(os.environ))
    assert records == [
        {'kind': 'transport-only', 'environment': 'app', 'prefix': str(root / '.pixi/envs/app')}
    ], 'normal-app receipt preparation precedes capture-time app environment provisioning'
