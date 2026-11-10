"""Atomic displacement counts the same atom-site rows its table shows."""

import pytest

from tests.integration.app.online_load_host import run_online_host


@pytest.fixture(scope='module')
def atomic_host(tmp_path_factory):
    with run_online_host(
        tmp_path_factory.mktemp('displacement-count'),
        failure_entries=False,
        offline_http=True,
        session_type='PopupContractSession',
    ) as host:
        host.check('atomic_setup')
        yield host


@pytest.mark.parametrize('types', ['biso', 'mixed'])
def test_atomic_displacement_count_equals_visible_site_rows(atomic_host, types):
    atomic_host.check('atomic_count', types)
