"""Delivery requirements; runtime artifacts belong to the dedicated wasm job.

The native CLI capture is the oracle for wasm numerics. Build-specific browser
runs are separate from this fast delivery gate and the disabled desktop app tier.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tomllib
import zipfile
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / 'tests/fixtures/e04_t11_wasm'


def test_public_webapp_packer_excludes_native_build_outputs(tmp_path):
    root = tmp_path / 'source'
    scripts = root / 'tools/ci'
    scripts.mkdir(parents=True)
    for name in ('wasm-pack.sh', 'wasm-env.sh', 'wasm_import_check.mjs'):
        shutil.copy2(ROOT / 'tools/ci' / name, scripts / name)
    shutil.copytree(ROOT / 'app/web', root / 'app/web')
    for name in ('DEPENDENCIES.md', 'LICENSE', 'COPYING', 'THIRD-PARTY-NOTICES'):
        shutil.copy2(ROOT / name, root / name)
    toolchain = tmp_path / 'toolchain'
    node = toolchain / 'emsdk-4.0.7/node/transport/bin/node'
    node.parent.mkdir(parents=True)
    node.write_text('#!/bin/sh\nexit 0\n')
    node.chmod(0o755)
    # Transport inventory only: the real module/link validator has its own gates.
    native = {'engine.a', 'engine.so', 'engine.dll', 'engine.o', '_edi.pyd'}
    for mode in ('multithread', 'singlethread'):
        app = root / 'build/wasm' / mode / 'app/app'
        app.mkdir(parents=True)
        for name in ('edi_app.js', 'edi_app.wasm', 'qtloader.js', 'CRYSTA_SOURCE_SHA'):
            (app / name).write_bytes(('independent transport ' + mode + name).encode())
        for name in native:
            (app / name).write_bytes(b'private native object transport witness')
    binary = root / 'build/ci/core/engine.a'
    binary.parent.mkdir(parents=True)
    binary.write_bytes(b'private native object transport witness')
    env = {**os.environ, 'EDI_WASM_TOOLCHAIN': str(toolchain)}
    env['PATH'] = str(Path(sys.executable).parent) + os.pathsep + env['PATH']
    run = subprocess.run(
        ['bash', str(scripts / 'wasm-pack.sh')],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=8,
    )
    assert run.returncode == 0, (
        'the actual webapp packer must complete the independent transport inventory: ' + run.stderr
    )
    with zipfile.ZipFile(root / 'build/wasm/edi-webapp.zip') as archive:
        names = archive.namelist()
        assert not any(Path(name).name in native or name.startswith('build/') for name in names), (
            'public webapp packaging must exclude native libraries, objects and build trees'
        )
        assert sum(Path(name).name == 'edi_app.wasm' for name in names) == 2, (
            'excluding native objects must retain both prescribed WebAssembly transport outputs'
        )


def test_native_fixture_is_bound_to_the_committed_nontrivial_project():
    oracle = json.loads((FIXTURE / 'native.json').read_text())
    digest = hashlib.sha256()
    for path in sorted((ROOT / oracle['project']).rglob('*')):
        if path.is_file():
            digest.update(path.relative_to(ROOT / oracle['project']).as_posix().encode() + b'\0')
            digest.update(path.read_bytes())
    assert digest.hexdigest() == oracle['project_sha256'], (
        'numeric oracle must describe the identical committed CLI input project'
    )
    assert oracle['reference'] == 'native CLI, independent of wasm', (
        'numerical values must come from a native CLI run, never the wasm target'
    )
    report = dict(
        line.split('=', 1) for line in (FIXTURE / 'native-report.txt').read_text().splitlines()
    )
    assert report['status'] == oracle['status'] == 'done' and report['converged'] == 'true', (
        'native oracle must have completed and converged'
    )
    assert len(oracle['parameters']) == int(report['n_free']) == 16, (
        'native oracle must include every varied parameter of the LBCO HRPT project'
    )
    assert all(math.isfinite(value) and value != 0.0 for value in oracle['parameters'].values()), (
        'fit parity must exercise finite nonzero parameter values'
    )
    assert oracle['relative_tolerance'] <= 1e-9, (
        'wasm/native fit parity must retain the declared relative tolerance'
    )


def test_toolchain_tasks_declare_reproducible_pins():
    manifest = tomllib.loads((ROOT / 'pixi.toml').read_text())
    tasks = {
        **manifest.get('tasks', {}),
        **{
            key: value
            for feature in manifest.get('feature', {}).values()
            for key, value in feature.get('tasks', {}).items()
        },
    }
    assert {'wasm-toolchain', 'wasm-build'} <= tasks.keys(), (
        'a clean runner must acquire and build both wasm kits through declared pixi tasks'
    )
    text = (ROOT / 'pixi.toml').read_text() + '\n'.join(
        path.read_text() for path in (ROOT / 'tools/ci').glob('*wasm*') if path.is_file()
    )
    assert '4.0.7' in text and '6.11.2' in text, (
        'Qt 6.11.2 and Emscripten exactly 4.0.7 must be declared toolchain pins'
    )
    aqt = [
        feature.get('pypi-dependencies', {}).get('aqtinstall')
        for feature in [manifest, *manifest.get('feature', {}).values()]
    ]
    assert any(value and '3.3.0' in str(value) and '==' in str(value) for value in aqt), (
        'aqtinstall 3.3.0 must be pinned as a pixi dependency'
    )
    assert 'wasm_singlethread' in text and 'wasm_multithread' in text, (
        'toolchain acquisition must cover the independent single- and multi-thread kits'
    )


def test_webassembly_ci_builds_uploads_and_runs_the_browser_gate():
    jobs = [
        (path, job)
        for path in (ROOT / '.github/workflows').glob('*.y*ml')
        for job in (yaml.safe_load(path.read_text()).get('jobs') or {}).values()
        if job.get('name') == 'app · WebAssembly'
    ]
    assert jobs, 'must have a dedicated WebAssembly CI job'
    programs = '\n'.join(
        str(step.get('run', '')) for _, job in jobs for step in job.get('steps', [])
    )
    assert 'wasm-build' in programs, 'CI must build through the same reproducible wasm pixi task'
    assert 'e04_t11' in programs and 'wasm-check' in programs, (
        'dedicated CI must execute the task browser checks; disabled '
        'desktop tests are insufficient'
    )
    assert any(
        'upload-artifact@' in str(step.get('uses', ''))
        for _, job in jobs
        for step in job.get('steps', [])
    ), 'CI must publish the combined static-site artifact'
    checker = (ROOT / 'tools/ci/wasm-check.sh').read_text()
    assert all(
        token in checker
        for token in (
            'export EDI_WASM_ZIP=',
            'export EDI_WASM_CLI_SINGLETHREAD=',
            'export EDI_WASM_CLI_MULTITHREAD=',
            'python -m pytest',
        )
    ), 'dedicated wasm-check must supply the real zip and execute the delivery gates'
    for path, _ in jobs:
        workflow = yaml.safe_load(path.read_text())
        triggers = workflow.get('on', workflow.get(True, {}))
        assert 'workflow_dispatch' in triggers and 'pull_request' in triggers, (
            'the wasm workflow must support both dispatch and PR execution'
        )


def test_web_build_adr_explains_prior_host_threading_and_gpl():
    documents = [
        path.read_text().lower()
        for path in (ROOT / 'docs').rglob('*.md')
        if 'adr' in path.as_posix().lower() and 'wasm' in path.read_text().lower()
    ]
    assert documents, 'must document the web host in an edi ADR'
    text = '\n'.join(documents)
    assert all(
        word in text for word in ('4.0.7', '6.11.2', 'single', 'thread', 'fallback', 'gpl')
    ), 'the web ADR must explain pinned tooling, both thread modes, automatic fallback and GPL'
    assert 'adr-0006' in text or 'adr-0009' in text or 'adr-0015' in text, (
        'the web ADR must identify the prior app host design it extends'
    )


def site_zip():
    explicit = os.environ.get('EDI_WASM_ZIP')
    if not explicit:
        pytest.skip('real zip delivery runs in app · WebAssembly via wasm-check')
    candidates = [Path(explicit)] if explicit else sorted((ROOT / 'build/wasm').glob('*.zip'))
    assert len(candidates) == 1 and candidates[0].is_file(), (
        'delivery requires one combined zip; set EDI_WASM_ZIP to the produced artifact'
    )
    return candidates[0]


def test_zip_contains_two_real_modules_loader_shim_and_licences():
    with zipfile.ZipFile(site_zip()) as archive:
        names = archive.namelist()
        assert len(names) == len(set(names)), (
            'static-site zip must not contain duplicate ambiguous entries'
        )
        assert all(
            not Path(name).is_absolute() and '..' not in Path(name).parts for name in names
        ), 'static-site zip paths must stay inside the published webapp folder'
        wasm = [name for name in names if name.endswith('.wasm')]
        assert len(wasm) >= 2 and len({str(Path(name).parent) for name in wasm}) >= 2, (
            'zip must carry separate single-thread and multithread wasm applications'
        )
        assert all(archive.read(name)[:8] == b'\0asm\x01\0\0\0' for name in wasm), (
            'shipped wasm entries must be actual wasm binaries'
        )
        assert any(Path(name).name == 'index.html' for name in names), (
            'zip must carry an automatic start page'
        )
        assert any(Path(name).name == 'qtloader.js' for name in names), (
            'zip must carry the Qt browser loader'
        )
        assert any(Path(name).name == 'coi-serviceworker.js' for name in names), (
            'header-less GitHub Pages hosting requires the isolation service worker'
        )
        assert any(
            name.lower().endswith('.js')
            and 'qtloader' not in name
            and 'coi-serviceworker' not in name
            for name in names
        ), 'zip must carry the generated application JavaScript'
        licences = [
            name for name in names if re.search(r'licen[cs]e|copying', name, re.IGNORECASE)
        ]
        assert licences and any(
            b'GNU GENERAL PUBLIC LICENSE' in archive.read(name)
            and b'Version 3' in archive.read(name)
            for name in licences
        ), 'distributed GPL-3.0 app must include the actual GPL v3 licence text'
        readmes = [name for name in names if Path(name).name.lower().startswith('readme')]
        assert readmes, 'zip must include its hosting README'
        text = '\n'.join(archive.read(name).decode() for name in readmes).lower()
        assert ('cross-origin' in text or 'coop' in text) and 'single' in text, (
            'hosting README must state isolation requirements and the single-thread fallback'
        )


@pytest.mark.parametrize('mode', ['singlethread', 'multithread'])
def test_each_build_has_browser_runtime_assets(mode):
    with zipfile.ZipFile(site_zip()) as archive:
        names = archive.namelist()
        # No directory spelling is prescribed: identify the build by its explicit thread label.
        selected = [
            name for name in names if mode in name.replace('-', '').replace('_', '').lower()
        ]
        assert any(name.endswith('.wasm') for name in selected), (
            'each thread variant must carry its own real wasm application'
        )
        assert any(name.endswith('.js') for name in selected), (
            'each thread variant must include JavaScript so the start page can launch it'
        )
