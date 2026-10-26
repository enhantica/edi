"""Real harness/receipt dispatch escape controls; compiler/capture payloads are transport only."""

import hashlib
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.fixtures.app_environment import builds
from tests.fixtures.app_environment.closure import dependencies, seal_bundle
from tests.fixtures.scan_app.build_probe import fingerprint, sdk_inputs
from tests.fixtures.scan_screen import harness as screen
from tests.fixtures.thread_selector import harness as selector
from tests.integration.py.test_app_build_cache import namespace  # noqa: F401 - shared fixture


@pytest.fixture
def dispatch(namespace, monkeypatch):  # noqa: F811 - shared pytest fixture
    root, sdk, source, fixture = namespace
    calls, captures = [], []
    state = SimpleNamespace(root=root, calls=calls, captures=captures, build_hook=None)
    for relative in (
        'tests/fixtures/scan_screen/build.py',
        'tests/fixtures/scan_screen/harness.py',
        'tests/fixtures/scan_app/build_probe.py',
        'tests/fixtures/fast_chart_redraws/rendering.py',
        'tools/ci/app-platform.sh',
        'tests/fixtures/app_environment/closure.py',
        'tests/conftest.py',
    ):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('transport recipe identity')
    (root / screen.normal_app.APP).chmod(0o755)
    (fixture / 'harness.py').write_text('transport owner fixture')
    original_run, delivered_receipt = subprocess.run, screen.normal_app.receipt

    def prepare_normal_app(*args):
        calls.append(('screen', 'desktop'))
        return delivered_receipt(*args)

    monkeypatch.setattr(screen.normal_app, 'receipt', prepare_normal_app)
    monkeypatch.setattr(screen.normal_app, '__file__', str(fixture / 'normal_app.py'))

    def prepare(command, **kwargs):
        if '--output' not in command:
            if command[0] == 'pixi' and 'app-build' in command:
                raise RuntimeError('screen fixture attempted to compile the normal app')
            return original_run(command, **kwargs)
        owner = 'selector' if 'tests.fixtures.thread_selector.build' in command else 'screen'
        backend = command[command.index('--backend') + 1]
        output = Path(command[command.index('--output') + 1])
        calls.append((owner, backend))
        output.mkdir(parents=True, exist_ok=True)
        executable = output / 'site' / ('edi_app.wasm' if backend == 'browser' else 'edi_app')
        executable.parent.mkdir(exist_ok=True)
        executable.write_bytes(b'transport executable')
        if backend == 'browser':
            for name in (
                'edi_app.html',
                'edi_app.js',
                'qtloader.js',
                'worker.js',
                'fonts/font.dat',
            ):
                path = executable.parent / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('transport served asset')
        production, selected = fingerprint(root), sdk_inputs(sdk, source)
        receipt = {
            'backend': backend,
            'escape': None,
            'source_sha': subprocess.check_output(
                ['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True
            ).strip(),
            'production': production,
            'compiled_inputs': {'production': production, 'sdk': selected},
            'engine_sha': selected['identity'],
            'sdk_manifest': selected['manifest'],
            'fixture': {
                p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                for p in fixture.iterdir()
                if p.is_file()
            },
            'executable': str(executable),
            'binary': hashlib.sha256(executable.read_bytes()).hexdigest(),
            'dependencies': dependencies(owner, root),
        }
        seal_bundle(receipt)
        if owner == 'selector':
            observed = output / 'observations.json'
            observed.write_text(
                json.dumps({
                    'receipt': receipt,
                    'controls': {'normal': {'transport-only': 'prepared selector capture'}},
                })
            )
            receipt['observations_sha256'] = hashlib.sha256(observed.read_bytes()).hexdigest()
        (output / 'receipt.json').write_text(json.dumps(receipt))
        if state.build_hook:
            state.build_hook(receipt)
        return subprocess.CompletedProcess(command, 0)

    def capture(receipt, *_args):
        captures.append(receipt['backend'])
        return {'transport-only': 'screen capture', 'receipt': receipt}

    for harness in (screen, selector):
        monkeypatch.setattr(harness, 'ROOT', root)
        monkeypatch.setattr(harness, 'crysta_reference_prefix', lambda: sdk)
        monkeypatch.setattr(harness, 'crysta_reference_source', lambda: source)
        monkeypatch.setattr(harness, '__file__', str(fixture / 'harness.py'))
        monkeypatch.setattr(harness, 'prepare_browser_toolchain', lambda _env: None)
    monkeypatch.setattr(selector, 'HERE', fixture)
    monkeypatch.setattr(screen, 'capture', capture)
    monkeypatch.setattr(subprocess, 'run', prepare)
    for prefix in ('EDI_THREAD_SELECTOR_', 'EDI_SCAN_SCREEN_'):
        for backend in ('DESKTOP', 'BROWSER'):
            monkeypatch.delenv(prefix + backend + '_RECEIPT', raising=False)
    return state


def request(owner, backend, scratch):
    scratch.mkdir(parents=True, exist_ok=True)
    return (selector if owner == 'selector' else screen).observation(backend, scratch)


INPUT_CHANNELS = [
    'gui-content',
    'gui-selection',
    'gui-appearance',
    'gui-revision',
    'gui-status',
    'gui-linked-directory',
    'browser-configuration',
    'browser-helpers',
    'build-probe',
    'platform-helper',
    'closure-helper',
    'reference-selection',
]


@pytest.mark.parametrize('owner', ['selector', 'screen'])
@pytest.mark.parametrize('backend', ['desktop', 'browser'])
@pytest.mark.parametrize('reuse', ['cache', 'prepared'])
@pytest.mark.parametrize('channel', INPUT_CHANNELS)
def test_harness_reuse_closes_effective_dependency_channels(  # noqa: PLR0912 - independent escape channels
    dispatch, owner, backend, reuse, channel, tmp_path, monkeypatch
):
    gui = dispatch.root / 'build/app/_deps/gui_components-src'
    qml = gui / 'src/Control.qml'
    qml.parent.mkdir(parents=True)
    qml.write_text('transport QML input')
    if channel == 'gui-appearance':
        gui.rename(gui.with_name('unselected-gui'))
    if channel in {'gui-revision', 'gui-status'}:
        subprocess.run(['git', 'init', '-q', str(gui)], check=True)
        subprocess.run(['git', '-C', str(gui), 'add', 'src/Control.qml'], check=True)
        subprocess.run(
            [
                'git',
                '-C',
                str(gui),
                '-c',
                'user.name=Transport',
                '-c',
                'user.email=transport@example.invalid',
                'commit',
                '-qm',
                'Record selected transport GUI',
            ],
            check=True,
        )
    first = request(owner, backend, tmp_path / 'first')
    assert request(owner, backend, tmp_path / 'second') == first and len(dispatch.calls) == 1, (
        'unchanged effective dependencies share the qualified owner/backend build'
    )
    if reuse == 'prepared':
        prefix = 'EDI_THREAD_SELECTOR_' if owner == 'selector' else 'EDI_SCAN_SCREEN_'
        receipt = (
            tmp_path / 'first' / ('build' if owner == 'selector' else backend) / 'receipt.json'
        )
        monkeypatch.setenv(prefix + backend.upper() + '_RECEIPT', str(receipt))
    paths = {
        'gui-content': qml,
        'gui-status': qml,
        'browser-configuration': dispatch.root / 'tests/fixtures/scan_screen/build.py',
        'browser-helpers': dispatch.root / 'tests/fixtures/scan_screen/harness.py',
        'build-probe': dispatch.root / 'tests/fixtures/scan_app/build_probe.py',
        'platform-helper': dispatch.root / 'tools/ci/app-platform.sh',
        'closure-helper': dispatch.root / 'tests/fixtures/app_environment/closure.py',
        'reference-selection': dispatch.root / 'tests/conftest.py',
    }
    if channel == 'gui-selection':
        gui.rename(gui.with_name('unselected-gui'))
    elif channel == 'gui-appearance':
        gui.with_name('unselected-gui').rename(gui)
    elif channel == 'gui-linked-directory':
        external = tmp_path / 'external-gui'
        external.mkdir()
        (external / 'Hidden.qml').write_text('transport external QML')
        (gui / 'src/external').symlink_to(external, target_is_directory=True)
    elif channel == 'gui-status':
        subprocess.run(['git', '-C', str(gui), 'rm', '--cached', 'src/Control.qml'], check=True)
    elif channel == 'gui-revision':
        subprocess.run(
            [
                'git',
                '-C',
                str(gui),
                '-c',
                'user.name=Transport',
                '-c',
                'user.email=transport@example.invalid',
                'commit',
                '--allow-empty',
                '-qm',
                'Change selected GUI identity',
            ],
            check=True,
        )
    elif channel in {'browser-configuration', 'browser-helpers'} and owner == 'screen':
        # The screen consumes these as its own fixture files; exercise that same live dependency.
        target = Path(screen.__file__).parent / (
            'build.py' if channel == 'browser-configuration' else 'harness.py'
        )
        target.write_text('changed owner recipe')
    else:
        path = paths[channel]
        path.write_text(path.read_text() + '\nchanged transport input')
    try:
        request(owner, backend, tmp_path / 'changed')
    except RuntimeError:
        refused = True
    else:
        refused = False
    assert refused or (reuse == 'cache' and len(dispatch.calls) == 2), (
        'changed GUI/shared recipe inputs rebuild or refuse old evidence'
    )
    if reuse == 'prepared':
        assert refused and len(dispatch.calls) == 1, (
            'prepared receipts refuse changed effective dependencies'
        )


@pytest.mark.parametrize('owner', ['selector', 'screen'])
@pytest.mark.parametrize('reuse', ['cache', 'prepared'])
@pytest.mark.parametrize(
    'asset',
    [
        'edi_app.html',
        'edi_app.js',
        'edi_app.wasm',
        'qtloader.js',
        'worker.js',
        'fonts/font.dat',
        'extra.dat',
    ],
)
@pytest.mark.parametrize('mutation', ['change', 'remove'])
def test_harness_browser_reuse_refuses_changed_served_files(
    dispatch, owner, reuse, asset, mutation, tmp_path, monkeypatch
):
    first = request(owner, 'browser', tmp_path / 'first')
    assert request(owner, 'browser', tmp_path / 'second') == first and len(dispatch.calls) == 1, (
        'a sealed unchanged browser host can reuse completed observations'
    )
    if reuse == 'prepared':
        prefix = 'EDI_THREAD_SELECTOR_' if owner == 'selector' else 'EDI_SCAN_SCREEN_'
        receipt = (
            tmp_path / 'first' / ('build' if owner == 'selector' else 'browser') / 'receipt.json'
        )
        monkeypatch.setenv(prefix + 'BROWSER_RECEIPT', str(receipt))
    path = Path(first['receipt']['executable']).parent / asset
    if asset == 'extra.dat' or mutation == 'change':
        path.write_bytes(b'changed served transport asset')
    else:
        path.unlink()
    with pytest.raises((RuntimeError, FileNotFoundError), match=r'browser|Browser|executable'):
        request(owner, 'browser', tmp_path / 'changed')
    assert len(dispatch.calls) == 1, (
        'stale served assets refuse before any cached or prepared capture returns'
    )


@pytest.mark.parametrize('owner', ['selector', 'screen'])
@pytest.mark.parametrize('field', ['dependencies', 'browser_bundle'])
def test_prepared_receipt_requires_effective_input_and_bundle_seals(
    dispatch, owner, field, tmp_path, monkeypatch
):
    request(owner, 'browser', tmp_path / 'first')
    path = tmp_path / 'first' / ('build' if owner == 'selector' else 'browser') / 'receipt.json'
    receipt = json.loads(path.read_text())
    del receipt[field]
    if owner == 'selector':
        observed = path.parent / 'observations.json'
        data = json.loads(observed.read_text())
        del data['receipt'][field]
        observed.write_text(json.dumps(data))
        receipt['observations_sha256'] = hashlib.sha256(observed.read_bytes()).hexdigest()
    path.write_text(json.dumps(receipt))
    prefix = 'EDI_THREAD_SELECTOR_' if owner == 'selector' else 'EDI_SCAN_SCREEN_'
    monkeypatch.setenv(prefix + 'BROWSER_RECEIPT', str(path))
    with pytest.raises(RuntimeError, match='unsealed'):
        request(owner, 'browser', tmp_path / 'unsealed')
    assert len(dispatch.calls) == 1, (
        'old prepared receipts without effective dependency/bundle evidence refuse'
    )


@pytest.mark.parametrize('owner', ['selector', 'screen'])
@pytest.mark.parametrize('asset', ['edi_app.html', 'edi_app.js'])
@pytest.mark.parametrize('mutation', ['change', 'remove'])
def test_new_browser_host_requires_sealed_served_assets(
    dispatch, owner, asset, mutation, tmp_path
):
    def change(receipt):
        path = Path(receipt['executable']).parent / asset
        if mutation == 'change':
            path.write_text('changed after build seal')
        else:
            path.unlink()

    dispatch.build_hook = change
    with pytest.raises(RuntimeError, match=r'browser|Browser'):
        request(owner, 'browser', tmp_path / 'new-host')
    assert not dispatch.captures, (
        'new browser hosts must validate the served bundle before any capture'
    )


@pytest.mark.usefixtures('dispatch')
def test_changing_browser_assets_during_screen_capture_cannot_cache_success(tmp_path, monkeypatch):
    def change_during_capture(receipt, *_args):
        (Path(receipt['executable']).parent / 'edi_app.html').write_text('changed while capturing')
        return {'transport-only': 'stale capture', 'receipt': receipt}

    monkeypatch.setattr(screen, 'capture', change_during_capture)
    with pytest.raises(RuntimeError, match='browser assets'):
        request('screen', 'browser', tmp_path / 'changing-host')
    assert not builds.CAPTURES, (
        'a browser bundle changed during capture cannot publish cached success'
    )


@pytest.mark.parametrize('owner', ['selector', 'screen'])
@pytest.mark.parametrize('reuse', ['cache', 'prepared'])
def test_browser_reuse_cannot_serve_an_unsealed_linked_directory(
    dispatch, owner, reuse, tmp_path, monkeypatch
):
    first = request(owner, 'browser', tmp_path / 'first')
    if reuse == 'prepared':
        prefix = 'EDI_THREAD_SELECTOR_' if owner == 'selector' else 'EDI_SCAN_SCREEN_'
        path = (
            tmp_path / 'first' / ('build' if owner == 'selector' else 'browser') / 'receipt.json'
        )
        monkeypatch.setenv(prefix + 'BROWSER_RECEIPT', str(path))
    external = tmp_path / 'external-served-files'
    external.mkdir()
    (external / 'loader.js').write_text('transport external browser loader')
    (Path(first['receipt']['executable']).parent / 'linked').symlink_to(
        external, target_is_directory=True
    )
    with pytest.raises(RuntimeError, match='linked directories'):
        request(owner, 'browser', tmp_path / 'changed')
    assert len(dispatch.calls) == 1, (
        'a browser server cannot reuse captures with unsealed linked-directory assets'
    )


@pytest.mark.parametrize('reuse', ['cache', 'prepared'])
def test_normal_screen_reuse_refuses_replaced_delivered_binary(
    dispatch, reuse, tmp_path, monkeypatch
):
    first = request('screen', 'desktop', tmp_path / 'first')
    retained = Path(first['receipt']['executable'])
    delivered = dispatch.root / 'build/app/app/edi_app'
    assert (
        retained.parent == delivered.parent and retained.read_bytes() == delivered.read_bytes()
    ), 'Desktop screen receipts bind an unchanged retained copy of the delivered normal app'
    if reuse == 'prepared':
        monkeypatch.setenv(
            'EDI_SCAN_SCREEN_DESKTOP_RECEIPT', str(tmp_path / 'first/desktop/receipt.json')
        )
    Path(first['receipt']['executable']).write_bytes(b'replaced delivered transport app')
    with pytest.raises(RuntimeError, match='replaced observation executable'):
        request('screen', 'desktop', tmp_path / 'changed')
    assert dispatch.calls == [('screen', 'desktop')] and dispatch.captures == ['desktop'], (
        'a replaced delivered app refuses cached or prepared evidence before a second capture'
    )


def test_normal_screen_transport_requires_a_delivered_app(dispatch, tmp_path):
    (dispatch.root / 'build/app/app/edi_app').unlink()
    with pytest.raises(RuntimeError, match='screen observer runs the normal app'):
        request('screen', 'desktop', tmp_path / 'missing')
    assert not dispatch.captures and not builds.BUILDS, (
        'a missing delivered desktop app fails rather than compiling a private replacement'
    )


@pytest.mark.parametrize('reuse', ['cache', 'prepared'])
@pytest.mark.parametrize('backend', ['desktop', 'browser'])
def test_screen_receipt_seals_its_native_retention_recipe(
    dispatch, reuse, backend, tmp_path, monkeypatch
):
    request('screen', backend, tmp_path / 'first')
    if reuse == 'prepared':
        monkeypatch.setenv(
            'EDI_SCAN_SCREEN_' + backend.upper() + '_RECEIPT',
            str(tmp_path / 'first' / backend / 'receipt.json'),
        )
    recipe = dispatch.root / 'tests/fixtures/fast_chart_redraws/rendering.py'
    recipe.write_text('changed retention recipe')
    try:
        request('screen', backend, tmp_path / 'changed')
    except RuntimeError:
        refused = True
    else:
        refused = False
    assert refused if reuse == 'prepared' else len(dispatch.calls) == 2, (
        'Changing the retained-binary recipe refuses prepared evidence or rebuilds cached evidence'
    )


def test_normal_screen_keeps_its_completed_artifact_during_delivery_relink(dispatch, tmp_path):
    first = request('screen', 'desktop', tmp_path / 'first')
    retained = Path(first['receipt']['executable'])
    old = retained.read_bytes()
    delivered = dispatch.root / 'build/app/app/edi_app'
    delivered.write_bytes(b'new delivered native artifact')
    assert retained != delivered and retained.read_bytes() == old, (
        'The screen driver retains the completed native artifact across a later delivery relink'
    )
    assert request('screen', 'desktop', tmp_path / 'second') == first, (
        'A later delivery relink cannot replace the already qualified screen observation artifact'
    )
