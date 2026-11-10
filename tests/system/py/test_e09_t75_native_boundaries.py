"""I6/F15: public job dependency observations and archive link destinations."""

from __future__ import annotations

import pytest

from tests.system.py.test_e09_t75_native_execution import assert_restored, restore


@pytest.mark.parametrize('platform', ['linux-64', 'osx-arm64'])
@pytest.mark.usefixtures('private_native_workflow')
def test_job_dependency_rechecks_emit_exactly_one_sdk_line(platform, tmp_path):
    result = restore(tmp_path, 'core', platform, repeat_dependency=True)
    assert_restored(result)
    runs = result[0]
    first = [line for line in runs[0].stdout.splitlines() if line.startswith('crysta: using SDK ')]
    assert len(first) == 1, ' I6 the first real core-build invocation must expose its SDK identity'
    lines = [
        line
        for run in runs
        for line in run.stdout.splitlines()
        if line.startswith('crysta: using SDK ')
    ]
    assert len(lines) == 1, (
        ' I6 separate required job invocations must check their dependency '
        'while emitting exactly one SDK line'
    )


@pytest.mark.parametrize('kind', ['symlink-destination', 'hardlink-destination'])
@pytest.mark.usefixtures('private_native_workflow')
def test_native_restore_refuses_links_escaping_the_native_tree(tmp_path, kind):
    control = tmp_path / 'control'
    control.mkdir()
    assert_restored(restore(control, 'audit', 'linux-64'))
    subject = tmp_path / 'subject'
    subject.mkdir()
    result = restore(subject, 'audit', 'linux-64', defect=kind)
    assert result[0][0].returncode != 0, (
        ' F15 archive links outside build/ci must refuse at the actual restore boundary'
    )
    link = subject / 'edi/build/ci/escape'
    assert not link.exists(), (
        ' F15 rejected archive must not install a link to repository files outside build/ci'
    )
    assert not link.is_symlink(), ' F15 rejected archive must leave no dangling escaping link'
