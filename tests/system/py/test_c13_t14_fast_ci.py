"""CI app reuse, opt-in observer isolation and measured shard-time boundaries."""

import copy
import importlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from tests.fixtures.fast_ci.generate import run_record
from tests.fixtures.fast_ci.policy import app_build_sites
from tests.fixtures.fast_ci.processes import process_guard, stop_observer_tree
from tests.fixtures.fast_ci.workflow import artifact_routes, timing_route
from tests.system.py.test_latest_fit_uncertainty import vehicle

ROOT = Path(__file__).resolve().parents[3]
CONTRACT = json.loads((ROOT / 'tests/fixtures/fast_ci/interface.json').read_text())


def test_no_pr_fixture_has_an_app_compiler_entry_point():
    sites = app_build_sites(ROOT)
    assert not sites, (
        'PR fixtures must reuse the CI-built app, never compile an app: ' + ', '.join(sites)
    )


@pytest.mark.parametrize(
    'channel',
    [
        'direct',
        'alias',
        'wrapper',
        'composed',
        'shell',
        'helper',
        'scopes',
        'compiler',
        'keyword',
        'assignment',
        'tool-helper',
        'shell-fixture',
    ],
)
def test_app_build_policy_reaches_each_launcher_escape(tmp_path, channel):
    folder = tmp_path / 'tests/fixtures/probe'
    folder.mkdir(parents=True)
    direct = {
        'keyword': 'import subprocess\nsubprocess.run(args=["cmake","--build","app"])\n',
        'assignment': (
            'import subprocess\nlaunch=subprocess.run\nlaunch(["cmake","--build","app"])\n'
        ),
    }
    if channel in direct:
        code = direct[channel]
    elif channel == 'tool-helper':
        helper = tmp_path / 'tools/build.py'
        helper.parent.mkdir()
        helper.write_text('import subprocess\nsubprocess.run(["cmake","--build","app"])\n')
        code = 'import subprocess\nsubprocess.run(["python","tools/build.py"])\n'
    elif channel == 'shell-fixture':
        (folder / 'build.sh').write_text('cmake --build app\n')
        code = 'pass\n'
    elif channel == 'direct':
        code = 'import subprocess\nsubprocess.run(["cmake","--build","app"])\n'
    elif channel == 'alias':
        code = 'from subprocess import run as launch\nlaunch(["cmake","--build","app"])\n'
    elif channel == 'wrapper':
        code = (
            'import subprocess\ndef execute(args): subprocess.run(args)\n'
            'execute(["cmake","--build","app"])\n'
        )
    elif channel == 'composed':
        code = 'import subprocess\nargs=["cmake"]+["--build","app"]\nsubprocess.Popen(args)\n'
    elif channel == 'shell':
        code = 'import os\nos.system("cmake --build app")\n'
    elif channel == 'compiler':
        code = 'import subprocess\nsubprocess.run(["clang++","app/src/main.cpp","-o","host"])\n'
    elif channel == 'scopes':
        code = (
            'import subprocess\n'
            'def app():\n'
            ' args=["cmake","--build","app"]\n'
            ' subprocess.run(args)\n'
            'def native():\n'
            ' args=["cmake","--build","native"]\n'
            ' subprocess.run(args)\n'
        )
    else:
        (folder / 'build.sh').write_text('cmake --build build --target edi_app\n')
        code = 'import subprocess\nsubprocess.run(["bash","build.sh"])\n'
    (folder / 'probe.py').write_text(code)
    assert app_build_sites(tmp_path), (
        'The app build policy must reject every exercised launcher channel'
    )
    if channel in {'shell-fixture', 'helper'}:
        (folder / 'build.sh').unlink()
    (folder / 'probe.py').write_text(
        'import subprocess\nsubprocess.run(["cmake","--build","native-core-probe"])\n'
    )
    assert not app_build_sites(tmp_path), 'The same policy must allow a native core-only probe'


@pytest.mark.parametrize(('enabled', 'context'), [(None, True), ('1', False), ('1', True)])
def test_normal_app_observer_switch_is_off_by_default_and_requires_test_context(
    tmp_path, enabled, context
):
    binary = Path(os.environ.get('EDI_APP_BINARY', ROOT / 'build/app/app/edi_app'))
    assert binary.is_file(), (
        'Observer tests require the app CI already built, without a fixture build'
    )
    project = tmp_path / 'project'
    vehicle(project, 'single')
    env = os.environ.copy()
    env['QT_QPA_PLATFORM'] = 'cocoa' if sys.platform == 'darwin' else 'offscreen'
    env['QT_QUICK_BACKEND'] = 'software'
    env.pop(CONTRACT['observer_switch'], None)
    env.pop(CONTRACT['test_context_variable'], None)
    if enabled is not None:
        env[CONTRACT['observer_switch']] = enabled
    if context:
        env[CONTRACT['test_context_variable']] = (
            'tests/system/py/test_c13_t14_fast_ci.py::observer (call)'
        )
    process = subprocess.Popen(
        ['pixi', 'run', '-e', 'app', str(binary), *CONTRACT['observer_arguments'], str(project)],
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        stdout, stderr = process.communicate(timeout=3)
    except subprocess.TimeoutExpired:
        stop_observer_tree(process)
        pytest.fail(
            'An observer request must be accepted or explicitly refused before entering '
            'the normal GUI event loop'
        )
    result = subprocess.CompletedProcess(process.args, process.returncode, stdout, stderr)
    if enabled == CONTRACT['enabled_value'] and context:
        assert result.returncode == 0, (
            'The opted-in normal app must execute its existing observer action'
        )
        rows = [json.loads(line) for line in result.stdout.splitlines() if line.startswith('{')]
        assert rows, 'The actual normal app observer must publish its state observation'
        assert rows[-1]['before'] == 'single', 'The observer must read the independent input mode'
        assert rows[-1]['after'] == 'joint', (
            'The observer must observe the real app mode transition'
        )
        assert not rows[-1].get('error'), (
            'The positive observer control must perform a valid operation'
        )
    else:
        assert result.returncode != 0, (
            'Default, disabled and outside-test observer requests must refuse'
        )
        assert 'observer' in (result.stdout + result.stderr).lower(), (
            'The refusal must identify the test-only observer request; '
            f'exit={result.returncode}, stdout={result.stdout!r}, stderr={result.stderr!r}'
        )


def observe_factory(family, scratch, normal, monkeypatch):
    if family == 'scan-app':
        harness = importlib.import_module('tests.fixtures.scan_app.harness').Harness(scratch)
        return harness.receipt
    module = importlib.import_module('tests.fixtures.' + family.replace('-', '_') + '.harness')
    original = module.capture

    def qualified_capture(receipt, *args, **kwargs):
        executable = Path(receipt.get('executable', '')).resolve()
        if executable != normal:
            raise RuntimeError('The factory attempted to run a cached private app executable')
        try:
            return original(receipt, *args, **kwargs)
        except subprocess.CalledProcessError as error:
            marker = Path(os.environ.get('EDI_GATE_ONCE', scratch / 'unobserved'))
            if family != 'scan-screen' or error.returncode != 77 or not marker.is_file():
                raise
            completed = json.loads(marker.read_text(encoding='utf-8'))
            assert completed['returncode'] == 0, (
                'The bounded reuse request must finish in the real native app'
            )
            assert Path(completed['argv'][0]).resolve() == normal, (
                'The completed child request must bind the delivered app identity'
            )
            assert completed['argv'][1:] == ['--test-observer', 'scan-screen'], (
                'The completed request must exercise the migrated observer'
            )
            return {'receipt': receipt, 'reuse_completed': completed}

    monkeypatch.setattr(module, 'capture', qualified_capture)
    observation = module.observation('desktop', scratch)
    receipt = observation.get('receipt', {})
    if 'reuse_completed' in observation:
        receipt = {**receipt, 'reuse_completed': observation['reuse_completed']}
    return receipt


@pytest.mark.parametrize('family', ['scan-app', 'thread-selector'])
def test_each_pr_observer_factory_uses_the_normal_app_without_a_private_build(
    tmp_path, family, monkeypatch
):
    declaration = json.loads((ROOT / 'tests/test-groups.json').read_text())['groups'][
        'nightly-only'
    ]
    off_pr = {
        'scan-app': 'tests/system/py/test_scan_app_execution.py',
        'thread-selector': 'tests/system/py/test_thread_selector.py',
        'scan-screen': 'tests/system/py/test_scan_screen.py',
    }
    if family != 'scan-screen' and off_pr[family] in declaration['paths']:
        pytest.skip('This separate host is declared off PR and gated by the actual shard selector')
    normal = Path(os.environ.get('EDI_APP_BINARY', ROOT / 'build/app/app/edi_app')).resolve()
    assert normal.is_file(), 'Every PR observer needs the CI-built normal app before construction'
    with process_guard(ROOT) as state:
        try:
            record = observe_factory(family, tmp_path / 'observer', normal, monkeypatch)
        except RuntimeError as error:
            pytest.fail(
                'A PR observer must reuse its delivered app without a private build: ' + str(error)
            )
    assert not state['blocked'], (
        'Every actual PR factory must stay outside app compiler entry points'
    )
    assert record.get('executable'), 'Every PR factory must identify its actual observed app'
    assert Path(record['executable']).resolve() == normal, (
        'A cached private executable cannot replace the delivered normal app in any PR family'
    )
    assert any(str(normal) in words for words in state['launched']), (
        'Each PR observer must actually execute its delivered normal app, not just name it'
    )


def test_system_jobs_restore_the_app_artifact_instead_of_building_it(tmp_path):
    workflow = yaml.safe_load((ROOT / '.github/workflows/ci.yml').read_text())
    artifact_routes(workflow, tmp_path)


@pytest.mark.parametrize(
    'defect', ['producer-run', 'consumer-run', 'fallback', 'miss', 'payload', 'optional']
)
def test_normal_app_cache_reuse_refuses_cross_run_and_unenforced_transfers(tmp_path, defect):
    workflow = yaml.safe_load((ROOT / '.github/workflows/ci.yml').read_text())
    artifact_routes(workflow, tmp_path / 'valid')
    damaged = copy.deepcopy(workflow)
    producer = next(
        s
        for s in damaged['jobs']['app']['steps']
        if 'cache/save' in s.get('uses', '') and 'edi_app' in str(s.get('with', {}))
    )
    consumer = next(
        s
        for s in damaged['jobs']['system']['steps']
        if 'cache/restore' in s.get('uses', '') and 'edi-app-' in str(s.get('with', {}))
    )
    if defect.endswith('-run'):
        target = producer if defect == 'producer-run' else consumer
        target['with']['key'] = 'edi-app-${{ matrix.platform }}-main'
    elif defect == 'fallback':
        consumer['with']['restore-keys'] = 'edi-app-${{ matrix.platform }}-'
    elif defect == 'miss':
        consumer['with']['fail-on-cache-miss'] = False
    elif defect == 'payload':
        producer['with']['path'] = 'build/app'
    else:
        consumer['continue-on-error'] = True
    with pytest.raises(AssertionError):
        artifact_routes(damaged, tmp_path / 'damaged')


def invoke_time_gate(tmp_path, current, main):
    script = ROOT / CONTRACT['time_gate']
    assert script.is_file(), (
        'A PR system-shard timing gate must exist and accept actual job evidence'
    )
    paths = dict(CONTRACT['time_gate_current_identity'])
    for name, record in (('current', current), ('main', main)):
        path = tmp_path / f'{name}.json'
        path.write_text(json.dumps(record))
        paths[name] = str(path)
    argv = [
        'python',
        str(script),
        *[value.format(**paths) for value in CONTRACT['time_gate_arguments']],
    ]
    env = dict(os.environ)
    for key in ('GITHUB_RUN_ID', 'GITHUB_SHA', 'GITHUB_EVENT_PATH'):
        env.pop(key, None)
    result = subprocess.run(
        argv, cwd=ROOT, env=env, capture_output=True, text=True, timeout=3, check=False
    )
    assert result.stdout.startswith('system shard time: '), (
        'Every timing witness must reach evidence validation, not fail at argument parsing'
    )
    return result


@pytest.mark.parametrize(
    ('baseline', 'ratio', 'allowed'),
    [
        (2400, 1.199, True),
        (2400, 1.2, True),
        (2400, 1.201, False),
        (1200, 1.25, False),
        (3000, 1.1, True),
    ],
)
def test_real_shard_gate_uses_main_and_the_twenty_percent_boundary(
    tmp_path, baseline, ratio, allowed
):
    main = run_record('main', [baseline] * 3)
    current = run_record(
        'feature', [baseline * 0.4, baseline * ratio, baseline * 0.5], current=True
    )
    result = invoke_time_gate(tmp_path, current, main)
    assert (result.returncode == 0) == allowed, (
        'The CI-time verdict must compare the slow shard with actual main evidence'
    )
    if not allowed:
        diagnostic = result.stdout + result.stderr
        assert '2/3' in diagnostic, (
            'A timing regression must name the affected shard rather than average it away'
        )
        assert 'main' in diagnostic.lower(), (
            'A timing regression must identify its main comparison'
        )


@pytest.mark.parametrize('parts', [3, 16])
def test_the_last_system_shard_cannot_escape_the_timing_gate(tmp_path, parts):
    main = run_record('main', [2400] * parts)
    durations = [1200] * parts
    durations[-1] = 3000
    result = invoke_time_gate(tmp_path, run_record('feature', durations, current=True), main)
    assert result.returncode != 0, 'Every shard must be compared even after the matrix grows'
    assert f'{parts}/{parts}' in result.stdout + result.stderr, (
        'The gate must identify the final slow shard rather than inspect a fixed subset'
    )


@pytest.mark.parametrize(
    'mutation',
    [
        'missing-main',
        'missing-current',
        'pending',
        'cancelled',
        'wrong-main-branch',
        'wrong-main-event',
        'duplicate-current',
        'zero-baseline',
        'bad-timestamp',
        'wrong-current-id',
        'wrong-current-head',
    ],
)
def test_shard_time_gate_refuses_unprovable_evidence(tmp_path, mutation):
    main = run_record('main', [2400] * 3)
    current = run_record('feature', [2500] * 3, current=True)
    if mutation == 'missing-main':
        main['jobs'] = []
    elif mutation == 'missing-current':
        current['jobs'].pop(1)
    elif mutation == 'pending':
        current['jobs'][1]['status'] = 'in_progress'
        current['jobs'][1]['completed_at'] = None
    elif mutation == 'cancelled':
        current['jobs'][1]['conclusion'] = 'cancelled'
    elif mutation == 'wrong-main-branch':
        main['head_branch'] = 'unrelated-feature'
    elif mutation == 'wrong-main-event':
        main['event'] = 'pull_request'
    elif mutation == 'duplicate-current':
        current['jobs'].append(copy.deepcopy(current['jobs'][1]))
    elif mutation == 'zero-baseline':
        main['jobs'][1]['completed_at'] = main['jobs'][1]['started_at']
    elif mutation == 'wrong-current-id':
        current['id'] = 110
    elif mutation == 'wrong-current-head':
        current['head_sha'] = 'a' * 40
    else:
        main['jobs'][1]['started_at'] = 'not-a-timestamp'
    result = invoke_time_gate(tmp_path, current, main)
    assert result.returncode == 2, (
        'Incomplete, unrelated or invalid timing evidence must reach the evidence-refusal verdict'
    )
    diagnostic = {
        'missing-main': ('main', 'Linux', 'shard'),
        'missing-current': ('current', 'Linux', 'shard'),
        'pending': ('current', 'in_progress'),
        'cancelled': ('current', 'cancelled'),
        'wrong-main-branch': ('baseline', 'unrelated-feature'),
        'wrong-main-event': ('baseline', 'pull_request'),
        'duplicate-current': ('current', 'twice'),
        'zero-baseline': ('main', 'positive wall time'),
        'bad-timestamp': ('started_at', 'valid'),
        'wrong-current-id': ('current', '110', '111'),
        'wrong-current-head': ('current', 'a' * 40, 'c' * 40),
    }[mutation]
    assert all(word in result.stdout for word in diagnostic), (
        'A timing evidence refusal must identify the actual malformed or mismatched input'
    )


def test_timing_gate_is_wired_after_system_shards_on_pull_requests(tmp_path):
    workflow = yaml.safe_load((ROOT / '.github/workflows/ci.yml').read_text())
    timing_route(workflow, tmp_path)


@pytest.mark.parametrize(
    'mutation',
    [
        'equal-omissions',
        'missing-platform',
        'mixed-denominators',
        'zero-part',
        'out-of-range',
        'renamed-platform',
        'mismatched-declarations',
        'empty-declaration',
    ],
)
def test_matching_incomplete_or_malformed_partition_evidence_must_refuse(tmp_path, mutation):
    main = run_record('main', [2400] * 3)
    current = run_record('feature', [2400] * 3, current=True)
    for record in (main, current):
        if mutation == 'equal-omissions':
            record['jobs'] = [record['jobs'][0]]
        elif mutation == 'missing-platform':
            record['expected_system_shards']['macOS'] = 3
        elif mutation == 'mixed-denominators':
            record['jobs'][1]['name'] = 'system · Linux · 2/4'
        elif mutation == 'zero-part':
            record['jobs'][0]['name'] = 'system · Linux · 0/3'
        elif mutation == 'out-of-range':
            record['jobs'][0]['name'] = 'system · Linux · 4/3'
        elif mutation == 'renamed-platform':
            for job in record['jobs'][:3]:
                job['name'] = job['name'].replace('Linux', 'unknown-host')
        elif mutation == 'empty-declaration':
            record['expected_system_shards'] = {}
    if mutation == 'mismatched-declarations':
        current['expected_system_shards'] = {'Linux': 4}
    result = invoke_time_gate(tmp_path, current, main)
    assert result.returncode == 2, (
        'Matching receipts must still prove complete declared platform and partition membership'
    )
    assert 'cannot compare with main' in result.stdout and ('shard' in result.stdout), (
        'An incomplete partition refusal must identify its evidence'
    )


def test_a_complete_declared_two_platform_matrix_passes_at_the_ratio_boundary(tmp_path):
    main = run_record('main', [2400] * 3)
    current = run_record('feature', [2880] * 3, current=True)
    for record in (main, current):
        record['expected_system_shards']['macOS'] = 3
        record['jobs'] += [
            dict(job, name=job['name'].replace('Linux', 'macOS')) for job in record['jobs'][:3]
        ]
    result = invoke_time_gate(tmp_path, current, main)
    assert result.returncode == 0, (
        'Complete declared matrices must admit the permitted 1.2 boundary'
    )


@pytest.fixture(scope='module')
def migrated_screen_reuse(tmp_path_factory):
    normal = Path(os.environ.get('EDI_APP_BINARY', ROOT / 'build/app/app/edi_app')).resolve()
    assert normal.is_file(), 'The migrated factory requires the app CI already built'
    scratch = tmp_path_factory.mktemp('normal-screen-reuse')
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv('EDI_GATE_SETTINGS_ONLY', '1')
        patch.setenv('EDI_GATE_ONCE', str(scratch / 'completed-native-request.json'))
        with process_guard(ROOT) as state:
            record = observe_factory('scan-screen', scratch, normal, patch)
    return record, normal, state


def test_migrated_screen_factory_binds_the_normal_delivered_executable(migrated_screen_reuse):
    record, normal, _ = migrated_screen_reuse
    assert Path(record['executable']).resolve() == normal, (
        'The migrated desktop factory must bind the delivered app, '
        'independently of nightly companion placement'
    )


def test_migrated_screen_factory_executes_its_actual_child_request(migrated_screen_reuse):
    record, normal, state = migrated_screen_reuse
    assert record['reuse_completed']['returncode'] == 0, (
        'The real migrated request must complete successfully'
    )
    assert any(
        bool(words)
        and Path(words[0]).resolve() == normal
        and '--test-observer' in words
        and 'scan-screen' in words
        for words in state['launched']
    ), 'The actual child transport must execute the delivered normal app with the migrated request'


def test_migrated_screen_factory_cannot_compile_a_private_app(migrated_screen_reuse):
    _, _, state = migrated_screen_reuse
    assert not state['blocked'], (
        'The actual migrated factory and its Python helper '
        'must stay outside app compiler entry points'
    )
