"""Execute the two real hosts with private machine settings and qualified build receipts."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

from tests.conftest import crysta_reference_prefix, crysta_reference_source
from tests.fixtures.app_environment.builds import build_receipt, capture_once
from tests.fixtures.app_environment.closure import validate_bundle, validate_dependencies
from tests.fixtures.scan_app.build_probe import (
    fingerprint,
    validate_current_inputs,
    validate_fixture,
)
from tests.fixtures.scan_screen import normal_app

ROOT = Path(__file__).resolve().parents[3]
MODES = ('adaptive', 'every', 'second', 'end')


def prepare_browser_toolchain(env):
    toolchain = Path(env.get('EDI_WASM_TOOLCHAIN', str(Path.home() / '.cache/edi-wasm')))
    required = (
        toolchain / 'emsdk-4.0.7/emsdk_env.sh',
        toolchain / 'qt/6.11.2/wasm_multithread/bin/qt-cmake',
        toolchain / 'playwright/node_modules/playwright-core/index.mjs',
        toolchain / 'chrome-146.0.7680.153/.edi-installed',
    )
    if not all(path.exists() for path in required):
        subprocess.run(
            ['pixi', 'run', '-e', 'app', 'wasm-toolchain'],
            cwd=ROOT,
            env=env,
            check=True,
        )


def pinned_browser(toolchain):
    browsers = [
        path
        for path in (toolchain / 'chrome-146.0.7680.153').rglob('chrome-headless-shell')
        if path.is_file()
    ]
    if len(browsers) != 1:
        raise RuntimeError('The screen gate requires one executable from its pinned browser build')
    return browsers[0]


def observation(backend, scratch):
    env = dict(os.environ)
    receipt_path = env.get('EDI_SCAN_SCREEN_' + backend.upper() + '_RECEIPT')
    if receipt_path:
        receipt_path = Path(receipt_path)
    else:
        directory = scratch / backend
        if backend == 'browser':
            prepare_browser_toolchain(env)
        command = [
            'pixi',
            'run',
            '-e',
            'app',
            'python',
            '-m',
            'tests.fixtures.scan_screen.build',
            '--root',
            str(ROOT),
            '--output',
            str(directory),
            '--sdk',
            str(crysta_reference_prefix()),
            '--engine-source',
            str(crysta_reference_source()),
            '--backend',
            backend,
        ]

        def prepare():
            if (
                backend == 'desktop'
            ):  # qualify the delivered binary; never infer its build from HEAD
                return normal_app.receipt(
                    ROOT, directory, crysta_reference_prefix(), crysta_reference_source()
                )
            subprocess.run(command, cwd=ROOT, check=True)
            return directory / 'receipt.json'

        receipt_path = build_receipt(
            'screen',
            backend,
            ROOT,
            crysta_reference_prefix(),
            crysta_reference_source(),
            Path(__file__).parent,
            prepare,
        )
    receipt = json.loads(receipt_path.read_text())
    validate_current_inputs(receipt, ROOT, crysta_reference_prefix(), crysta_reference_source())
    validate_dependencies(receipt, 'screen', ROOT)
    validate_bundle(receipt)
    if receipt['backend'] != backend or receipt['production'] != fingerprint(ROOT):
        raise RuntimeError(
            'A screen gate requires the actual committed app sources on its backend'
        )
    committed_main = subprocess.check_output([
        'git',
        '-C',
        str(ROOT),
        'show',
        receipt['source_sha'] + ':app/main.cpp',
    ])
    if committed_main != (ROOT / 'app/main.cpp').read_bytes():
        raise RuntimeError('The screen receipt must bind the unchanged committed app entry point')
    if receipt['engine_sha'] != receipt['sdk_manifest']['source_sha']:
        raise RuntimeError(
            'The screen receipt must use the published SDK matching its engine source'
        )
    validate_fixture(receipt, Path(__file__).parent)
    executable = Path(receipt['executable'])
    if hashlib.sha256(executable.read_bytes()).hexdigest() != receipt['binary']:
        raise RuntimeError('A screen gate refuses a replaced observation executable')
    if backend == 'desktop':
        normal_app.validate_identity(receipt, ROOT)

    def qualified_capture():
        if backend == 'desktop':
            normal_app.validate_identity(receipt, ROOT)
        result = capture(receipt, scratch, env)
        if backend == 'desktop':
            normal_app.validate_identity(receipt, ROOT)
        validate_dependencies(receipt, 'screen', ROOT)
        validate_bundle(receipt)
        return result

    result = capture_once(receipt, qualified_capture)
    if backend == 'desktop':
        normal_app.validate_identity(receipt, ROOT)
    validate_dependencies(receipt, 'screen', ROOT)
    validate_bundle(receipt)
    result['receipt_path'] = str(receipt_path)
    return result


def capture(receipt, scratch, env):
    validate_bundle(receipt)
    executable = Path(receipt['executable'])
    backend = receipt['backend']
    output = scratch / (backend + '.json')
    if backend == 'browser':
        toolchain = Path(env.get('EDI_WASM_TOOLCHAIN', str(Path.home() / '.cache/edi-wasm')))
        node = next((toolchain / 'emsdk-4.0.7/node').glob('*/bin/node'))
        chrome = pinned_browser(toolchain)
        playwright = toolchain / 'playwright/node_modules/playwright-core/index.mjs'
        subprocess.run(
            [
                str(node),
                str(Path(__file__).with_name('browser.mjs')),
                str(executable.parent),
                str(output),
                str(chrome),
                str(playwright),
            ],
            env=env,
            check=True,
            timeout=700,
        )
        result = json.loads(output.read_text())
    else:
        plan = {'executable': str(executable), 'output': str(output), 'scratch': str(scratch)}
        plan_path = scratch / 'desktop-plan.json'
        plan_path.write_text(json.dumps(plan))
        # Not --as-is: where the app came without its environment (a system job), pixi installs it.
        subprocess.run(
            [
                'pixi',
                'run',
                '-e',
                'app',
                'bash',
                '-c',
                (
                    'source tools/ci/app-platform.sh; app_capture_platform scan-screen; '
                    'export QSG_RENDER_LOOP=basic; '
                    'python -m tests.fixtures.scan_screen.harness "$1"'
                ),
                'scan-screen',
                str(plan_path),
            ],
            cwd=ROOT,
            env=env,
            check=True,
            timeout=700,
        )
        result = json.loads(output.read_text())
    validate_bundle(receipt)
    result['receipt'] = receipt
    return result


def desktop(plan):
    result = {'backend': 'desktop', 'results': {}}
    for mode in MODES:
        config = Path(plan['scratch']) / ('machine-' + mode)
        config.mkdir()
        settings = config / 'EasyScience/EasyDiffraction/settings.ini'
        settings.parent.mkdir(parents=True, exist_ok=True)
        env = dict(
            os.environ,
            XDG_CONFIG_HOME=str(config),
            SCAN_SCREEN_SETTINGS_FILE=str(settings),
            SCAN_SCREEN_OUTPUT=plan['output'],
            EDI_TEST_OBSERVERS='1',
        )

        def invoke(choice, settings_only, env=env):
            env.update(SCAN_SCREEN_MODE=choice, SCAN_SCREEN_SETTINGS_ONLY=str(int(settings_only)))
            command = [plan['executable'], '--test-observer', 'scan-screen']
            subprocess.run(command, env=env, check=True, timeout=150)
            return json.loads(Path(plan['output']).read_text(encoding='utf-8'))

        item = invoke(mode, False)
        item['saved'] = invoke(mode, True)
        item['reopened'] = invoke('read', True)
        result['results'][mode] = item
    Path(plan['output']).write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    import sys

    desktop(json.loads(Path(sys.argv[1]).read_text(encoding='utf-8')))
