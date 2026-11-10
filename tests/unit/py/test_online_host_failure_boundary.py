"""A lost Qt transport never dispatches again or waits for another answer."""

import json
from queue import Empty
from types import SimpleNamespace

import pytest

from tests.integration.app.online_load_host import OnlineHost


class Host(OnlineHost):
    def __init__(self, *, failed=False, exit_code=None):
        self.communication_failed = failed
        self.process = SimpleNamespace(poll=lambda: exit_code)
        self.sequence = 17
        self.failed = False
        self.request_timeout = 0.25
        self.calls = []
        self.mailbox = self

    def __truediv__(self, name):
        return SimpleNamespace(
            name=name,
            write_text=lambda text: self.calls.append(('write', json.loads(text))),
            replace=lambda target: self.calls.append(('rename', target.name)),
        )

    def receive(self, marker, timeout):
        self.calls.append(('receive', marker, timeout))
        return '{"id": 18, "passed": true}', ''


@pytest.mark.parametrize(('failed', 'exit_code'), [(True, None), (False, 0), (False, 7)])
@pytest.mark.parametrize('entry', ['check', 'send'])
def test_unavailable_host_refuses_before_a_new_request_or_wait(failed, exit_code, entry):
    host = Host(failed=failed, exit_code=exit_code)
    with pytest.raises(pytest.fail.Exception, match='unavailable'):
        getattr(host, entry)('next', 'fixture')
    assert host.calls == [], 'A failed or exited host sends no request and consumes no wait budget'


def test_live_host_keeps_its_normal_correlated_dispatch_and_receipt():
    host = Host()
    host.check('next', 'fixture')
    assert host.calls == [
        ('write', {'id': 18, 'case': 'next', 'tag': 'fixture'}),
        ('rename', 'request'),
        ('receive', 'ONLINE_RESULT ', 0.25),
    ], 'A live host retains the ordinary correlated request and receipt protocol'
    assert host.sequence == 18, 'The live control keeps a nontrivial increasing request identity'


@pytest.mark.parametrize('ending', ['exit', 'empty', 'deadline'])
def test_consumed_exit_marker_never_becomes_another_empty_queue_wait(ending):
    host = Host()
    reads = []

    def ended(*, timeout):
        reads.append(timeout)
        if len(reads) > 1 or ending == 'deadline':
            raise AssertionError('An unavailable host must never enter another queue wait')
        if ending == 'empty':
            raise Empty

    host.lines = SimpleNamespace(get=ended)
    with pytest.raises(pytest.fail.Exception, match='exited' if ending == 'exit' else 'timed out'):
        OnlineHost.receive(host, 'ONLINE_RESULT ', 0 if ending == 'deadline' else 0.25)
    with pytest.raises(pytest.fail.Exception, match='unavailable'):
        OnlineHost.receive(host, 'ONLINE_RESULT ', 0.25)
    assert len(reads) == (0 if ending == 'deadline' else 1), (
        'Every terminal transport condition is latched before a later receive can wait again'
    )
