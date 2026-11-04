"""Exercise structure loading and source fallback through the production Load group."""

import pytest

from tests.integration.app.online_load_host import run_online_host


@pytest.fixture(scope='module')
def online_host(tmp_path_factory):
    with run_online_host(tmp_path_factory.mktemp('online-host'), load_groups_only=True) as host:
        yield host


def test_structure_matches_disk(online_host):
    online_host.check('disk_parity', 'structure')


def test_cod_falls_back_to_easydiffraction(online_host):
    online_host.check('cod_fallback')
