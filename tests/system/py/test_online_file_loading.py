"""Compare the production online and ordinary file loaders with offline data."""

import pytest

from tests.integration.app.online_load_host import run_online_host


@pytest.fixture(scope='module')
def online_host(tmp_path_factory):
    with run_online_host(tmp_path_factory.mktemp('online-host'), load_groups_only=True) as host:
        yield host


@pytest.mark.parametrize('tag', ['experiment', 'measured'])
def test_online_fixture_loading(online_host, tag):
    online_host.check('disk_parity', tag)
