"""Failed qualification preserves compiled objects without promoting an unqualified SDK."""

import copy
import os
import subprocess
from pathlib import Path

import pytest
import yaml

from tests.fixtures.e09_t75_workflow import active
from tests.fixtures.native_process import environment_bash

ROOT = Path(__file__).resolve().parents[3]
STORE = './.github/actions/store'
OBJECTS = '${{ runner.temp }}/crysta-ccache'


def sdk_object_save(step):
    return step.get('uses') == STORE and step.get('with', {}).get('path') == OBJECTS


def producer():
    return yaml.safe_load((ROOT / '.github/workflows/crysta-sdk.yml').read_text())['jobs']['build']


def object_cache_boundary(job):
    steps = job['steps']
    restores = [step for step in steps if step.get('id') == 'compiler-cache']
    saves = [step for step in steps if sdk_object_save(step)]
    assert len(restores) == len(saves) == 1, (
        'One explicit restore/save pair owns SDK compiler objects'
    )
    restore, save = restores[0], saves[0]
    assert not any(
        step.get('uses', '').startswith(('actions/cache/save@', 'actions/cache@'))
        and step.get('with', {}).get('path') == OBJECTS
        for step in steps
    ), 'The checked save is the only route that can publish these compiler objects'
    assert restore['uses'] == 'actions/cache/restore@v4', (
        'Compiler restore cannot depend on a successful-job post-save'
    )
    assert save['with']['key'] == restore['with']['key'] and save['with'].get('ccache') == (
        'pixi run --manifest-path "$RUNNER_TEMP/crysta/pixi.toml" -e cpp-ci --skip-deps python'
    ), 'Saved objects keep their exact restored identity and undergo compiler-cache inspection'
    inputs = next(step for step in steps if step.get('id') == 'compiler-inputs')
    install = next(step for step in steps if step.get('uses') == './.github/actions/setup-pixi')
    build = next(step for step in steps if 'cpp-ci sdk-pack' in step.get('run', ''))
    assert (
        steps.index(inputs)
        < steps.index(restore)
        < steps.index(install)
        < steps.index(build)
        < steps.index(save)
    ), 'Cache restore precedes the sole bootstrap; save follows its build attempt'
    for hit, inputs_outcome, restore_outcome, cancelled in [
        ('false', 'success', 'success', False),
        ('true', 'success', 'success', False),
        ('false', 'failure', 'success', False),
        ('false', 'success', 'failure', False),
        ('false', 'skipped', 'skipped', False),
        ('false', 'success', 'success', True),
    ]:
        expected = (
            hit == 'false' and inputs_outcome == restore_outcome == 'success' and not cancelled
        )
        assert (
            active(
                save,
                'workflow_dispatch',
                outputs={
                    ('cache', 'cache-hit'): hit,
                    ('compiler-inputs', 'outcome'): inputs_outcome,
                    ('compiler-cache', 'outcome'): restore_outcome,
                },
                states={'qualification': 'failure'},
                cancelled=cancelled,
            )
            == expected
        ), 'Only valid cold restores save objects after a noncancelled failure'
    archive = next(step for step in steps if step.get('id') == 'cache')
    archive_save = next(
        step
        for step in steps
        if step.get('with', {}).get('key') == ('${{ steps.cache.outputs.cache-primary-key }}')
    )
    assert archive['uses'] == 'actions/cache/restore@v4' and archive_save.get('uses') == STORE, (
        'Qualified SDK archives use a separate restore and checked save'
    )
    assert archive['with']['path'] == archive_save['with']['path'] == 'crysta-sdk-archives', (
        'The checked SDK archive save retains the exact restored archive payload'
    )
    check = next(step for step in steps if 'SDK checksum does not bind' in step.get('run', ''))
    assert steps.index(build) < steps.index(check) < steps.index(archive_save), (
        'Cold archives are checked after the build and before they can be cached'
    )
    for hit, qualification in [('true', 'success'), ('false', 'success'), ('false', 'failure')]:
        assert active(
            archive_save,
            'workflow_dispatch',
            outputs={('cache', 'cache-hit'): hit},
            states={'qualification': qualification},
        ) == (hit == 'false' and qualification == 'success'), (
            'The archive save must not publish a warm restore or a failed qualification'
        )
    assert install['with'].get('cache') is False, (
        'SDK archives and compiler objects survive without redundant whole builder environments'
    )
    assert install['with'].get('environments') == 'cpp-ci', (
        'SDK bootstrap installs only the environment used by its actual pack command'
    )


def test_compiler_cache_survives_failed_qualification_and_refuses_missing_or_wrong_save():
    job = producer()
    object_cache_boundary(job)
    for damage in [
        'missing-save',
        'wrong-key',
        'success-only',
        'unconditional',
        'other-environment',
        'redundant-builder-environment',
    ]:
        changed = copy.deepcopy(job)
        save = next(step for step in changed['steps'] if sdk_object_save(step))
        if damage == 'missing-save':
            changed['steps'].remove(save)
        elif damage == 'wrong-key':
            save['with']['key'] = 'foreign-objects'
        elif damage == 'success-only':
            save['if'] = 'success()'
        elif damage == 'unconditional':
            save['if'] = '!cancelled()'
        elif damage == 'redundant-builder-environment':
            install = next(
                step
                for step in changed['steps']
                if step.get('uses') == './.github/actions/setup-pixi'
            )
            install['with']['cache'] = True
        else:
            install = next(
                step
                for step in changed['steps']
                if step.get('uses') == './.github/actions/setup-pixi'
            )
            install['with']['environments'] = 'default'
        with pytest.raises(AssertionError):
            object_cache_boundary(changed)


def test_selected_windows_bootstrap_uses_ninja_and_wrapper_keeps_other_callers_default(tmp_path):
    job = producer()
    steps = job['steps']
    inputs = next(step for step in steps if step.get('id') == 'compiler-inputs')
    (tmp_path / 'crysta').mkdir()
    (tmp_path / 'crysta/pixi.lock').write_bytes(b'independent real lock bytes')
    jobs = tmp_path / 'crysta' / 'tools' / 'ci' / 'build-jobs.sh'
    jobs.parent.mkdir(parents=True)
    jobs.write_text("printf '%s\\n' 6\n", encoding='utf-8', newline='\n')
    for platform in ['Windows', 'Linux', 'macOS']:
        output, environment = tmp_path / 'output', tmp_path / 'environment'
        output.write_text('', encoding='utf-8')
        environment.write_text('', encoding='utf-8')
        result = subprocess.run(
            [environment_bash(), '-e', '-c', inputs['run']],
            cwd=tmp_path,
            env={
                **os.environ,
                'RUNNER_TEMP': str(tmp_path),
                'RUNNER_OS': platform,
                'GITHUB_OUTPUT': str(output),
                'GITHUB_ENV': str(environment),
            },
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        assert result.returncode == 0, 'The actual cache/bootstrap environment program executes'
        assert 'CMAKE_BUILD_PARALLEL_LEVEL=6' in environment.read_text().splitlines(), (
            'Bootstrap receives the checked-out engine CPU/memory cap unchanged'
        )
        assert ('CMAKE_GENERATOR=Ninja' in environment.read_text().splitlines()) == (
            platform == 'Windows'
        ), 'Only Windows bootstrap selects Ninja so MSVC uses the compiler launcher'
    jobs.unlink()
    missing = subprocess.run(
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
    assert missing.returncode != 0, (
        'Bootstrap refuses an unavailable engine resource cap instead of continuing unbounded'
    )
    sdk_pixi_install_boundary(job)


def sdk_pixi_install_boundary(job):
    setup_action = './.github/actions/setup-pixi'
    wrapper = yaml.safe_load((ROOT / '.github/actions/setup-pixi/action.yml').read_text())
    defaults = {name: entry['default'] for name, entry in wrapper['inputs'].items()}
    assert defaults == {
        'manifest-path': 'pixi.toml',
        'environments': 'default',
        'cache': 'true',
        'install': 'true',
    }, 'Installing callers keep the main manifest, default environment and cached installation'

    upstream = [
        step
        for step in wrapper['runs']['steps']
        if step.get('uses', '').startswith('prefix-dev/setup-pixi@')
    ]
    assert len(upstream) == 1, 'One upstream Pixi action owns the wrapper installation'
    forwarded = upstream[0]['with']
    assert forwarded['manifest-path'] == (
        "${{ inputs.install == 'true' && inputs.manifest-path "
        "|| format('{0}/pixi.toml', github.workspace) }}"
    ), 'Installing callers keep their manifest and launcher-only setup reads the edi workspace'
    assert (
        forwarded['environments'] == "${{ inputs.install == 'true' && inputs.environments || '' }}"
    ), 'Installing callers keep their environment; launcher-only setup selects none'
    assert forwarded['cache'] == "${{ inputs.install == 'true' && inputs.cache || 'false' }}", (
        'Only installing callers can use the selected environment cache'
    )
    assert forwarded['run-install'] == forwarded['frozen'] == '${{ inputs.install }}', (
        'Only installing callers enable the upstream install and its frozen lock'
    )

    steps = job['steps']
    setup = [step for step in steps if step.get('uses') == setup_action]
    install = [step for step in steps if 'pixi install' in step.get('run', '')]
    assert len(setup) == len(install) == 1, (
        'The SDK has one launcher setup and one explicit install'
    )
    setup, install = setup[0], install[0]
    assert setup['with'] == {
        'manifest-path': '${{ runner.temp }}/crysta/pixi.toml',
        'environments': 'cpp-ci',
        'cache': False,
        'install': False,
    }, 'The SDK pins Pixi from the engine manifest without a cached upstream install'
    assert install['run'].strip() == (
        'pixi install --manifest-path "$RUNNER_TEMP/crysta/pixi.toml" -e cpp-ci --frozen'
    ), 'The SDK installs its locked cpp-ci environment explicitly'
    run_defaults = job['defaults']['run']
    assert install.get('shell', run_defaults['shell']) == 'python3 tools/ci/public_log.py {0}', (
        'The SDK environment install runs inside the CI output filter'
    )
    build = next(step for step in steps if 'cpp-ci sdk-pack' in step.get('run', ''))
    assert steps.index(setup) < steps.index(install) < steps.index(build), (
        'The filtered install uses the pinned Pixi launcher and precedes SDK compilation'
    )
    assert not install.get('continue-on-error'), 'A failed frozen install prevents SDK compilation'
    for hit in ('true', 'false'):
        outputs = {('cache', 'cache-hit'): hit}
        assert (
            active(setup, 'workflow_dispatch', outputs=outputs)
            == active(install, 'workflow_dispatch', outputs=outputs)
            == (hit == 'false')
        ), 'Only a cold SDK archive lookup sets up Pixi and installs cpp-ci'


def test_failed_native_observations_are_retained_without_promoting_an_sdk():
    steps = producer()['steps']
    evidence = next(
        step
        for step in steps
        if step.get('with', {}).get('artifact')
        == 'crysta-sdk-red-${{ matrix.platform }}-${{ needs.resolve.outputs.sha }}'
    )
    artifact = next(
        step
        for step in steps
        if step.get('with', {}).get('artifact') == 'crysta-sdk-${{ matrix.platform }}'
    )
    assert evidence['uses'] == artifact['uses'] == STORE, (
        'Failed observations and qualified SDKs undergo checked publication'
    )
    summary = next(step for step in steps if 'tools/ci/sdk_red_summary.py' in step.get('run', ''))
    assert (
        steps.index(summary) < steps.index(evidence)
        and summary['env']['SHA'] == '${{ needs.resolve.outputs.sha }}'
        and '"$RUNNER_TEMP/crysta/build/sdk-pack-red/$SHA"' in summary['run']
        and '"$RUNNER_TEMP/sdk-red/summary.json"' in summary['run']
        and evidence['with']['path'] == '${{ runner.temp }}/sdk-red/summary.json'
    ), 'The real summary consumes pinned failed observations and only its checked output is kept'
    for state, cancelled in [('success', False), ('failure', False), ('failure', True)]:
        context = {'states': {'qualification': state}, 'cancelled': cancelled}
        assert active(summary, 'workflow_dispatch', **context) == active(
            evidence, 'workflow_dispatch', **context
        ), 'Failure evidence is produced under the same condition that permits its publication'
        assert active(evidence, 'workflow_dispatch', **context) == (
            state == 'failure' and not cancelled
        ), 'Failed native observations are retained without promoting an sdk.'
        assert active(artifact, 'workflow_dispatch', **context) == (
            state == 'success' and not cancelled
        ), 'Failure evidence can never satisfy successful SDK transport'


def installer_cache_boundary(job):
    steps = job['steps']
    restore = next(step for step in steps if step.get('id') == 'compiler-cache')
    save = next(step for step in steps if step.get('name') == 'Save installer compiler objects')
    build = next(
        step
        for step in steps
        if step.get('name') == 'Build desktop bundle and CLI with the qualified SDK'
    )
    assert restore['uses'] == 'actions/cache/restore@v4', (
        'Installer cache identity and failure diagnostics remain unconditional.'
    )
    assert save['uses'] == STORE and save['with']['ccache'] == (
        'pixi run --manifest-path tools/installer/pixi.toml python'
    ), 'The installer save inspects objects using its locked compiler environment'
    assert {key: save['with'][key] for key in ('path', 'key')} == {
        key: restore['with'][key] for key in ('path', 'key')
    }, 'Installer cache identity and failure diagnostics remain unconditional.'
    assert steps.index(restore) < steps.index(build) < steps.index(save), (
        'Installer cache identity and failure diagnostics remain unconditional.'
    )
    for outcome, cancelled in [
        ('success', False),
        ('failure', False),
        ('skipped', False),
        ('success', True),
    ]:
        assert active(
            save,
            'pull_request',
            outputs={('compiler-cache', 'outcome'): outcome},
            states={'qualification': 'failure'},
            cancelled=cancelled,
        ) == (outcome == 'success' and not cancelled), (
            'Installer cache identity and failure diagnostics remain unconditional.'
        )


def test_installer_preserves_objects_after_failure_with_the_same_explicit_cache_boundary():
    document = yaml.safe_load((ROOT / '.github/workflows/installers.yml').read_text())
    job = next(
        job
        for job in document['jobs'].values()
        if any(
            step.get('name') == 'Build desktop bundle and CLI with the qualified SDK'
            for step in job.get('steps', [])
        )
    )
    installer_cache_boundary(job)
    for defect in ('success-only', 'unconditional', 'wrong-key', 'before-build'):
        damaged = copy.deepcopy(job)
        save = next(
            step
            for step in damaged['steps']
            if step.get('name') == 'Save installer compiler objects'
        )
        if defect == 'success-only':
            save['if'] = 'success()'
        elif defect == 'unconditional':
            save['if'] = '!cancelled()'
        elif defect == 'wrong-key':
            save['with']['key'] = 'foreign-objects'
        else:
            damaged['steps'].remove(save)
            damaged['steps'].insert(0, save)
        with pytest.raises(AssertionError):
            installer_cache_boundary(damaged)


def test_failed_sdk_pack_reports_cache_stats_then_keeps_its_failure(tmp_path):
    build = next(step for step in producer()['steps'] if 'cpp-ci sdk-pack' in step.get('run', ''))
    (tmp_path / 'crysta').mkdir()
    tools = tmp_path / 'bin'
    tools.mkdir()
    pixi = tools / 'pixi'
    pixi.write_text(
        '#!/usr/bin/env bash\n'
        'echo "$*" >> "$CACHE_WITNESS"\n'
        'case "$*" in *sdk-pack*) exit 23;; esac\n',
        encoding='utf-8',
        newline='\n',
    )
    pixi.chmod(0o755)
    witness = tmp_path / 'calls'
    result = subprocess.run(
        [
            environment_bash(),
            '-e',
            '-c',
            build['run'].replace('${{ matrix.platform }}', 'linux-64'),
        ],
        cwd=tmp_path,
        env={
            **os.environ,
            'PATH': str(tools) + os.pathsep + os.environ['PATH'],
            'RUNNER_TEMP': str(tmp_path),
            'GITHUB_WORKSPACE': str(tmp_path),
            'SHA': 'a7' * 20,
            'CACHE_WITNESS': str(witness),
        },
        capture_output=True,
        text=True,
        encoding='utf-8',
        timeout=5,
        check=False,
    )
    assert result.returncode == 23, 'Cache reporting must preserve the failed qualification status'
    calls = witness.read_text(encoding='utf-8').splitlines()
    assert len(calls) == 3 and '--zero-stats' in calls[0] and 'sdk-pack' in calls[1], (
        'Failed sdk pack reports cache stats then keeps its failure.'
    )
    assert '--show-stats' in calls[2], 'The failed real pack step must report its cache statistics'
    assert not list(tmp_path.glob('*.tar*')), 'A failed pack must stop before source archiving'
