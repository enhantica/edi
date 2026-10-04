"""Review-14 F08: a failed publication leaves a local-only proposal for retry."""

import subprocess

from tests.system.py.test_e09_t75_sdk_update import update


def test_failed_push_retry_publishes_local_proposal_without_deleting_local_work(tmp_path):
    good = tmp_path / 'control'
    good.mkdir()
    runs, state, *_ = update(good)
    assert runs[-1].returncode == 0 and state['pushed'] and state['dispatched'], (
        ' I26 complete updater control must publish before dispatch'
    )
    subject = tmp_path / 'subject'
    subject.mkdir()
    runs, state, *_ = update(subject, 'lost-push')
    assert runs[-1].returncode == 0, (
        f' I26 failed push must be retryable from its local commit: {runs[-1].stderr}'
    )
    assert len(state['pushed']) == 1 and state['dispatched'], (
        ' I26 retry must publish once and dispatch its same committed pin'
    )
    assert state['pushed'][0]['sha'] == state['local_proposal'], (
        ' I26 retry must reconcile the validated retained commit'
    )
    result = subprocess.run(
        [
            'git',
            '-C',
            str(subject / 'edi'),
            'rev-parse',
            '--verify',
            'refs/heads/crysta-sdk/local-unrelated',
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=2,
    )
    assert result.returncode == 0, ' I26 remote cleanup cannot delete a local-only branch'
    assert not (subject / 'unsupported-commands.jsonl').exists(), (
        ' I26 successful retry cannot swallow an unsupported remote deletion'
    )
