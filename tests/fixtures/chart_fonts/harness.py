"""Sealed browser compilation/capture for the shared chart-font witness."""

import hashlib
import json
import os
import subprocess
from pathlib import Path

from tests.conftest import crysta_reference_prefix, crysta_reference_source
from tests.fixtures.app_environment.closure import dependencies, files
from tests.fixtures.chart_fonts.build import ROOT, probe_inputs
from tests.fixtures.scan_app.build_probe import fingerprint, sdk_inputs
from tests.fixtures.scan_screen.harness import pinned_browser, prepare_browser_toolchain


def validate(receipt):
    if receipt.get('backend') != 'browser' or receipt.get('production') != fingerprint(ROOT):
        raise RuntimeError(
            'Chart fonts require the actual current production sources on the browser kit'
        )
    if receipt.get('probes') != probe_inputs(ROOT):
        raise RuntimeError('Chart fonts refuse a changed font witness, input fixture or builder')
    if receipt.get('sdk') != sdk_inputs(crysta_reference_prefix(), crysta_reference_source()):
        raise RuntimeError('Chart fonts require the selected published SDK and matching source')
    if receipt.get('dependencies') != dependencies('chart-fonts', ROOT):
        raise RuntimeError('Chart fonts refuse changed shared GUI and recipe inputs')
    if receipt.get('assets') != files(Path(receipt['site'])):
        raise RuntimeError('Chart fonts refuse a changed served browser asset')


def observe(scratch):
    scratch.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    prepare_browser_toolchain(env)
    if explicit := env.get('EDI_CHART_FONT_BROWSER_RECEIPT'):
        path = Path(explicit)
    else:
        directory = scratch / 'host'
        subprocess.run(
            [
                'pixi',
                'run',
                '-e',
                'app',
                'python',
                '-m',
                'tests.fixtures.chart_fonts.build',
                '--output',
                str(directory),
                '--sdk',
                str(crysta_reference_prefix()),
                '--engine-source',
                str(crysta_reference_source()),
            ],
            cwd=ROOT,
            check=True,
        )
        path = directory / 'receipt.json'
    receipt = json.loads(path.read_text())
    validate(receipt)
    toolchain = Path(env.get('EDI_WASM_TOOLCHAIN', str(Path.home() / '.cache/edi-wasm')))
    nodes = list((toolchain / 'emsdk-4.0.7/node').glob('*/bin/node'))
    if len(nodes) != 1:
        raise RuntimeError(
            'The font witness requires one pinned browser-toolchain node executable'
        )
    output = scratch / 'fonts.json'
    subprocess.run(
        [
            str(nodes[0]),
            str(Path(__file__).with_name('browser.mjs')),
            receipt['site'],
            str(output),
            str(pinned_browser(toolchain)),
            str(toolchain / 'playwright/node_modules/playwright-core/index.mjs'),
            str(Path(__file__).with_name('cases.json')),
        ],
        cwd=ROOT,
        env=env,
        check=True,
        timeout=150,
    )
    validate(receipt)
    result = json.loads(output.read_text())
    result['receipt'] = str(path)
    result['wasm_sha256'] = hashlib.sha256(
        (Path(receipt['site']) / 'chart_font_tests.wasm').read_bytes()
    ).hexdigest()
    return result
