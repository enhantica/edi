"""Unavailable collection inputs never fall back to bundled tutorial files."""

import pytest

from tests.integration.app.online_load_host import run_online_host


@pytest.fixture(scope='module')
def unavailable_tutorial_host(tmp_path_factory):
    root = tmp_path_factory.mktemp('unavailable-tutorial')
    with run_online_host(
        root / 'mailbox',
        failure_entries=False,
        offline_http=True,
        collection_root=root / 'unavailable',
        session_type='CollectionBoundarySession',
    ) as host:
        yield host


@pytest.mark.parametrize('action', ['next', 'save'])
def test_tutorial_failure_never_substitutes_bundled_files(unavailable_tutorial_host, action):
    unavailable_tutorial_host.check('unavailable_tutorial', action)
