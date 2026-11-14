"""Failed qualification preserves compiled objects without promoting an unqualified SDK."""

import copy
import os
import subprocess
from pathlib import Path

import pytest
import yaml

from tests.fixtures.e09_t75_workflow import active

ROOT = Path(__file__).resolve().parents[3]


def producer():
    return yaml.safe_load((ROOT / '.github/workflows/crysta-sdk.yml').read_text())['jobs']['build']


def object_cache_boundary(job):
    steps = job['steps']
    restores = [step for step in steps if step.get('id') == 'compiler-cache']
    saves = [
        step
        for step in steps
        if step.get('uses') == 'actions/cache/save@v4'
        and step.get('with', {}).get('path') == '${{ runner.temp }}/crysta-ccache'
    ]
    assert len(restores) == len(saves) == 1, (
        'One explicit restore/save pair owns SDK compiler objects'
    )
    restore, save = restores[0], saves[0]
    assert restore['uses'] == 'actions/cache/restore@v4', (
        'Compiler restore cannot depend on a successful-job post-save'
    )
    assert save['with']['key'] == restore['with']['key'], (
        'Saved compiler objects keep their exact restored identity'
    )
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
    assert (
        archive['uses'] == 'actions/cache@v4' and archive['with']['path'] == 'crysta-sdk-archives'
    ), 'Qualified SDK archive caching retains its separate successful-job policy'
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
    ]:
        changed = copy.deepcopy(job)
        save = next(
            step for step in changed['steps'] if step.get('uses') == 'actions/cache/save@v4'
        )
        if damage == 'missing-save':
            changed['steps'].remove(save)
        elif damage == 'wrong-key':
            save['with']['key'] = 'foreign-objects'
        elif damage == 'success-only':
            save['if'] = 'success()'
        elif damage == 'unconditional':
            save['if'] = '!cancelled()'
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
    steps = producer()['steps']
    inputs = next(step for step in steps if step.get('id') == 'compiler-inputs')
    (tmp_path / 'crysta').mkdir()
    (tmp_path / 'crysta/pixi.lock').write_bytes(b'independent real lock bytes')
    jobs = tmp_path / 'crysta' / 'tools' / 'ci' / 'build-jobs.sh'
    jobs.parent.mkdir(parents=True)
    jobs.write_text("printf '%s\\n' 6\n", encoding='utf-8')
    for platform in ['Windows', 'Linux', 'macOS']:
        output, environment = tmp_path / 'output', tmp_path / 'environment'
        output.write_text('', encoding='utf-8')
        environment.write_text('', encoding='utf-8')
        result = subprocess.run(
            ['bash', '-e', '-c', inputs['run']],
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
        ['bash', '-e', '-c', inputs['run']],
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
    wrapper = yaml.safe_load((ROOT / '.github/actions/setup-pixi/action.yml').read_text())
    assert wrapper['inputs']['environments']['default'] == 'default', (
        'Existing wrapper callers keep their original default environment'
    )
    upstream = wrapper['runs']['steps'][0]
    assert upstream['with']['environments'] == '${{ inputs.environments }}', (
        'The selected environment reaches the pinned upstream Pixi action'
    )
    assert upstream['with']['frozen'] is True, (
        'Choosing one environment never changes frozen lock admission'
    )


def test_failed_native_observations_are_retained_without_promoting_an_sdk():
    steps = producer()['steps']
    evidence = next(
        step
        for step in steps
        if step.get('with', {}).get('name')
        == 'crysta-sdk-red-${{ matrix.platform }}-${{ needs.resolve.outputs.sha }}'
    )
    artifact = next(
        step
        for step in steps
        if step.get('with', {}).get('name') == 'crysta-sdk-${{ matrix.platform }}'
    )
    assert evidence['uses'] == 'actions/upload-artifact@v4'
    assert evidence['with']['path'] == (
        '${{ runner.temp }}/crysta/build/sdk-pack-red/${{ needs.resolve.outputs.sha }}'
    ), 'The observer owns retained native logs after the packer removes its scratch checkout'
    for state, cancelled in [('success', False), ('failure', False), ('failure', True)]:
        context = {'states': {'qualification': state}, 'cancelled': cancelled}
        assert active(evidence, 'workflow_dispatch', **context) == (
            state == 'failure' and not cancelled
        )
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
    assert restore['uses'] == 'actions/cache/restore@v4'
    assert save['uses'] == 'actions/cache/save@v4'
    assert save['with'] == {key: restore['with'][key] for key in ('path', 'key')}
    assert steps.index(restore) < steps.index(build) < steps.index(save)
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
        ) == (outcome == 'success' and not cancelled)


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
