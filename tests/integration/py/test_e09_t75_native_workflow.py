"""D6/I34 topology, using the accepted restore boundary at 12a297d28."""

import copy
import shlex
from pathlib import Path

import pytest
import yaml

from tests.fixtures.e09_t75_workflow import active, reached
from tests.integration.py.ci_runner_contract import platform_job, self_hosted_runners

ROOT = Path(__file__).resolve().parents[3]
CONSUMERS = ['audit', 'core', 'system', 'notebooks', 'cli-python', 'docs', 'app']


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
    # The public repository builds locally in each job: its private SDK object
    # code cannot be uploaded. The private repository's artifact gates below stay.
    job = data[name]
    runners = self_hosted_runners(job)
    assert all(runner[0] == 'github-hosted' for runner in runners), (
        'public native jobs must use the approved standard hosted platforms'
    )
    if platform is not None:
        expected_os = {'linux-64': 'Linux', 'osx-arm64': 'macOS'}[platform]
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
        ) and '||' not in str(job.get('if', '')), (
            'public SDK native jobs must retain the positive trusted-pull-request fork boundary'
        )
        for core_only in (False, True):
            assert not active(
                job,
                'pull_request',
                fork=True,
                core_only=core_only,
                states={'changes': 'success', 'native': 'success', 'core': 'success'},
            ), 'every public SDK job must refuse forks with either core-only input'
    for event in ('pull_request', 'push', 'workflow_dispatch'):
        assert active(
            job, event, states={'changes': 'success', 'native': 'success', 'core': 'success'}
        ), 'every full trusted event must reach its public SDK job'
        assert active(
            job,
            event,
            core_only=True,
            states={'changes': 'success', 'native': 'success', 'core': 'success'},
        ) == (name in {'native', 'core', 'system'}), (
            'core-only repairs retain native/core and skip every downstream public SDK job'
        )
    assert job.get('environment') == 'crysta-sdk', (
        'public native builds must use the protected private SDK environment'
    )
    needs = job.get('needs')
    needs = [needs] if isinstance(needs, str) else needs
    expected_needs = {'changes'}
    if name == 'notebooks':
        expected_needs |= {'native', 'core'}
    elif name not in {'native', 'core', 'system'}:
        expected_needs.add('core')
    assert set(needs or []) == expected_needs, (
        'public native jobs resolve the source once and build locally rather than download objects'
    )
    assert job.get('env', {}).get('CRYSTA_SOURCE_SHA') == (
        '${{ needs.changes.outputs.crysta_sha }}'
    ), 'each public native build must consume the workflow-resolved SDK source identity'
    steps = job['steps']
    builds = [
        (i, step)
        for i, step in enumerate(steps)
        if shlex.split(step.get('run', '')) == ['pixi', 'run', 'core-build']
    ]
    assert len(builds) == 1, 'every public native job must have one actual local native build'
    index, build = builds[0]
    assert (
        build.get('if') == 'github.event.pull_request.head.repo.fork == false'
        if name == 'notebooks'
        else 'if' not in build
    ) and not build.get('continue-on-error'), (
        'the public local native build must be required whenever its protected job executes'
    )
    for step in steps:
        environment = {**job.get('env', {}), **step.get('env', {})}
        assert str(environment.get('EDI_NATIVE_ARTIFACT', '0')) == '0', (
            'public native jobs must build locally and cannot select engine object restoration'
        )
        assert 'edi_native.py' not in step.get('run', '') and 'edi-native-' not in str(
            step.get('with', {})
        ), 'public native workflows must neither pack nor transfer private engine object artifacts'
    if name == 'native':
        assert build.get('env', {}).get('EDI_CORE_TARGETS') == 'edi_tests', (
            'the public native producer must include the independently required C++ unit target'
        )
        first_use = 'cpp-test'
    else:
        first_use = FIRST_USE[name]
    uses = [i for i, step in enumerate(steps) if first_use in step.get('run', '')]
    assert uses and index < uses[0], (
        'each public native job must build its local objects before the first declared native use'
    )
    assert (
        steps[uses[0]].get('if') == 'github.event.pull_request.head.repo.fork == false'
        if name == 'notebooks'
        else 'if' not in steps[uses[0]]
    ) and not steps[uses[0]].get('continue-on-error'), (
        'the first public native use must execute whenever the protected build job succeeds'
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


def test_d6_one_unfiltered_native_matrix_uploads_the_prescribed_artifacts():
    data = jobs()
    assert 'native' in data, ' I34 requires the one native producer job'
    native = data['native']
    if public_profile(data):
        for platform in ('linux-64', 'osx-arm64'):
            public_build_boundary(data, 'native', platform)
        assert {leg.get('sdk') for leg in native['strategy']['matrix']['include']} == {
            'linux-64',
            'osx-arm64',
        }, 'the public native matrix must compile against both independently prescribed SDKs'
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
    for step in (build, pack, upload):
        for event in ('pull_request', 'push', 'workflow_dispatch'):
            reached(job, event)
            reached(step, event)
    environment = {**job.get('env', {}), **build.get('env', {})}
    assert environment.get('EDI_CORE_TARGETS') == 'edi_tests', (
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
            {'run': 'pixi run core-build', 'env': {'EDI_CORE_TARGETS': 'edi_tests'}},
            {'run': 'pixi run python tools/ci/edi_native.py pack --out "$RUNNER_TEMP/edi-native"'},
            {'uses': 'actions/upload-artifact@v5'},
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
    # The public profile keeps no object-transfer steps. Reuse every existing
    # producer escape against that independently declared hosted-build boundary.
    public_job = {
        'runs-on': '${{ matrix.runner }}',
        'environment': 'crysta-sdk',
        'if': 'github.event.pull_request.head.repo.fork == false',
        'needs': 'changes',
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
            {'run': 'pixi run core-build', 'env': {'EDI_CORE_TARGETS': 'edi_tests'}},
            {'run': 'pixi run --skip-deps cpp-test'},
        ],
    }
    public_build_boundary({'native': public_job}, 'native', 'linux-64')
    public_mutant = copy.deepcopy(public_job)
    if defect == 'missing-build':
        public_mutant['steps'].pop(0)
    elif defect == 'upload-first':
        public_mutant['steps'].insert(
            0,
            {
                'uses': 'actions/upload-artifact@v5',
                'with': {'name': 'edi-native-linux-64'},
            },
        )
    elif defect == 'pack-first':
        public_mutant['steps'].insert(
            0, {'run': 'pixi run python tools/ci/edi_native.py pack --out native-objects'}
        )
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
        disabled_use['steps'][1]['if'] = False
        with pytest.raises(AssertionError, match='first public native use'):
            public_build_boundary({'native': disabled_use}, 'native', 'linux-64')
