"""Run real desktop restarts/browser reloads with private settings and measured engine fills."""

import hashlib
import json
import os
import subprocess
from pathlib import Path

from tests.conftest import crysta_reference_prefix, crysta_reference_source
from tests.fixtures.app_environment.builds import build_receipt
from tests.fixtures.app_environment.closure import validate_bundle, validate_dependencies
from tests.fixtures.scan_app.build_probe import (
    fingerprint,
    validate_current_inputs,
    validate_fixture,
)
from tests.fixtures.scan_screen.harness import pinned_browser, prepare_browser_toolchain

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
COUNTS = (0, 1, 3, 9)


def observation(backend, scratch, escape=None):
    scratch.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    key = 'EDI_THREAD_SELECTOR_' + backend.upper() + '_RECEIPT'
    path = env.get(key)
    if path:
        receipt_path = Path(path)
    else:
        if backend == 'browser':
            prepare_browser_toolchain(env)
        build = scratch / 'build'
        command = [
            'pixi',
            'run',
            '-e',
            'app',
            'python',
            '-m',
            'tests.fixtures.thread_selector.build',
            '--root',
            str(ROOT),
            '--output',
            str(build),
            '--sdk',
            str(crysta_reference_prefix()),
            '--engine-source',
            str(crysta_reference_source()),
            '--backend',
            backend,
        ]

        def prepare():
            subprocess.run(command, cwd=ROOT, env=env, check=True)
            return build / 'receipt.json'

        receipt_path = build_receipt(
            'selector',
            backend,
            ROOT,
            crysta_reference_prefix(),
            crysta_reference_source(),
            HERE,
            prepare,
        )
    receipt = json.loads(receipt_path.read_text())
    validate_current_inputs(receipt, ROOT, crysta_reference_prefix(), crysta_reference_source())
    validate_dependencies(receipt, 'selector', ROOT)
    validate_bundle(receipt)
    if (
        receipt['backend'] != backend
        or receipt['escape'] is not None
        or receipt['production'] != fingerprint(ROOT)
    ):
        raise RuntimeError('Selector gates require the actual committed app and selected control')
    if receipt['engine_sha'] != receipt['sdk_manifest']['source_sha']:
        raise RuntimeError('Selector gates must use the actual linked SDK source revision')
    validate_fixture(receipt, HERE)
    executable = Path(receipt['executable'])
    if hashlib.sha256(executable.read_bytes()).hexdigest() != receipt['binary']:
        raise RuntimeError('Selector gates refuse a replaced observation executable')
    captured = receipt_path.parent / 'observations.json'
    if captured.is_file():
        data = json.loads(captured.read_text())
        original = {key: value for key, value in receipt.items() if key != 'observations_sha256'}
        if data['receipt'] != original or hashlib.sha256(
            captured.read_bytes()
        ).hexdigest() != receipt.get('observations_sha256'):
            raise RuntimeError(
                'Prepared worker observations must bind their actual binary receipt'
            )
        return {
            **data['controls'][escape or 'normal'],
            'receipt': receipt,
            'receipt_path': str(receipt_path),
        }
    result = capture(receipt, scratch, env, escape)
    validate_dependencies(receipt, 'selector', ROOT)
    validate_bundle(receipt)
    result['receipt_path'] = str(receipt_path)
    return result


def capture(receipt, scratch, env, escape=None):
    validate_bundle(receipt)
    executable = Path(receipt['executable'])
    backend = receipt['backend']
    output = scratch / 'result.json'
    if backend == 'browser':
        toolchain = Path(env.get('EDI_WASM_TOOLCHAIN', str(Path.home() / '.cache/edi-wasm')))
        node = next((toolchain / 'emsdk-4.0.7/node').glob('*/bin/node'))
        subprocess.run(
            [
                str(node),
                str(HERE / 'browser.mjs'),
                str(executable.parent),
                str(output),
                str(pinned_browser(toolchain)),
                str(toolchain / 'playwright/node_modules/playwright-core/index.mjs'),
                escape or '',
            ],
            env=env,
            check=True,
            timeout=1300,
        )
    else:
        plan = {
            'executable': str(executable),
            'output': str(output),
            'scratch': str(scratch),
            'escape': escape,
        }
        plan_path = scratch / 'plan.json'
        plan_path.write_text(json.dumps(plan))
        subprocess.run(
            [
                'pixi',
                'run',
                '--as-is',
                '-e',
                'app',
                'bash',
                '-c',
                (
                    'source tools/ci/app-platform.sh; app_capture_platform thread-selector; '
                    'python -m tests.fixtures.thread_selector.harness "$1"'
                ),
                'thread-selector',
                str(plan_path),
            ],
            cwd=ROOT,
            env=env,
            check=True,
            timeout=1300,
        )
    result = json.loads(output.read_text())
    validate_bundle(receipt)
    result['receipt'] = receipt
    return result


def desktop(plan):
    results = {}
    for count in ('3',) if plan.get('escape') else (*COUNTS, 'restore'):
        config = Path(plan['scratch']) / ('machine-' + str(count))
        settings = config / 'EasyScience/EasyDiffraction/settings.ini'
        settings.parent.mkdir(parents=True, exist_ok=True)
        env = dict(
            os.environ,
            XDG_CONFIG_HOME=str(config),
            OMP_NUM_THREADS='2',
            OMP_DYNAMIC='FALSE',
            THREAD_SELECTOR_SETTINGS_FILE=str(settings),
            THREAD_SELECTOR_OUTPUT=plan['output'],
        )

        def invoke(choice, env=env):
            subprocess.run(
                [plan['executable']],
                env=dict(
                    env,
                    THREAD_SELECTOR_COUNT=str(choice),
                    THREAD_SELECTOR_ESCAPE=(plan.get('escape') or '')
                    if choice == 'read' or plan.get('escape') != 'ignored-persistence'
                    else '',
                ),
                check=True,
                timeout=150,
            )
            return json.loads(Path(plan['output']).read_text(encoding='utf-8'))

        results[str(count)] = {'selected': invoke(count), 'reopened': invoke('read')}
    Path(plan['output']).write_text(
        json.dumps({'backend': 'desktop', 'results': results}, indent=2) + '\n', encoding='utf-8'
    )


if __name__ == '__main__':
    import sys

    desktop(json.loads(Path(sys.argv[1]).read_text(encoding='utf-8')))
