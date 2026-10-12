"""Compiled-app fixture launches provision their declared cold namespace."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from tests.fixtures.scan_app import harness as scan
from tests.fixtures.scan_screen import harness as screen
from tests.fixtures.thread_selector import harness as selector

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize('entry', ['selector', 'screen', 'browser-toolchain', 'scan-host'])
def test_compiled_app_launch_provisions_an_absent_app_prefix(entry, tmp_path, monkeypatch):
    namespace = tmp_path / 'runner'
    (namespace / '.pixi/envs/default').mkdir(parents=True)
    modules = {'selector': selector, 'screen': screen, 'scan-host': scan}
    module = modules.get(entry, screen)
    monkeypatch.setattr(module, 'ROOT', namespace)
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
                str(namespace),
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
        assert Path(kwargs['cwd']) == namespace, (
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
            'prefix': str(namespace / '.pixi/envs/app'),
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
