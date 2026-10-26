"""Content-key and capture transport controls, never scientific or app observations."""

import hashlib
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.fixtures.app_environment import builds
from tests.fixtures.app_environment.closure import dependencies, seal_bundle


@pytest.fixture
def namespace(tmp_path, monkeypatch):
    builds.BUILDS.clear()
    builds.CAPTURES.clear()
    monkeypatch.delenv('EDI_APP_BUILD_EVENTS', raising=False)
    roots = [tmp_path / name for name in ('app', 'sdk', 'source', 'observer')]
    root, sdk, source, fixture = roots
    files = {
        root / 'app/main.cpp': 'int main() { return 0; }',
        root / 'core/src/value.cpp': 'void transport_input() {}',
        root / 'CMakeLists.txt': 'project(transport)',
        root / 'build/app/app/edi_app': 'transport-only delivered normal app',
        sdk / '.crysta-sha': 'a' * 40,
        sdk / 'share/crysta-sdk/manifest.json': json.dumps({'source_sha': 'a' * 40}),
        sdk / 'include/input.hpp': 'void sdk_input();',
        sdk / 'lib/libcrysta_core.a': 'transport-only archive bytes',
        source / 'src/value.cpp': 'void engine_input() {}',
        source / 'CMakeLists.txt': 'project(engine_transport)',
        source / 'pyproject.toml': '[project]',
        fixture / 'observer.cpp': 'void observe_input() {}',
    }
    for path, text in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        if path.name == 'edi_app':
            path.chmod(0o755)
    subprocess.run(['git', 'init', '-q', str(root)], check=True)
    subprocess.run(
        ['git', '-C', str(root), 'add', 'core/src/value.cpp', 'app/main.cpp', 'CMakeLists.txt'],
        check=True,
    )
    subprocess.run(
        [
            'git',
            '-C',
            str(root),
            '-c',
            'user.name=Transport',
            '-c',
            'user.email=transport@example.invalid',
            'commit',
            '-qm',
            'Record transport inputs',
        ],
        check=True,
    )
    head = subprocess.check_output(
        ['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True
    ).strip()
    (root / 'build/app/app/edi_app').write_bytes(
        b'transport-only binary identity; not application evidence\nedi-build-commit:'
        + head.encode()
        + b'\n'
    )
    return roots


@pytest.mark.parametrize(
    'seam',
    [
        'production',
        'sdk-header',
        'sdk-library',
        'sdk-manifest',
        'engine-source',
        'observer',
        'options',
        'source-identity',
        'owner',
        'backend',
    ],
)
def test_cached_app_build_rebuilds_on_each_exact_input_seam(namespace, seam, monkeypatch):
    root, sdk, source, fixture = namespace
    calls = []

    def prepare():
        calls.append(len(calls))
        return fixture / f'transport-receipt-{len(calls)}.json'

    def observe(owner='selector', backend='desktop'):
        return builds.build_receipt(owner, backend, root, sdk, source, fixture, prepare)

    first = observe()
    assert observe() == first and len(calls) == 1, (
        'identical app build inputs prepare one binary per process'
    )
    paths = {
        'production': root / 'core/src/value.cpp',
        'sdk-header': sdk / 'include/input.hpp',
        'sdk-library': sdk / 'lib/libcrysta_core.a',
        'sdk-manifest': sdk / 'share/crysta-sdk/manifest.json',
        'engine-source': source / 'src/value.cpp',
        'observer': fixture / 'observer.cpp',
    }
    if seam in paths:
        path = paths[seam]
        path.write_text(path.read_text() + '\n')
    elif seam == 'options':
        monkeypatch.setenv('CXXFLAGS', '-DTRANSPORT_BUILD_OPTION=17')
    elif seam == 'source-identity':
        subprocess.run(
            [
                'git',
                '-C',
                str(root),
                '-c',
                'user.name=Transport',
                '-c',
                'user.email=transport@example.invalid',
                'commit',
                '--allow-empty',
                '-qm',
                'Change transport source identity',
            ],
            check=True,
        )
    changed = observe(
        'screen' if seam == 'owner' else 'selector', 'browser' if seam == 'backend' else 'desktop'
    )
    assert changed != first and len(calls) == 2, (
        'changed production, SDK, observer, options or backend cannot reuse an old build'
    )


def test_failed_or_mutating_app_build_cannot_cache_success(namespace):
    root, sdk, source, fixture = namespace

    def mutate():
        path = source / 'src/value.cpp'
        path.write_text(path.read_text() + '\n')
        return fixture / 'transport-receipt.json'

    with pytest.raises(RuntimeError, match='inputs changed'):
        builds.build_receipt('selector', 'desktop', root, sdk, source, fixture, mutate)
    assert not builds.BUILDS, 'changed inputs during a build must not publish a cache entry'

    def fail():
        raise RuntimeError('Transport builder failed')

    with pytest.raises(RuntimeError, match='Transport builder failed'):
        builds.build_receipt('selector', 'desktop', root, sdk, source, fixture, fail)
    assert not builds.BUILDS, 'failed build setup must remain retryable without a cached success'


@pytest.mark.usefixtures('namespace')
def test_captured_app_observations_reuse_only_the_same_qualified_binary():
    calls = []
    receipt = {'binary': hashlib.sha256(b'transport binary').hexdigest(), 'backend': 'desktop'}

    def capture():
        calls.append(1)
        return {'transport-only': [17]}

    first = builds.capture_once(receipt, capture)
    first['transport-only'].append(99)
    assert builds.capture_once(receipt, capture) == {'transport-only': [17]} and len(calls) == 1, (
        'gates share a completed host capture without mutating another gate observation'
    )
    receipt['binary'] = hashlib.sha256(b'changed transport binary').hexdigest()
    builds.capture_once(receipt, capture)
    assert len(calls) == 2, 'a different qualified binary must produce its own capture'


def test_real_app_fixtures_build_once_per_owner_and_backend(namespace, monkeypatch):  # noqa: PLR0915
    from tests.fixtures.scan_app.build_probe import fingerprint, sdk_inputs  # noqa: PLC0415
    from tests.fixtures.scan_screen import harness as screen  # noqa: PLC0415
    from tests.fixtures.thread_selector import harness as selector  # noqa: PLC0415
    from tests.fixtures.thread_selector.build import ESCAPES  # noqa: PLC0415
    from tests.system.py import test_app_receipt_current_inputs as receipts  # noqa: PLC0415
    from tests.system.py import test_scan_screen, test_thread_selector  # noqa: PLC0415

    root, sdk, source, _fixture = namespace
    calls = []
    captures = []
    normal_receipts = []
    delivered_receipt = screen.normal_app.receipt

    def reuse_normal_app(*args):
        normal_receipts.append(args[0])
        return delivered_receipt(*args)

    monkeypatch.setattr(screen.normal_app, 'receipt', reuse_normal_app)
    toolchain = root.parent / 'transport-toolkit'
    node = toolchain / 'emsdk-4.0.7/node/transport/bin/node'
    node.parent.mkdir(parents=True)
    node.touch()
    monkeypatch.setenv('EDI_WASM_TOOLCHAIN', str(toolchain))
    for harness in (screen, selector):
        monkeypatch.setattr(harness, 'ROOT', root)
        monkeypatch.setattr(harness, 'crysta_reference_prefix', lambda: sdk)
        monkeypatch.setattr(harness, 'crysta_reference_source', lambda: source)
        monkeypatch.setattr(harness, 'prepare_browser_toolchain', lambda _env: None)
        monkeypatch.setattr(harness, 'pinned_browser', lambda _toolchain: toolchain / 'chrome')
    for name in ('EDI_THREAD_SELECTOR_', 'EDI_SCAN_SCREEN_'):
        for backend in ('DESKTOP', 'BROWSER'):
            monkeypatch.delenv(name + backend + '_RECEIPT', raising=False)

    original_run = subprocess.run

    def build(command, **kwargs):
        if '--output' not in command:
            if str(command[0]) == str(node):
                harness_output = root.parent / command[3]
                harness_output.write_text(json.dumps({'transport-only': 'browser'}))
                return subprocess.CompletedProcess(command, 0)
            if command[0] == 'pixi' and 'scan-screen' in command:
                plan = json.loads((root.parent / command[-1]).read_text())
                (root.parent / plan['output']).write_text(
                    json.dumps({'transport-only': 'desktop'})
                )
                return subprocess.CompletedProcess(command, 0)
            return original_run(command, **kwargs)
        owner = 'selector' if 'tests.fixtures.thread_selector.build' in command else 'screen'
        harness = selector if owner == 'selector' else screen
        output = root.parent / command[command.index('--output') + 1]
        backend = command[command.index('--backend') + 1]
        calls.append((owner, backend))
        executable = output / 'cmake/app/edi_app'
        executable.parent.mkdir(parents=True)
        executable.write_bytes(b'transport-only binary')
        production = fingerprint(root)
        sdk_record = sdk_inputs(sdk, source)
        receipt = {
            'backend': backend,
            'escape': None,
            'source_sha': subprocess.check_output(
                ['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True
            ).strip(),
            'engine_sha': sdk_record['identity'],
            'sdk_manifest': sdk_record['manifest'],
            'production': production,
            'compiled_inputs': {'production': production, 'sdk': sdk_record},
            'fixture': {
                p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                for p in harness.Path(harness.__file__).parent.iterdir()
                if p.is_file()
            },
            'executable': str(executable),
            'binary': hashlib.sha256(executable.read_bytes()).hexdigest(),
        }
        receipt['dependencies'] = dependencies(owner, root)
        if backend == 'browser':
            for name in ('edi_app.html', 'edi_app.js'):
                (executable.parent / name).write_text('transport browser asset')
            seal_bundle(receipt)
        if owner == 'selector':
            captured = output / 'observations.json'
            captured.write_text(
                json.dumps({
                    'receipt': receipt,
                    'controls': {
                        control or 'normal': {'transport-only': control or 'normal'}
                        for control in (None, *ESCAPES)
                    },
                })
            )
            receipt['observations_sha256'] = hashlib.sha256(captured.read_bytes()).hexdigest()
        (output / 'receipt.json').write_text(json.dumps(receipt))
        return subprocess.CompletedProcess(command, 0)

    def capture(receipt, _scratch, _env):
        captures.append(receipt['backend'])
        return {'transport-only': receipt['backend'], 'receipt': receipt}

    monkeypatch.setattr(screen.subprocess, 'run', build)
    monkeypatch.setattr(screen, 'capture', capture, raising=False)

    def scratch(name):
        path = root.parent / name
        path.mkdir()
        return path

    factory = SimpleNamespace(mktemp=scratch)
    selected = test_thread_selector.selectors.__wrapped__(factory)
    drawn = test_scan_screen.screens.__wrapped__(factory)
    hosts = receipts.compiled_hosts.__wrapped__(factory)
    for backend in ('desktop', 'browser'):
        for control in (None, *ESCAPES):
            selected[backend][control]
        drawn[backend]
        for owner in ('selector', 'screen'):
            hosts[owner, backend]
    assert sorted(calls) == [
        ('screen', 'browser'),
        ('selector', 'browser'),
        ('selector', 'desktop'),
    ], 'real fixture dispatch shares three private builds and the delivered desktop screen app'
    assert normal_receipts == [root], (
        'desktop screen fixtures prepare one receipt for the delivered app without compiling it'
    )
    check_delivered_snapshot(drawn['desktop']['receipt'], root)
    assert sorted(captures) == ['browser', 'desktop'], (
        'screen fixtures and receipt controls reuse one completed capture per backend'
    )


def check_delivered_snapshot(receipt, root):
    delivered = root / 'build/app/app/edi_app'
    snapshot = Path(receipt['executable'])
    assert (
        snapshot.parent == delivered.parent
        and snapshot.name.startswith(delivered.name + '.capture-')
        and snapshot.read_bytes() == delivered.read_bytes()
        and receipt['binary'] == hashlib.sha256(delivered.read_bytes()).hexdigest()
    ), 'the desktop screen dispatch binds a checked snapshot of the delivered normal app'
