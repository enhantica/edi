"""D6/I34 topology, using the accepted restore boundary at 12a297d28."""

import copy
import shlex
from pathlib import Path

import pytest
import yaml

from tests.fixtures.e09_t75_workflow import active, reached, require_reporting_step
from tests.fixtures.native_process import environment_bash
from tests.integration.py.ci_runner_contract import platform_job, self_hosted_runners

ROOT = Path(__file__).resolve().parents[3]
CONSUMERS = ['audit', 'core', 'system', 'notebooks', 'cli-python', 'docs', 'app']
APP_JOBS = {'linux-64': 'app', 'osx-arm64': 'app-macos', 'win-64': 'app-windows'}
SDK_OS = {'linux-64': 'Linux', 'osx-arm64': 'macOS', 'win-64': 'Windows'}
NIGHTLY_MARKERS = {
    'notebooks': 'Notebooks run at night and on a manual run',
    'docs': 'The docs build runs at night and on a manual run',
}
NIGHTLY_GUARD = "env.NIGHTLY == 'true'"


def jobs():
    return yaml.safe_load((ROOT / '.github/workflows/ci.yml').read_text())['jobs']


def public_profile(data):
    runners = [
        runner for name in ['native', *CONSUMERS] for runner in self_hosted_runners(data[name])
    ]
    kinds = {runner[0] for runner in runners}
    assert kinds in ({'github-hosted'}, {'self-hosted'}), (
        'workflow applicability requires one resolved hosted or private runner family'
    )
    return kinds == {'github-hosted'}


def public_build_boundary(data, name, platform=None):
    if name == 'app' and platform is None:
        for sdk in APP_JOBS:
            public_build_boundary(data, 'app', sdk)
        return
    if name == 'app':
        job = data[APP_JOBS[platform]]
        assert job['steps'] is data['app']['steps'], (
            'All desktop app jobs share one YAML step list'
        )
        assert job['name'] == f'app · {SDK_OS[platform]}', (
            'Every desktop job has its static OS name'
        )
    else:
        job = data[name]
    require_public_job(job, name, platform)
    require_public_steps(job, name, platform)


def require_public_job(job, name, platform):
    runners = self_hosted_runners(job)
    assert all(runner[0] == 'github-hosted' for runner in runners), (
        'public native jobs must use the approved standard hosted platforms'
    )
    if platform is not None:
        expected_os = SDK_OS[platform]
        if name == 'system':
            legs = job['strategy']['matrix']['include']
            expected = {
                (os, sdk, part)
                for os, sdk in (('Linux', 'linux-64'), ('macOS', 'osx-arm64'))
                for part in (1, 2, 3)
            }
            assert (
                len(legs) == 6
                and {(leg.get('platform'), leg.get('sdk'), leg.get('part')) for leg in legs}
                == expected
            ), 'each system part binds exactly its prescribed SDK, OS and part once'
        assert sum(runner[1] == expected_os for runner in runners) == (
            3 if name == 'system' else 1
        ), 'each public native boundary must execute on its exact prescribed SDK platform'
    if name != 'notebooks':
        terms = str(job.get('if', '')).removeprefix('${{').removesuffix('}}').split('&&')
        assert any(
            term.strip(' ()') == 'github.event.pull_request.head.repo.fork == false'
            for term in terms
        ) and (name == 'system' or '||' not in str(job.get('if', ''))), (
            'public SDK native jobs must retain the positive trusted-pull-request fork boundary'
        )
        for core_only in (False, True):
            assert not active(
                job,
                'pull_request',
                fork=True,
                core_only=core_only,
                states={
                    'changes': 'success',
                    'native': 'success',
                    'core': 'success',
                    'crysta-sdk': 'success',
                },
            ), 'every public SDK job must refuse forks with either core-only input'
    for event in ('pull_request', 'push', 'schedule', 'workflow_dispatch'):
        expected = not (
            (name == 'system' and event in {'pull_request', 'push'})
            or (name == 'app-wasm' and event == 'pull_request')
        )
        assert (
            active(
                job,
                event,
                states={
                    'changes': 'success',
                    'native': 'success',
                    'core': 'success',
                    'crysta-sdk': 'success',
                },
            )
            == expected
        ), 'system is nightly or manual, WebAssembly skips PRs, and fast SDK jobs retain scope'
        assert active(
            job,
            event,
            core_only=True,
            states={
                'changes': 'success',
                'native': 'success',
                'core': 'success',
                'crysta-sdk': 'success',
            },
        ) == (expected and name in {'native', 'core', 'system'}), (
            'core-only repairs retain native/core and skip every downstream public SDK job'
        )
    assert job.get('environment') == 'crysta-sdk', (
        'public native builds must use the protected private SDK environment'
    )
    needs = job.get('needs')
    needs = [needs] if isinstance(needs, str) else needs
    expected_needs = {'changes', 'crysta-sdk'}
    if name == 'system':
        expected_needs.update({'app', 'app-macos'})
        public_system_app_route(job)
        if platform is not None:
            sdk = next(
                step for step in job['steps'] if step.get('uses') == './.github/actions/crysta-sdk'
            )
            assert selects_sdk(sdk, platform), 'Every system part acquires the SDK for its OS'
    elif name in {'app', 'core'}:
        expected_needs.add('native')
    elif name == 'notebooks':
        expected_needs |= {'native', 'core'}
    elif name != 'native':
        expected_needs.add('core')
    assert set(needs or []) == expected_needs, (
        'Native consumers wait for the exact SDK and their transitive native producer'
    )
    if name == 'app':
        assert active(job, 'pull_request', states=dict.fromkeys(expected_needs, 'success')), (
            'Each desktop app starts once changes, the native build and the SDK finish while core runs'
        )
    assert job.get('env', {}).get('CRYSTA_SOURCE_SHA') == (
        '${{ needs.changes.outputs.crysta_sha }}'
    ), 'Each native consumer retains the workflow-resolved engine source identity'


def require_public_steps(job, name, platform):
    steps = job['steps']
    if name == 'app':
        require_desktop_sdk_and_msvc(steps, platform)
    if name in NIGHTLY_MARKERS:
        require_nightly_work(job, NIGHTLY_MARKERS[name])
    builds = [
        (i, step)
        for i, step in enumerate(steps)
        if shlex.split(step.get('run', '')) == ['pixi', 'run', 'core-build']
    ]
    assert len(builds) == 1, 'Every native route crosses one explicit core-build boundary'
    index, build = builds[0]
    expected_condition = {
        'docs': NIGHTLY_GUARD,
        'notebooks': NIGHTLY_GUARD + ' && (github.event.pull_request.head.repo.fork == false)',
        'app': "runner.os != 'Windows' && (steps.inputs.outputs.run == 'true')",
    }.get(name)
    assert step_condition(build) == expected_condition and not build.get('continue-on-error'), (
        'The native build or restore follows the declared protected execution scope'
    )
    if name == 'native':
        producer_boundary(job)
        first_use = 'cpp-test'
    else:
        public_native_transfer(steps, index, name)
        first_use = FIRST_USE[name]
    uses = [i for i, step in enumerate(steps) if first_use in step.get('run', '')]
    assert uses and index < uses[0], (
        'Each native build or restore finishes before the first public native use'
    )
    assert_first_public_use(name, build, steps[uses[0]], expected_condition)


def require_desktop_sdk_and_msvc(steps, platform):
    sdk = next(step for step in steps if step.get('uses') == './.github/actions/crysta-sdk')
    assert selects_sdk(sdk, platform), 'The desktop build acquires its exact pinned SDK'
    windows = [step for step in steps if 'tools/ci/app-windows-build.py' in step.get('run', '')]
    assert len(windows) == 1, 'The shared app steps include one MSVC build'
    assert steps.index(sdk) < steps.index(windows[0]), 'MSVC builds after the pinned SDK arrives'
    assert active(windows[0], 'schedule', bindings={'runner.os': SDK_OS[platform]}) == (
        platform == 'win-64'
    ), 'Only the Windows job reaches the installer-aligned MSVC build'


def require_nightly_work(job, marker_name):
    nightly = {'if': job.get('env', {}).get('NIGHTLY', False)}
    markers = [step for step in job['steps'] if step.get('name') == marker_name]
    assert len(markers) == 1, 'A single skip receipt keeps the required check name'
    marker = markers[0]
    assert set(marker) == {'name', 'if', 'run'} and marker['run'] == (
        f'echo "{marker_name}; this $GITHUB_EVENT_NAME run does not."'
    ), 'The skip receipt only reports the cadence'
    outcomes = {('build', 'outcome'): 'success', ('tutorials', 'outcome'): 'success'}
    for event in ('pull_request', 'push', 'schedule', 'workflow_dispatch'):
        full = event in {'schedule', 'workflow_dispatch'}
        enabled = active(nightly, event)
        assert enabled == full, 'Only the nightly and manual events enable the real work'
        selected = [
            step
            for step in job['steps']
            if active(
                step, event, outputs=outcomes, bindings={'env.NIGHTLY': str(enabled).lower()}
            )
        ]
        assert selected == (
            [step for step in job['steps'] if step is not marker] if full else [marker]
        ), 'PR and push run only the receipt; nightly and manual run every actual step'


def assert_first_public_use(name, build, use, expected_condition):
    if name in {'native', 'core'}:
        assert build.get('id') == 'build', (
            'A guarded native use must name its actual core-build producer'
        )
        require_reporting_step(use, 'build')
    else:
        assert step_condition(use) == expected_condition and not use.get('continue-on-error'), (
            'The first public native use executes whenever its protected restore succeeds'
        )


def step_condition(step):
    value = step.get('if')
    if isinstance(value, str):
        return value.removeprefix('${{').removesuffix('}}').strip()
    return value


def selects_sdk(step, platform):
    expression = step_condition({'if': step['with']['platform']})
    return active(
        {'if': f"({expression}) == '{platform}'"},
        'schedule',
        bindings={'runner.os': SDK_OS[platform]},
    )


def public_system_app_route(job):
    steps = job['steps']
    transfers = [
        step for step in steps if step.get('with', {}).get('key', '').startswith('edi-app-')
    ]
    assert len(transfers) == 1, 'System restores exactly one app cache'
    transfer = transfers[0]
    assert transfer['with']['key'] == 'edi-app-${{ matrix.platform }}-${{ github.run_id }}', (
        'System restores the current run app for its own platform'
    )
    assert transfer['with'].get('fail-on-cache-miss') is True, (
        'A missing app cache fails its shard'
    )
    consumers = [
        step
        for step in steps
        if step is transfer
        or step.get('run', '').startswith(('chmod +x build/app/', 'pixi install -e app'))
    ]
    assert len(consumers) == 3, (
        'Restoring the app, making it executable and installing Qt each run'
    )
    results = ('success', 'failure', 'skipped', 'cancelled')
    for platform, needed in (('Linux', 'app'), ('macOS', 'app-macos')):
        for linux in results:
            for macos in results:
                inputs = {'needs.app.result': linux, 'needs.app-macos.result': macos}
                for step in consumers:
                    observed = active(
                        step, 'schedule', bindings={**inputs, 'matrix.platform': platform}
                    )
                    assert observed == (inputs[f'needs.{needed}.result'] != 'skipped'), (
                        'Each system part uses its own app result, even when its sibling skips'
                    )


@pytest.mark.parametrize(
    'condition',
    [
        'true',
        'github.event.pull_request.head.repo.fork != false',
        'github.event.pull_request.head.repo.fork == false || inputs.core_only != true',
        'github.event.pull_request.head.repo.fork == false && inputs.core_only == true',
        'github.event.pull_request.head.repo.fork == false && inputs.unknown != true',
    ],
)
def test_public_sdk_boundary_rejects_guard_and_core_only_escapes(condition):
    data = jobs()
    public_build_boundary(data, 'audit')
    damaged = copy.deepcopy(data)
    damaged['audit']['if'] = condition
    with pytest.raises(AssertionError):
        public_build_boundary(damaged, 'audit')


@pytest.mark.parametrize('damage', ['missing-part', 'duplicate-part', 'wrong-sdk'])
def test_public_system_boundary_proves_every_part_and_sdk(damage):
    data = jobs()
    for platform in ('linux-64', 'osx-arm64'):
        public_build_boundary(data, 'system', platform)
    damaged = copy.deepcopy(data)
    legs = damaged['system']['strategy']['matrix']['include']
    if damage == 'missing-part':
        legs.pop()
    elif damage == 'duplicate-part':
        legs[-1] = copy.deepcopy(legs[-2])
    else:
        legs[-1]['sdk'] = 'linux-64'
    with pytest.raises(AssertionError, match='each system part'):
        public_build_boundary(damaged, 'system', 'osx-arm64')
    if damage == 'wrong-sdk':
        damaged = copy.deepcopy(data)
        app_cache = next(
            step
            for step in damaged['system']['steps']
            if step.get('with', {}).get('key', '').startswith('edi-app-')
        )
        app_cache['if'] = "needs.app.result != 'skipped'"
        with pytest.raises(AssertionError, match='its own app result'):
            public_build_boundary(damaged, 'system', 'osx-arm64')


def test_d6_one_unfiltered_native_matrix_uploads_the_prescribed_artifacts():
    data = jobs()
    assert 'native' in data, ' I34 requires the one native producer job'
    native = data['native']
    if public_profile(data):
        for platform in ('linux-64', 'osx-arm64', 'win-64'):
            public_build_boundary(data, 'native', platform)
        assert {leg.get('sdk') for leg in native['strategy']['matrix']['include']} == {
            'linux-64',
            'osx-arm64',
            'win-64',
        }, 'the public native matrix must compile against all three independently prescribed SDKs'
        return
    producers = [platform_job(data, 'native', sdk) for sdk in ('linux-64', 'osx-arm64')]
    legs = [leg for job in producers for leg in job['strategy']['matrix']['include']]
    assert len(legs) == 2, 'native production covers exactly the two supported platforms'
    assert {leg.get('sdk') for leg in legs} == {'linux-64', 'osx-arm64'}, (
        'native production retains both independently prescribed SDK platforms'
    )
    assert {tuple(leg['runner']) for leg in legs} == {
        ('self-hosted', 'Linux', 'X64'),
        ('self-hosted', 'macOS', 'ARM64'),
    }, 'native production compiles once on each supported platform'
    for job in producers:
        producer_boundary(job)
        assert 'if' not in job, 'default native production runs on every event without filters'
        assert job.get('needs') in ('changes', ['changes']), (
            'each native producer uses the common source resolution'
        )
        upload = next(
            step['with']
            for step in job['steps']
            if step.get('uses', '').startswith('actions/upload-artifact@')
        )
        assert upload['name'] == 'edi-native-${{ matrix.sdk }}', (
            'native artifact names retain the prescribed platform prefix'
        )
        assert 'edi-native' in str(upload['path']), (
            'native uploads preserve executable bits through tar and include identity metadata'
        )
        assert str(upload.get('retention-days')) == '1' and upload.get('overwrite') is True, (
            'native artifacts expire in one day and all-job reruns replace them'
        )


@pytest.mark.parametrize('consumer', CONSUMERS)
def test_d6_every_default_native_consumer_waits_downloads_and_selects_artifact_mode(consumer):
    data = jobs()
    if public_profile(data):
        public_build_boundary(data, consumer)
        return
    job = data[consumer]
    needs = job.get('needs', [])
    if isinstance(needs, str):
        needs = [needs]
    platforms = {runner[1] for runner in self_hosted_runners(job)}
    producers = {'native' if platform == 'Linux' else 'native-macos' for platform in platforms}
    cores = (
        {'core' if platform == 'Linux' else 'core-macos' for platform in platforms}
        if consumer != 'core'
        else set()
    )
    assert set(needs) == {'changes', *producers, *cores}, (
        'every native consumer waits for its own platform builds and source resolution; '
        'downstream consumers also wait for those platforms core tests'
    )
    assert str(job.get('env', {}).get('EDI_NATIVE_ARTIFACT')) == '1', (
        ' D6 all implicit core-build dependencies in every consumer'
        ' must select refuse-never-rebuild mode'
    )
    downloads = [
        step
        for step in job['steps']
        if step.get('uses', '').startswith('actions/download-artifact@')
        and 'edi-native-' in str(step.get('with', {}).get('name', ''))
    ]
    assert len(downloads) == 1, (
        ' D6 every default native consumer must download exactly its native artifact'
    )
    step = downloads[0]
    assert not step.get('continue-on-error'), (
        ' D6 a missing native artifact must fail the job rather tha'
        'n continue or conditionally rebuild'
    )
    assert step.get('if', 'success()') == 'success()', (
        ' D6 a missing native artifact must fail the job rather tha'
        'n continue or conditionally rebuild'
    )
    params = step['with']
    assert 'pattern' not in params, (
        ' D6 artifact selection must be exact and confined to the same workflow run'
    )
    assert params.get('run-id', '${{ github.run_id }}') == '${{ github.run_id }}', (
        ' D6 artifact selection must be exact and confined to the same workflow run'
    )
    assert params.get('repository', '${{ github.repository }}') in {
        '${{ github.repository }}',
        'enhantica/edi',
    }, ' D6 default native consumers must download only edi artifacts'


ROSTER = [
    (job, platform)
    for job in CONSUMERS
    for platform in (
        ('linux-64', 'osx-arm64')
        if job in {'core', 'system', 'cli-python', 'app'}
        else ('linux-64',)
    )
]
FIRST_USE = {
    'audit': 'per-pr-audit',
    'core': 'crysta-consumer',
    'system': 'system-tests-part',
    'notebooks': 'notebook-tests',
    'cli-python': 'cli-projects',
    'docs': 'notebook-exec-ci',
    'app': 'app-build',
    'app-wasm': 'wasm-check',
}


def consumer_boundary(job, platform):
    legs = job.get('strategy', {}).get('matrix', {}).get('include', [{}])
    matches = []
    for leg in legs:
        runner = str(leg.get('runner', job.get('runs-on', [])))
        actual = 'osx-arm64' if 'macOS' in runner else 'linux-64' if 'Linux' in runner else None
        if actual == platform:
            matches.append(leg)
    assert len(matches) == 1, ' I34 each consumer must have exactly its declared platform leg'
    leg = matches[0]

    def resolve(value):
        value = str(value)
        for key, item in leg.items():
            value = value.replace('${{ matrix.' + key + ' }}', str(item))
        return value

    downloads = [
        (i, step)
        for i, step in enumerate(job['steps'])
        if step.get('uses', '').startswith('actions/download-artifact@')
        and 'edi-native-' in str(step.get('with', {}).get('name', ''))
    ]
    assert len(downloads) == 1, ' I34 requires one exact native download on every platform'
    index, download = downloads[0]
    params = download.get('with', {})
    assert resolve(params['name']) == 'edi-native-' + platform, (
        ' I34 artifact selection must name this platform, never a sibling platform'
    )
    assert params.get('repository', '${{ github.repository }}') in {
        '${{ github.repository }}',
        'enhantica/edi',
    }, ' I34 native download must address edi'
    assert str(params.get('run-id', '${{ github.run_id }}')) == '${{ github.run_id }}', (
        ' I34 native download must address this run'
    )
    assert 'pattern' not in params, ' I34 native artifact resource is selected exactly'
    restores = [
        (i, step)
        for i, step in enumerate(job['steps'])
        if step.get('name') == 'Restore and validate the native artifact'
    ]
    assert len(restores) == 1, ' I34 each consumer needs its explicit restore boundary'
    ri, restore = restores[0]
    assert restore.get('run', '').strip() == 'pixi run core-build', (
        ' I34 restore must execute artifact-mode core-build'
    )
    for step in (download, restore):
        assert step.get('if', 'success()') in {'success()', '${{ success() }}'}, (
            ' I34 download and restoration must execute whenever the consumer succeeds'
        )
        assert not step.get('continue-on-error'), ' I34 resource refusal must fail the consumer'
    for step in job['steps']:
        assert str(step.get('env', {}).get('EDI_NATIVE_ARTIFACT', '1')) == '1', (
            ' I34 no consumer step can override refuse-never-rebuild mode'
        )
    first = next(
        (
            i
            for i, step in enumerate(job['steps'])
            if FIRST_USE[job['_consumer']] in step.get('run', '')
        ),
        None,
    )
    assert first is not None, (
        ' I34 actual download must precede restore and every first native use'
    )
    assert index < ri < first, (
        ' I34 actual download must precede restore and every first native use'
    )
    return download, restore, leg


@pytest.mark.parametrize(('consumer', 'platform'), ROSTER)
def test_d6_explicit_restore_runs_between_exact_download_and_first_native_use(consumer, platform):
    data = jobs()
    if public_profile(data):
        public_build_boundary(data, consumer, platform)
        return
    job = {**platform_job(data, consumer, platform), '_consumer': consumer}
    consumer_boundary(job, platform)


def producer_boundary(job):
    steps = job['steps']
    builds = [
        (i, step)
        for i, step in enumerate(steps)
        if shlex.split(step.get('run', '')) == ['pixi', 'run', 'core-build']
    ]
    packs = [
        (i, step)
        for i, step in enumerate(steps)
        if 'edi_native.py' in step.get('run', '') and ' pack ' in step['run']
    ]
    uploads = [
        (i, step)
        for i, step in enumerate(steps)
        if step.get('uses', '').startswith('actions/upload-artifact@')
    ]
    assert len(builds) == len(packs) == len(uploads) == 1, (
        ' I34 producer requires one actual native build, pack and upload'
    )
    bi, build = builds[0]
    pi, pack = packs[0]
    ui, upload = uploads[0]
    assert bi < pi < ui, ' I34 actual workflow must build before packing before uploading'
    assert upload.get('with', {}).get('name') == 'edi-native-${{ matrix.sdk }}', (
        'The producer artifact name matches the platform-addressed native consumer'
    )
    assert upload.get('with', {}).get('path') == 'build/edi-native-artifact', (
        'The producer uploads only its validated tar and binding manifest directory'
    )

    for step in (build, pack, upload):
        for event in ('pull_request', 'push', 'workflow_dispatch'):
            reached(job, event)
            reached(step, event)
    environment = {**job.get('env', {}), **build.get('env', {})}
    assert environment.get('EDI_CORE_TARGETS') == 'edi_tests edi_integration_tests', (
        ' I34 producer build must include the independently required native test target'
    )
    assert str(environment.get('EDI_NATIVE_ARTIFACT', '0')) == '0', (
        ' I34 producer must build, never accidentally restore artifact mode'
    )
    return builds[0], packs[0], uploads[0]


@pytest.mark.parametrize(
    'defect',
    ['missing-build', 'upload-first', 'pack-first', 'target', 'mode', 'build-if', 'job-if'],
)
def test_native_producer_contract_refuses_missing_reordered_or_nonbuilding_work(defect):
    job = {
        'steps': [
            {
                'run': 'pixi run core-build',
                'id': 'build',
                'env': {'EDI_CORE_TARGETS': 'edi_tests edi_integration_tests'},
            },
            {'run': 'pixi run python tools/ci/edi_native.py pack --out "$RUNNER_TEMP/edi-native"'},
            {
                'uses': 'actions/upload-artifact@v5',
                'with': {
                    'name': 'edi-native-${{ matrix.sdk }}',
                    'path': 'build/edi-native-artifact',
                },
            },
        ]
    }
    producer_boundary(job)
    mutant = copy.deepcopy(job)
    if defect == 'missing-build':
        mutant['steps'].pop(0)
    elif defect == 'upload-first':
        mutant['steps'] = [mutant['steps'][2], *mutant['steps'][:2]]
    elif defect == 'pack-first':
        mutant['steps'][:2] = mutant['steps'][1::-1]
    elif defect == 'target':
        mutant['steps'][0]['env']['EDI_CORE_TARGETS'] = 'edi_core'
    elif defect == 'mode':
        mutant['steps'][0]['env']['EDI_NATIVE_ARTIFACT'] = '1'
    elif defect == 'build-if':
        mutant['steps'][0]['if'] = False
    else:
        mutant['if'] = "github.ref == 'refs/heads/main'"
    with pytest.raises(
        AssertionError,
        match='required workflow route' if defect in {'build-if', 'job-if'} else 'I34',
    ):
        producer_boundary(mutant)

    require_public_producer_escapes(defect)


def require_public_producer_escapes(defect):
    public_job = {
        'runs-on': '${{ matrix.runner }}',
        'environment': 'crysta-sdk',
        'if': 'github.event.pull_request.head.repo.fork == false',
        'needs': ['changes', 'crysta-sdk'],
        'env': {'CRYSTA_SOURCE_SHA': '${{ needs.changes.outputs.crysta_sha }}'},
        'strategy': {
            'matrix': {
                'include': [
                    {'platform': 'Linux', 'runner': 'ubuntu-24.04', 'sdk': 'linux-64'},
                    {'platform': 'macOS', 'runner': 'macos-15', 'sdk': 'osx-arm64'},
                ]
            }
        },
        'steps': [
            {
                'run': 'pixi run core-build',
                'id': 'build',
                'env': {'EDI_CORE_TARGETS': 'edi_tests edi_integration_tests'},
            },
            {'run': 'pixi run python tools/ci/edi_native.py pack --out native-objects'},
            {
                'uses': 'actions/upload-artifact@v4',
                'with': {
                    'name': 'edi-native-${{ matrix.sdk }}',
                    'path': 'build/edi-native-artifact',
                },
            },
            {
                'run': 'pixi run --skip-deps cpp-test',
                'if': "${{ !cancelled() && steps.build.outcome == 'success' }}",
            },
        ],
    }
    public_build_boundary({'native': public_job}, 'native', 'linux-64')
    public_mutant = copy.deepcopy(public_job)
    if defect == 'missing-build':
        public_mutant['steps'].pop(0)
    elif defect == 'upload-first':
        public_mutant['steps'].insert(0, public_mutant['steps'].pop(2))
    elif defect == 'pack-first':
        public_mutant['steps'][:2] = public_mutant['steps'][1::-1]
    elif defect == 'target':
        public_mutant['steps'][0]['env']['EDI_CORE_TARGETS'] = 'edi_core'
    elif defect == 'mode':
        public_mutant['env']['EDI_NATIVE_ARTIFACT'] = '1'
    elif defect == 'build-if':
        public_mutant['steps'][0]['if'] = False
    else:
        public_mutant['if'] = True
    with pytest.raises(AssertionError):
        public_build_boundary({'native': public_mutant}, 'native', 'linux-64')
    if defect == 'build-if':
        disabled_use = copy.deepcopy(public_job)
        disabled_use['steps'][3]['if'] = False
        with pytest.raises(AssertionError, match='independent check'):
            public_build_boundary({'native': disabled_use}, 'native', 'linux-64')


def public_native_transfer(steps, index, name):
    transports = [
        (i, step)
        for i, step in enumerate(steps)
        if step.get('uses') == './.github/actions/edi-native'
    ]
    assert len(transports) == 1, 'Each consumer selects one same-run native artifact action'
    transfer_index, transfer = transports[0]
    assert transfer_index < index, 'Artifact selection precedes restoration and first use'
    assert set(transfer['with']) == {'platform'}, (
        'Default native consumers restore this run and cannot select another producer run'
    )
    assert transfer.get('with', {}).get('platform') in {
        "${{ runner.os == 'macOS' && 'osx-arm64' || 'linux-64' }}",
        '${{ matrix.sdk }}',
    }, 'Each consumer requests its actual platform artifact rather than a sibling platform'
    guard = {'app': "runner.os != 'Windows'", **dict.fromkeys(NIGHTLY_MARKERS, NIGHTLY_GUARD)}.get(
        name
    )
    assert step_condition(transfer) == guard and not transfer.get('continue-on-error'), (
        'The native artifact action cannot be optional or bypassed'
    )
    for step in steps:
        assert str(step.get('env', {}).get('EDI_NATIVE_ARTIFACT', '1')) == '1', (
            'A later consumer step cannot switch artifact restoration back to compilation'
        )


def native_action_boundary(action):
    assert action['inputs']['run-id'].get('default') == '', (  # noqa: PLC1901 - absence and non-string defaults refuse
        'Native downloads default to the current run when no producer is supplied'
    )
    steps = action['runs']['steps']
    downloads = [step for step in steps if step.get('uses') == 'actions/download-artifact@v4']
    assert len(downloads) == 1, 'Native restoration selects exactly one addressed artifact'
    download = downloads[0]
    options = download['with']
    assert options.get('name') == 'edi-native-${{ inputs.platform }}', (
        'Native artifact names bind their platform'
    )
    assert options.get('path') == 'build/edi-native-artifact', (
        'The native checker reads the selected download directory'
    )
    assert options.get('run-id') == '${{ inputs.run-id }}', (
        'Native downloads address only the caller-selected producer or the current run'
    )
    assert options.get('github-token') == "${{ inputs.run-id != '' && github.token || '' }}", (
        'An explicit producer uses this repository token; default restoration stays same-run'
    )
    assert options.get('repository', '${{ github.repository }}') == '${{ github.repository }}', (
        'Native downloads address this repository'
    )
    assert not options.get('pattern') and not options.get('merge-multiple'), (
        'Native downloads cannot merge sibling artifacts'
    )
    assert not any('cache' in step.get('uses', '') for step in steps), (
        'A cache cannot replace native artifact transport'
    )
    for step in steps:
        assert not step.get('if') and not step.get('continue-on-error'), (
            'Every native selection step is required'
        )
    selectors = [step for step in steps if 'EDI_NATIVE_ARTIFACT=1' in step.get('run', '')]
    assert len(selectors) == 1, 'The consumer explicitly enables refuse-without-compile mode'
    assert selectors[0].get('env', {}).get('PRODUCER_RUN_ID') == '${{ inputs.run-id }}', (
        'The restore checker receives the same producer identity selected for download'
    )
    assert steps.index(download) < steps.index(selectors[0]), (
        'Artifact download precedes selection for restoration'
    )
    return selectors[0]['run']


@pytest.mark.parametrize(
    'damage',
    [
        'run-id',
        'repository',
        'name',
        'path',
        'pattern',
        'merge-multiple',
        'cache',
        'optional',
        'disabled',
        'mode',
    ],
)
def test_native_action_refuses_foreign_optional_and_fallback_routes(tmp_path, damage):
    action = yaml.safe_load((ROOT / '.github/actions/edi-native/action.yml').read_text())
    selector = native_action_boundary(action)
    import os  # noqa: PLC0415
    import subprocess  # noqa: PLC0415 - execute only the authored transport selector

    for run_id in ('', '431'):
        environment = tmp_path / ('job-environment-' + (run_id or 'current'))
        subprocess.run(
            [environment_bash(), '-e', '-c', selector],
            env={**os.environ, 'GITHUB_ENV': str(environment), 'PRODUCER_RUN_ID': run_id},
            check=True,
            capture_output=True,
            timeout=5,
        )
        expected = 'EDI_NATIVE_ARTIFACT=1\n'
        if run_id:
            expected += 'EDI_NATIVE_PRODUCER_RUN_ID=431\n'
        assert environment.read_text() == expected, (
            'The action selects artifact mode and forwards only the explicitly addressed producer'
        )
    for section, key, replacement in (
        ('download', 'github-token', '${{ secrets.OTHER_TOKEN }}'),
        ('selector', 'PRODUCER_RUN_ID', '${{ github.run_id }}'),
        ('input', 'default', '431'),
    ):
        changed = copy.deepcopy(action)
        download, select = changed['runs']['steps']
        spelling = {
            'download': download['with'],
            'selector': select['env'],
            'input': changed['inputs']['run-id'],
        }
        spelling[section][key] = replacement
        with pytest.raises(AssertionError):
            native_action_boundary(changed)
    mutant = copy.deepcopy(action)
    download = mutant['runs']['steps'][0]
    if damage == 'cache':
        download['uses'] = 'actions/cache/restore@v4'
    elif damage in {'optional', 'disabled'}:
        download['continue-on-error' if damage == 'optional' else 'if'] = (
            True if damage == 'optional' else 'false'
        )
    elif damage == 'mode':
        mutant['runs']['steps'][1]['run'] = 'echo EDI_NATIVE_ARTIFACT=0'
    else:
        download['with'][damage] = 'foreign'
    with pytest.raises(AssertionError):
        native_action_boundary(mutant)


def native_ancestors(data, name, trail=()):
    assert name in data, 'Artifact scheduling must reference an existing workflow job'
    assert name not in trail, 'Artifact scheduling cannot rely on a cyclic dependency graph'
    dependencies = data[name].get('needs', [])
    dependencies = [dependencies] if isinstance(dependencies, str) else dependencies
    ancestors = set(dependencies)
    for dependency in dependencies:
        ancestors.update(native_ancestors(data, dependency, (*trail, name)))
    return ancestors


def native_reusers_wait_for_producer(data):
    reusers = {
        name
        for name, job in data.items()
        if any(step.get('uses') == './.github/actions/edi-native' for step in job.get('steps', []))
    }
    assert reusers, 'The workflow must expose its real native artifact restoration routes'
    for name in reusers:
        assert 'native' in native_ancestors(data, name), (
            'Every same-run native artifact reuser must wait transitively for its producer'
        )
    return reusers


def test_every_actual_native_artifact_reuser_waits_for_completed_producer():
    data = jobs()
    reusers = native_reusers_wait_for_producer(data)
    for name in reusers:
        changed = copy.deepcopy(data)
        changed[name]['needs'] = ['changes', 'crysta-sdk']
        with pytest.raises(AssertionError, match='wait transitively'):
            native_reusers_wait_for_producer(changed)
    changed = copy.deepcopy(data)
    changed['future-unordered-consumer'] = {
        'steps': [{'uses': './.github/actions/edi-native'}],
        'needs': 'changes',
    }
    with pytest.raises(AssertionError, match='wait transitively'):
        native_reusers_wait_for_producer(changed)


def test_native_artifact_scheduling_accepts_real_transitive_edges_and_refuses_graph_escapes():
    data = {
        'changes': {},
        'crysta-sdk': {},
        'native': {'needs': ['changes', 'crysta-sdk']},
        'diagnostic-ready': {'needs': 'native'},
        'reader': {
            'needs': 'diagnostic-ready',
            'steps': [{'uses': './.github/actions/edi-native'}],
        },
    }
    assert native_reusers_wait_for_producer(data) == {'reader'}, (
        'A proven transitive wait may carry the artifact without imposing direct-edge duplication'
    )
    for escape in ('absent-job', 'reader'):
        changed = copy.deepcopy(data)
        changed['diagnostic-ready']['needs'] = escape
        with pytest.raises(AssertionError):
            native_reusers_wait_for_producer(changed)


def test_browser_diagnostics_wait_for_native_completion_without_requiring_native_test_success():
    job = copy.deepcopy(jobs()['app-wasm'])
    assert 'native' in native_ancestors(jobs(), 'app-wasm'), (
        'Browser restoration must wait until its same-run native producer has finished'
    )
    selector = 'needs.changes.outputs.wasm_build'
    assert selector in job['if'], 'The actual browser diagnostic retains its owed-input selector'
    job['if'] = job['if'].replace(selector, "'true'")
    states = {'changes': 'success', 'native': 'failure', 'crysta-sdk': 'success'}
    assert active(job, 'pull_request', states=states), (
        'Native test failure after upload must still permit independent browser diagnostics'
    )
    assert not active(job, 'pull_request', states=states, cancelled=True), (
        'A cancelled workflow must not launch independent browser diagnostics'
    )
    assert not active(job, 'pull_request', states=states, fork=True), (
        'Native diagnostic independence must retain the trusted-repository boundary'
    )
    assert not active(job, 'pull_request', states=states, core_only=True), (
        'Native diagnostic independence must retain the explicit core-only selection'
    )


@pytest.mark.parametrize('escape', ['producer-id', 'unguarded', 'implicit-success', 'optional'])
def test_native_reporting_requires_actual_build_and_retains_earlier_reds(escape):
    data = jobs()
    public_build_boundary(data, 'native', 'linux-64')
    bad = copy.deepcopy(data)
    steps = bad['native']['steps']
    build = next(step for step in steps if step.get('id') == 'build')
    use = next(step for step in steps if 'cpp-test' in step.get('run', ''))
    if escape == 'producer-id':
        build['id'] = 'unrelated'
    elif escape == 'unguarded':
        use['if'] = '!cancelled()'
    elif escape == 'implicit-success':
        use['if'] = "steps.build.outcome == 'success'"
    else:
        use['continue-on-error'] = True
    with pytest.raises(AssertionError):
        public_build_boundary(bad, 'native', 'linux-64')
