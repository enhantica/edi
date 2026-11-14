"""Local producer sequencing and immutable run transport, independent of remote builds."""

from __future__ import annotations

import copy
import hashlib
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from tests.fixtures.e09_t75_workflow import active
from tests.fixtures.native_process import environment_bash

ROOT = Path(__file__).resolve().parents[3]
PRODUCER = '.github/workflows/crysta-sdk.yml'
INPUTS = (
    PRODUCER,
    'tools/ci/crysta_source_receipt.py',
    'tools/ci/crysta_source_archive.py',
    '.github/actions/setup-pixi/action.yml',
    'tools/ci/crysta_sdk.py',
)


def document(path):
    return yaml.safe_load((ROOT / path).read_text())


def expanded_identity(template, *, platform='linux-64', pin='a7' * 20, recipe='c9' * 32):
    for name, value in {
        'matrix.platform': platform,
        'needs.resolve.outputs.sha': pin,
        'needs.resolve.outputs.recipe': recipe,
    }.items():
        template = template.replace('${{ ' + name + ' }}', value)
    assert '${{' not in template, 'Producer identity cannot depend on another mutable context'
    return template


def current_run_download(action):
    steps = action['runs']['steps']
    downloads = [step for step in steps if step.get('uses') == 'actions/download-artifact@v4']
    assert len(downloads) == 1, 'Each consumer takes one exact platform artifact'
    assert not any('cache' in step.get('uses', '') for step in steps), (
        'A consumer uses its producer artifact rather than cache availability'
    )
    selected = downloads[0]['with']
    assert selected.get('name') == 'crysta-sdk-${{ inputs.platform }}', (
        'Consumers select the exact platform SDK artifact'
    )
    assert selected.get('path') == 'crysta-sdk-archives', (
        'Consumers download SDK archives into their declared directory'
    )
    assert selected.get('run-id') in {None, '${{ github.run_id }}'}, (
        'Ordinary consumers cannot take an SDK from a foreign run'
    )
    assert selected.get('repository') in {None, '${{ github.repository }}'}, (
        'Ordinary consumers use artifacts from the current repository'
    )
    assert not selected.get('pattern') and not selected.get('merge-multiple'), (
        'Exact SDK downloads cannot merge wildcard artifact selections'
    )
    assert any(
        'CRYSTA_SDK_ARCHIVES=$GITHUB_WORKSPACE/crysta-sdk-archives' in step.get('run', '')
        for step in steps
    ), 'The actual reader receives the downloaded archive directory'


def test_sdk_producer_serializes_platform_pin_and_recipe_without_cancelling_waiters():
    workflow = document(PRODUCER)
    triggers = workflow.get('on', workflow.get(True))
    assert {'workflow_dispatch', 'workflow_call'} <= set(triggers), (
        'The producer supports both reusable and manually dispatched runs'
    )
    build = workflow['jobs']['build']
    assert build['needs'] == 'resolve', (
        'The producer resolves immutable inputs before building SDK archives'
    )
    assert build['concurrency']['cancel-in-progress'] is False, (
        'A competing SDK request cannot cancel an existing producer'
    )
    assert build['concurrency']['queue'] == 'max', (
        'Concurrent SDK requests retain the full waiting queue'
    )
    group = build['concurrency']['group']
    cache = next(step for step in build['steps'] if step.get('id') == 'cache')
    assert not cache['with'].get('restore-keys'), 'Another recipe cannot satisfy the exact cache'
    for identity in (group, cache['with']['key']):
        keys = [
            expanded_identity(identity),
            expanded_identity(identity, platform='osx-arm64'),
            expanded_identity(identity, platform='win-64'),
            expanded_identity(identity, pin='b8' * 20),
            expanded_identity(identity, recipe='d0' * 32),
        ]
        assert len(set(keys)) == 5, 'Each platform, source or recipe change invalidates identity'
        for field in (
            'matrix.platform',
            'needs.resolve.outputs.sha',
            'needs.resolve.outputs.recipe',
        ):
            changed = identity.replace('${{ ' + field + ' }}', 'constant')
            assert changed != identity, 'The identity challenge reaches its declared dimension'


def test_sdk_cold_and_warm_producers_publish_required_artifacts_only_after_success():
    build = document(PRODUCER)['jobs']['build']
    steps = build['steps']
    package = next(step for step in steps if 'sdk-pack' in step.get('run', ''))
    upload = next(step for step in steps if step.get('uses') == 'actions/upload-artifact@v4')
    assert steps.index(package) < steps.index(upload), (
        'SDK packaging finishes before its artifacts are uploaded'
    )
    assert upload['with']['name'] == 'crysta-sdk-${{ matrix.platform }}', (
        'Producers publish the artifact for their exact matrix platform'
    )
    assert upload['with']['path'] == 'crysta-sdk-archives', (
        'Producers upload archives from their declared output directory'
    )
    assert upload['with'].get('if-no-files-found') == 'error', (
        'A producer with missing archives must fail rather than report artifact delivery'
    )
    for hit, packed in [('false', True), ('true', False)]:
        outputs = {('cache', 'cache-hit'): hit}
        assert active(package, 'workflow_dispatch', outputs=outputs) is packed, (
            'Only a cold cache requires the SDK packaging step'
        )
        assert active(upload, 'workflow_dispatch', outputs=outputs), (
            'A warm producer still exports qualified bytes for its own consumers'
        )
        assert not active(
            upload, 'workflow_dispatch', outputs=outputs, states={'qualification': 'failure'}
        ), 'A failed qualification cannot publish an SDK artifact'


@pytest.mark.parametrize('platform', ['linux-64', 'osx-arm64', 'win-64'])
@pytest.mark.parametrize('index', range(13))
def test_sdk_producer_rejects_missing_empty_changed_and_misdirected_outputs(
    tmp_path, platform, index
):
    steps = document(PRODUCER)['jobs']['build']['steps']
    guard = next(
        step
        for step in steps
        if step.get('env', {}).get('CRYSTA_SDK_PLATFORM') == '${{ matrix.platform }}'
        and 'crysta-sdk-archives' in step.get('run', '')
    )
    upload = next(step for step in steps if step.get('uses') == 'actions/upload-artifact@v4')
    assert steps.index(guard) < steps.index(upload), (
        'Complete output validation precedes every SDK artifact upload'
    )
    for hit in ('false', 'true'):
        assert active(guard, 'workflow_dispatch', outputs={('cache', 'cache-hit'): hit}), (
            'Every cold and warm artifact crosses the same complete-output boundary'
        )
    assert guard['env']['SHA'] == '${{ needs.resolve.outputs.sha }}', (
        'Output validation uses the source identity resolved by this run'
    )
    assert guard['env']['CRYSTA_SDK_PLATFORM'] == '${{ matrix.platform }}'
    pin = 'a7' * 20
    archive = f'crysta-sdk-{pin}-{platform}.tar.gz'
    checksum = archive + '.sha256'
    source = f'crysta-src-{pin}.tar.gz'
    authored = b'independent opaque archive transport, not a scientific SDK'
    files = {
        archive: authored,
        checksum: (hashlib.sha256(authored).hexdigest() + '  ' + archive + '\n').encode(),
        source: b'independent source transport',
    }
    mutations = [
        (None, None),
        *[(name, None) for name in files],
        *[(name, b'') for name in files],
        (archive, b'changed archive'),
        (checksum, b'0' * 64 + b'  ' + archive.encode() + b'\n'),
        (checksum, files[checksum] * 2),
        (checksum, files[checksum] + b'extra record\n'),
        (checksum, files[checksum].replace(archive.encode(), b'../external.tar.gz')),
        (
            checksum,
            (hashlib.sha256(authored).hexdigest() + '  other-archive.tar.gz\n').encode(),
        ),
    ]
    assert len(mutations) == 13, 'Every independent transport damage remains declared'
    name, replacement = mutations[index]
    world = tmp_path / platform / str(index)
    destination = world / 'crysta-sdk-archives'
    destination.mkdir(parents=True)
    for member, data in files.items():
        if member != name or replacement is not None:
            (destination / member).write_bytes(replacement if member == name else data)
    if name == checksum and b'other-archive' in (replacement or b''):
        (destination / 'other-archive.tar.gz').write_bytes(authored)
        (destination / archive).write_bytes(b'unverified replacement')
    result = subprocess.run(
        [environment_bash(), '-e', '-c', guard['run']],
        cwd=world,
        env={
            **{key: value for key, value in os.environ.items() if key.casefold() != 'platform'},
            'SHA': pin,
            'Platform': 'x64',
            'CRYSTA_SDK_PLATFORM': platform,
        },
        capture_output=True,
        text=True,
        check=False,
        timeout=5,
    )
    assert (result.returncode == 0) == (name is None), (
        'The actual producer must reject missing, empty, corrupt or wrong-file '
        f'checksum transport: {platform} {name}'
    )


@pytest.mark.parametrize('changed', INPUTS)
def test_sdk_recipe_invalidates_every_local_producer_build_input(tmp_path, changed):
    steps = document(PRODUCER)['jobs']['resolve']['steps']
    recipe = next(step['run'] for step in steps if step.get('id') == 'recipe')
    for name in INPUTS:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, path)
    output = tmp_path / 'output'

    def resolve():
        output.write_text('')
        result = subprocess.run(
            [environment_bash(), '-e', '-c', recipe],
            cwd=tmp_path,
            env={**os.environ, 'GITHUB_OUTPUT': str(output)},
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        assert result.returncode == 0, 'The actual declared producer recipe must execute'
        fields = dict(line.split('=', 1) for line in output.read_text().splitlines())
        assert len(fields['sha']) == 64, (
            'The SDK build recipe is identified by a complete SHA256 digest'
        )
        return fields['sha']

    before = resolve()
    path = tmp_path / changed
    path.write_bytes(path.read_bytes() + b'\n# independent recipe invalidation control\n')
    assert resolve() != before, 'Changed producer build inputs cannot reuse an older SDK recipe'


def test_sdk_consumers_bind_same_run_artifacts_and_refuse_foreign_transport():
    action = document('.github/actions/crysta-sdk/action.yml')
    current_run_download(action)
    for mutation in ('run-id', 'repository', 'name', 'cache'):
        changed = copy.deepcopy(action)
        download = next(
            step
            for step in changed['runs']['steps']
            if step.get('uses') == 'actions/download-artifact@v4'
        )
        if mutation == 'cache':
            download['uses'] = 'actions/cache/restore@v4'
        else:
            download['with'][mutation] = 'foreign'
        with pytest.raises(AssertionError):
            current_run_download(changed)


def test_release_sdk_download_uses_the_exact_qualified_installer_run():
    steps = document('.github/workflows/release-publish.yml')['jobs']['publish']['steps']
    promotion = next(step for step in steps if 'tools/release/promote.py' in step.get('run', ''))
    download = next(
        step
        for step in steps
        if step.get('uses') == 'actions/download-artifact@v4'
        and step.get('with', {}).get('pattern') == 'crysta-sdk-*'
    )
    assert steps.index(promotion) < steps.index(download), (
        'Installer promotion is validated before downloading qualified SDK artifacts'
    )
    assert promotion['env']['INSTALLER_RUN'] == '${{ inputs.installer_run }}', (
        'Promotion validation receives the explicitly selected installer run'
    )
    assert download['with']['run-id'] == '${{ inputs.installer_run }}', (
        'Release SDK downloads use the explicitly qualified installer run'
    )
    assert download['with']['github-token'] == '${{ github.token }}', (
        'Qualified artifact downloads authenticate with the current repository token'
    )
    assert download['with']['merge-multiple'] is True, (
        'Release downloads merge the qualified platform archives into one directory'
    )
    assert download['with']['path'] == 'crysta-sdk-archives', (
        'Release SDK archives arrive in the declared consumer directory'
    )
    assert not any('cache' in step.get('uses', '') for step in steps), (
        'Publication must not substitute an opportunistic cache for qualified run artifacts'
    )


def test_native_sdk_matrix_and_windows_compiler_match_the_declared_platform_contract():
    build = document(PRODUCER)['jobs']['build']
    matrix = {row['platform']: row['runner'] for row in build['strategy']['matrix']['include']}
    assert matrix == {
        'linux-64': 'ubuntu-24.04',
        'osx-arm64': 'macos-15',
        'win-64': 'windows-2022',
    }, 'All native SDK platforms have an explicit matching architecture and supported host'
    assert build['strategy']['fail-fast'] is False, (
        'One platform failure cannot cancel another platform qualification'
    )
    steps = build['steps']
    compiler = next(step for step in steps if step.get('uses') == 'ilammy/msvc-dev-cmd@v1')
    assert compiler['if'] == "runner.os == 'Windows'", (
        'The Visual Studio environment is selected only on the actual Windows SDK host'
    )
    assert compiler['with']['toolset'] == '14.44', (
        'The SDK compiler toolset matches the locked Windows installer ABI family'
    )
    install = next(step for step in steps if step.get('uses') == './.github/actions/setup-pixi')
    pack = next(step for step in steps if 'sdk-pack' in step.get('run', ''))
    assert steps.index(compiler) < steps.index(install) < steps.index(pack), (
        'The selected compiler is active before required binding installation and full SDK pack'
    )
    assert '--skip crysta' not in str(install) + str(pack), (
        'Required binding-backed corpus policy remains installed rather than bypassed'
    )


def test_minimal_producer_checkout_does_not_remove_engine_qualification_inputs():
    steps = document(PRODUCER)['jobs']['build']['steps']
    checkout = next(step for step in steps if step.get('uses') == 'actions/checkout@v5')
    sparse = checkout['with']['sparse-checkout'].splitlines()
    assert checkout['with']['sparse-checkout-cone-mode'] is False, (
        'The SDK producer uses the declared explicit sparse checkout grammar'
    )
    assert set(sparse) == {'/*', '!/tests/', '!/docs/', '!/website/'}, (
        'Only unrelated Edi render/test trees are omitted from the local producer checkout'
    )
    engine = next(step for step in steps if 'git init -q' in step.get('run', ''))
    assert '--depth 1' in engine['run'] and '"$SHA"' in engine['run'], (
        'The engine qualification source is the exact resolved commit rather than a branch tip'
    )
    assert 'sparse' not in engine['run'], (
        'The complete engine CPP/corpus inputs remain in the independently checked-out source'
    )
    pack = next(step for step in steps if 'sdk-pack' in step.get('run', ''))
    assert '"$RUNNER_TEMP/crysta"' in pack['run'] and 'cpp-ci sdk-pack' in pack['run'], (
        'Qualification executes the owning engine recipe with all its declared cases'
    )


def test_compiler_cache_precedes_install_and_is_keyed_by_actual_engine_lock(tmp_path):
    steps = document(PRODUCER)['jobs']['build']['steps']
    inputs = next(step for step in steps if step.get('id') == 'compiler-inputs')
    cache = next(
        step
        for step in steps
        if step.get('with', {}).get('path') == '${{ runner.temp }}/crysta-ccache'
    )
    install = next(step for step in steps if step.get('uses') == './.github/actions/setup-pixi')
    pack = next(step for step in steps if 'sdk-pack' in step.get('run', ''))
    assert steps.index(inputs) < steps.index(cache) < steps.index(install) < steps.index(pack), (
        'Compiler objects are restored before required package installation and SDK compilation'
    )
    key, restore = cache['with']['key'], cache['with']['restore-keys']
    for identity in (key, restore):
        assert (
            '${{ matrix.platform }}' in identity
            and '${{ steps.compiler-inputs.outputs.lock }}' in identity
        ), 'Compiler-cache reuse preserves platform and actual engine lock identity'
    assert (
        '${{ needs.resolve.outputs.sha }}' in key
        and '${{ needs.resolve.outputs.sha }}' not in restore
    ), 'Writes retain source identity and cross-pin restores remain compiler-validated'
    engine = tmp_path / 'crysta'
    engine.mkdir()
    jobs = engine / 'tools' / 'ci' / 'build-jobs.sh'
    jobs.parent.mkdir(parents=True)
    jobs.write_text("printf '%s\\n' 4\n", encoding='utf-8', newline='\n')
    output, environment = tmp_path / 'output', tmp_path / 'environment'
    observed = []
    for content in (b'actual engine ABI lock', b'changed actual engine ABI lock'):
        (engine / 'pixi.lock').write_bytes(content)
        output.write_text('')
        result = subprocess.run(
            [environment_bash(), '-e', '-c', inputs['run']],
            cwd=tmp_path,
            env={
                **os.environ,
                'RUNNER_TEMP': str(tmp_path),
                'GITHUB_OUTPUT': str(output),
                'GITHUB_ENV': str(environment),
            },
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        assert result.returncode == 0, (
            'The actual engine-lock identity step executes independently'
        )
        fields = dict(line.split('=', 1) for line in output.read_text().splitlines())
        assert fields['lock'] == hashlib.sha256(content).hexdigest(), (
            'The cache fingerprint comes from the cloned engine lock bytes, not the Edi host lock'
        )
        observed.append(fields['lock'])
    assert observed[0] != observed[1], (
        'Changing the actual engine lock invalidates the exact object-cache identity'
    )


def test_future_sdk_publication_retains_all_promoted_platform_artifacts():
    publisher = document('.github/workflows/release-publish.yml')['jobs']['publish']['steps']
    copy = next(
        step['run']
        for step in publisher
        if 'publication/assets' in step.get('run', '') and 'crysta-sdk-' in step['run']
    )
    assert 'win-64' in copy and 'linux-64' in copy and 'osx-arm64' in copy, (
        'Future publication carries all qualified platform SDKs from the promoted run'
    )


def compiler_cache_path_policy(workflow):
    build = workflow['jobs']['build']
    assert 'CCACHE_BASEDIR' not in workflow.get('env', {}), (
        'Workflow-wide cache configuration cannot rewrite absolute fixture source paths'
    )
    assert 'CCACHE_BASEDIR' not in build.get('env', {}), (
        'Producer job cache configuration preserves actual absolute __FILE__ identities'
    )
    for step in build['steps']:
        assert 'CCACHE_BASEDIR' not in step.get('env', {}), (
            'Individual producer steps cannot enable unsafe fixture path rewriting'
        )
        assert not re.search(r'CCACHE_BASEDIR\s*=', step.get('run', '')), (
            'Shell environment writes cannot restore unsafe cache base-directory rewriting'
        )
    setup = next(step for step in build['steps'] if step.get('id') == 'compiler-inputs')
    assert 'CCACHE_COMPILERCHECK=content' in setup['run'], (
        'Cross-pin cache reuse checks actual compiler bytes while preserving source-path semantics'
    )


def test_compiler_cache_preserves_absolute_fixture_paths_and_rejects_unsafe_rewrites():
    workflow = document(PRODUCER)
    compiler_cache_path_policy(workflow)
    for location in ('workflow', 'job', 'step', 'shell'):
        changed = copy.deepcopy(workflow)
        build = changed['jobs']['build']
        if location == 'workflow':
            changed.setdefault('env', {})['CCACHE_BASEDIR'] = '${{ runner.temp }}'
        elif location == 'job':
            build.setdefault('env', {})['CCACHE_BASEDIR'] = '${{ runner.temp }}'
        elif location == 'step':
            build['steps'][0].setdefault('env', {})['CCACHE_BASEDIR'] = '${{ runner.temp }}'
        else:
            build['steps'].append({'run': 'echo "CCACHE_BASEDIR=$RUNNER_TEMP" >> "$GITHUB_ENV"'})
        with pytest.raises(AssertionError):
            compiler_cache_path_policy(changed)


def windows_checkout_guard(steps):
    checkout = next(step for step in steps if step.get('uses') == 'actions/checkout@v5')
    guards = [step for step in steps if 'core.protectNTFS' in step.get('run', '')]
    assert len(guards) == 1, 'One explicit Windows index-admission guard precedes checkout'
    guard = guards[0]
    assert steps.index(guard) < steps.index(checkout), (
        'Windows Git path admission must be configured before index validation in checkout'
    )
    assert guard.get('if') == "runner.os == 'Windows'", (
        'The NTFS compatibility boundary applies only on the Windows host'
    )
    commands = [line.split() for line in guard['run'].splitlines() if line.strip()]
    assert ['git', 'config', '--global', 'core.longpaths', 'true'] in commands, (
        'The checkout process inherits long-path support before its index is populated'
    )
    assert ['git', 'config', '--global', 'core.protectNTFS', 'false'] in commands, (
        'Sparse checkout still validates excluded historical reserved fixture paths'
    )
    return guard


def test_windows_checkout_configures_index_admission_before_sparse_materialization(tmp_path):
    steps = document(PRODUCER)['jobs']['build']['steps']
    guard = windows_checkout_guard(steps)
    isolated = {**os.environ, 'GIT_CONFIG_GLOBAL': str(tmp_path / 'global-git-config')}
    result = subprocess.run(
        [environment_bash(), '-e', '-c', guard['run']],
        env=isolated,
        capture_output=True,
        check=False,
        timeout=5,
    )
    assert result.returncode == 0, 'The actual pre-checkout commands must execute independently'
    for key, expected in [('core.longpaths', 'true'), ('core.protectNTFS', 'false')]:
        value = subprocess.check_output(
            ['git', 'config', '--global', key], env=isolated, text=True
        )
        assert value.strip() == expected, (
            'The child checkout inherits the exact Git admission setting'
        )
    for mutation in ('late', 'no-windows', 'longpaths', 'protectNTFS', 'false'):
        changed = copy.deepcopy(steps)
        index = next(
            i for i, step in enumerate(changed) if 'core.protectNTFS' in step.get('run', '')
        )
        if mutation == 'late':
            changed.append(changed.pop(index))
        elif mutation == 'no-windows':
            changed[index]['if'] = "runner.os != 'Windows'"
        else:
            changed[index]['run'] = changed[index]['run'].replace(mutation, 'invalid')
        with pytest.raises(AssertionError):
            windows_checkout_guard(changed)


def test_actual_sparse_checkout_omits_reserved_fixture_and_keeps_producer_inputs(tmp_path):
    source, target = tmp_path / 'source', tmp_path / 'target'
    source.mkdir()
    files = {
        'tests/fixtures/reserved/aux.edi': b'historical reserved fixture',
        'docs/index.md': b'documentation',
        'website/index.html': b'website',
        'pixi.toml': b'locked producer manifest',
        'tools/ci/crysta-source.sh': b'producer identity script',
        '.github/actions/setup-pixi/action.yml': b'producer setup action',
    }
    for name, data in files.items():
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    env = {**os.environ, 'GIT_CONFIG_GLOBAL': str(tmp_path / 'global-git-config')}

    def git(directory, *arguments):
        subprocess.run(
            ['git', '-C', str(directory), *arguments],
            env=env,
            check=True,
            capture_output=True,
            timeout=5,
        )

    git(source, 'init', '-q')
    git(source, 'config', 'core.protectNTFS', 'false')
    git(source, 'add', '.')
    git(
        source,
        '-c',
        'user.name=fixture',
        '-c',
        'user.email=fixture@example.invalid',
        'commit',
        '-qm',
        'independent sparse transport',
    )
    subprocess.run(
        ['git', 'clone', '-q', '--no-checkout', str(source), str(target)],
        env=env,
        check=True,
        capture_output=True,
        timeout=5,
    )
    steps = document(PRODUCER)['jobs']['build']['steps']
    guard = windows_checkout_guard(steps)
    subprocess.run(
        [environment_bash(), '-e', '-c', guard['run']],
        env=env,
        check=True,
        capture_output=True,
        timeout=5,
    )
    checkout = next(step for step in steps if step.get('uses') == 'actions/checkout@v5')
    git(target, 'config', 'core.sparseCheckout', 'true')
    (target / '.git/info/sparse-checkout').write_text(checkout['with']['sparse-checkout'])
    git(target, 'read-tree', '-mu', 'HEAD')
    for name, data in files.items():
        if name.split('/')[0] in {'tests', 'docs', 'website'}:
            assert not (target / name).exists(), (
                'Excluded historical fixtures are not materialized'
            )
        else:
            assert (target / name).read_bytes() == data, 'Producer configuration remains complete'


def compiler_restore_scope(object_cache, archive_cache):
    prefixes = [
        line.strip() for line in object_cache['with']['restore-keys'].splitlines() if line.strip()
    ]
    assert prefixes == [
        'crysta-objects-v1-${{ matrix.platform }}-${{ steps.compiler-inputs.outputs.lock }}-',
        'crysta-objects-v1-${{ matrix.platform }}-',
    ], 'Compiler objects restore exact lock first, then the same platform with content validation'
    assert not archive_cache['with'].get('restore-keys'), (
        'A qualified SDK archive must never use the broader compiler-object fallback'
    )


def test_compiler_objects_cross_lock_fallback_never_escapes_platform_or_qualified_archive():
    steps = document(PRODUCER)['jobs']['build']['steps']
    objects = next(step for step in steps if step.get('id') == 'compiler-cache')
    archive = next(step for step in steps if step.get('id') == 'cache')
    compiler_restore_scope(objects, archive)
    for escape in ('cross-platform', 'broad', 'reordered', 'qualified-archive'):
        bad_objects, bad_archive = copy.deepcopy(objects), copy.deepcopy(archive)
        prefixes = bad_objects['with']['restore-keys'].splitlines()
        if escape == 'cross-platform':
            prefixes[-1] = 'crysta-objects-v1-linux-64-'
        elif escape == 'broad':
            prefixes.append('crysta-objects-v1-')
        elif escape == 'reordered':
            prefixes.reverse()
        else:
            bad_archive['with']['restore-keys'] = 'crysta-sdk-v3-${{ matrix.platform }}-'
        bad_objects['with']['restore-keys'] = '\n'.join(prefixes)
        with pytest.raises(AssertionError):
            compiler_restore_scope(bad_objects, bad_archive)


def no_ambiguous_windows_platform_environment(node):
    if isinstance(node, dict):
        environment = node.get('env', {})
        if isinstance(environment, dict):
            assert not any(str(name).casefold() == 'platform' for name in environment), (
                'SDK identities must use task-specific names instead of MSVC Platform aliases'
            )
        script = node.get('run', '')
        assert not isinstance(script, str) or not re.search(
            r'\$(?:platform\b|\{platform(?:[}:]))', script, re.IGNORECASE
        ), 'Windows workflow shell cannot read a case-ambiguous inherited Platform identity'
        for value in node.values():
            no_ambiguous_windows_platform_environment(value)
    elif isinstance(node, list):
        for value in node:
            no_ambiguous_windows_platform_environment(value)


@pytest.mark.parametrize('workflow', [PRODUCER, '.github/workflows/installers.yml'])
def test_windows_sdk_workflows_refuse_case_ambiguous_platform_environment_routes(workflow):
    source = document(workflow)
    no_ambiguous_windows_platform_environment(source)
    for spelling in ('PLATFORM', 'Platform', 'platform'):
        for scope in ('workflow', 'job', 'step'):
            changed = copy.deepcopy(source)
            job = next(job for job in changed['jobs'].values() if job.get('steps'))
            target = changed if scope == 'workflow' else job if scope == 'job' else job['steps'][0]
            target.setdefault('env', {})[spelling] = '${{ matrix.platform }}'
            with pytest.raises(AssertionError, match='task-specific'):
                no_ambiguous_windows_platform_environment(changed)
        changed = copy.deepcopy(source)
        next(job for job in changed['jobs'].values() if job.get('steps'))['steps'][0]['run'] = (
            'printf "%s" "$' + spelling + '"'
        )
        with pytest.raises(AssertionError, match='case-ambiguous'):
            no_ambiguous_windows_platform_environment(changed)


def test_runtime_audit_fetches_the_immutable_source_history_its_collection_reads():
    workflow = document('.github/workflows/ci.yml')
    audit = workflow['jobs']['audit']
    assert any('per-pr-audit' in step.get('run', '') for step in audit['steps'])
    checkouts = [step for step in audit['steps'] if step.get('uses') == 'actions/checkout@v5']
    assert len(checkouts) == 1 and checkouts[0].get('with', {}).get('fetch-depth') == 0
