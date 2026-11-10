# SPDX-License-Identifier: BSD-3-Clause
"""Recovering a retained preview run picks one complete attempt, not the run's last one."""

import importlib.util
import sys
from pathlib import Path
from unittest import mock

import pytest

ROOT = Path(__file__).resolve().parents[3]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'tools/release' / (name + '.py'))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


PLAN = module('plan')
with mock.patch.dict(sys.modules, {'plan': PLAN}):
    PROMOTE = module('promote')
    with mock.patch.dict(sys.modules, {'promote': PROMOTE}):
        RECOVERY = module('preview')

PLATFORMS = ['Linux', 'macOS', 'Windows']


def installer_jobs(*failed):
    return [
        {'name': f'installer · {p}', 'conclusion': 'failure' if p in failed else 'success'}
        for p in PLATFORMS
    ]


def artifacts(*attempts):
    return [
        {'name': f'{kind}-{platform}-{attempt}', 'expired': False}
        for attempt in attempts
        for platform in PLATFORMS
        for kind in ('installer', 'installer-components')
    ]


def select(jobs_by_attempt, retained):
    def api(_repo, path):
        attempt = int(path.split('/attempts/')[1].split('/')[0])
        return {'jobs': jobs_by_attempt.get(attempt, [])}

    with mock.patch.object(RECOVERY, 'api', side_effect=api):
        return RECOVERY.qualified_attempt('enhantica/edi', 7, max(jobs_by_attempt), retained)


def test_a_draft_only_retry_keeps_the_complete_earlier_attempt():
    draft_only = [{'name': 'Create or update the prerelease draft', 'conclusion': 'success'}]
    assert select({1: installer_jobs(), 2: draft_only}, artifacts(1)) == 1, (
        'A draft only retry keeps the complete earlier attempt.'
    )


def test_platforms_are_never_combined_across_attempts():
    partial = installer_jobs('Windows')
    assert select({1: installer_jobs(), 2: partial}, artifacts(1, 2)) == 1, (
        'Platforms are never combined across attempts.'
    )
    with pytest.raises(ValueError, match='built and kept every platform'):
        select({1: installer_jobs('Linux'), 2: installer_jobs('Windows')}, artifacts(1, 2))


def test_the_newest_complete_attempt_wins_and_expired_artifacts_do_not_count():
    assert select({1: installer_jobs(), 2: installer_jobs()}, artifacts(1, 2)) == 2, (
        'The newest complete attempt wins and expired artifacts do not count.'
    )
    expired = [{**item, 'expired': item['name'].endswith('-2')} for item in artifacts(1, 2)]
    assert select({1: installer_jobs(), 2: installer_jobs()}, expired) == 1, (
        'The newest complete attempt wins and expired artifacts do not count.'
    )


def test_a_run_without_calendar_identity_cannot_be_recovered(tmp_path):
    run = {
        'path': '.github/workflows/installers.yml',
        'status': 'completed',
        'head_branch': 'b',
        'head_repository': {'full_name': 'enhantica/edi'},
        'run_attempt': 1,
        'head_sha': 'a' * 40,
    }

    def api(_repo, path):
        if path.endswith('/artifacts?per_page=100'):
            return {'artifacts': artifacts(1)}
        if '/attempts/' in path:
            return {'jobs': installer_jobs()}
        return run

    def recover(_repo, _artifacts, name, scratch):
        folder = scratch / name
        folder.mkdir()
        return folder

    with (
        mock.patch.object(RECOVERY, 'api', side_effect=api),
        mock.patch.object(RECOVERY, 'recover_artifact', side_effect=recover),
        pytest.raises(ValueError, match='Only a calendar preview'),
    ):
        RECOVERY.stage('enhantica/edi', 'b', 7, tmp_path / 'out')


RUN = {
    'path': '.github/workflows/installers.yml',
    'status': 'completed',
    'head_branch': 'b',
    'head_repository': {'full_name': 'enhantica/edi'},
    'run_attempt': 2,
    'head_sha': 'a' * 40,
}


def recover_deliveries(tmp_path, run):
    def api(_repo, path):
        if path.endswith('/artifacts?per_page=100'):
            return {'artifacts': artifacts(1, 2)}
        if '/attempts/2/' in path:
            return {'jobs': [{'name': 'Create or update the prerelease draft'}]}
        if '/attempts/' in path:
            return {'jobs': installer_jobs()}
        return run

    def recover(_repo, _artifacts, name, scratch):
        folder = scratch / name
        folder.mkdir()
        (folder / 'installer.json').write_text(name)
        return folder

    with (
        mock.patch.object(RECOVERY, 'api', side_effect=api),
        mock.patch.object(RECOVERY, 'recover_artifact', side_effect=recover),
    ):
        RECOVERY.deliveries('enhantica/edi', 'b', 7, tmp_path / 'out')
    return tmp_path / 'out'


def test_a_failed_draft_step_reuses_the_qualified_installers_of_its_run(tmp_path):
    out = recover_deliveries(tmp_path, RUN)
    assert sorted(p.name for p in out.iterdir()) == [
        'commit',
        'installer-Linux-1',
        'installer-Windows-1',
        'installer-macOS-1',
    ], 'A failed draft step reuses the qualified installers of its run.'
    assert (out / 'installer-macOS-1/installer.json').read_text() == 'installer-macOS-1', (
        'A failed draft step reuses the qualified installers of its run.'
    )
    assert (out / 'commit').read_text() == 'a' * 40 + '\n', (
        'The draft is checked against the source the installers were built from.'
    )


def test_installers_of_another_branch_or_an_unfinished_run_are_not_reused(tmp_path):
    for changed in ({'head_branch': 'other'}, {'status': 'in_progress'}):
        with pytest.raises(ValueError, match='completed desktop installer run on this branch'):
            recover_deliveries(tmp_path / next(iter(changed)), {**RUN, **changed})


def test_the_draft_job_attaches_a_preview_run_without_rebuilding():
    yaml = pytest.importorskip('yaml')
    workflow = yaml.safe_load((ROOT / '.github/workflows/installers.yml').read_text())
    builds, draft = workflow['jobs']['installers'], workflow['jobs']['draft-preview-release']
    assert "inputs.preview_run == ''" in builds['if'], 'A preview run skips the installer builds.'
    condition = ' '.join(draft['if'].split())
    assert "inputs.preview_run != '' && needs.installers.result == 'skipped'" in condition, (
        'The draft job runs on the skipped builds of a preview run.'
    )
    assert "needs.installers.result == 'success'" in condition, (
        'Without a preview run the draft job still needs successful builds.'
    )
    steps = {step.get('name', ''): step for step in draft['steps']}
    recover = steps['Recover qualified installers from the preview run']
    assert recover['if'] == "inputs.preview_run != ''" and '--deliveries' in recover['run'], (
        'A preview run recovers only its qualified installer deliveries.'
    )
    attach = steps['Attach qualified online installers to the draft']['run']
    assert 'commit=$(cat preview-delivery/commit)' in attach and '--commit "$commit"' in attach, (
        'Reused installers are checked against their own source commit.'
    )
