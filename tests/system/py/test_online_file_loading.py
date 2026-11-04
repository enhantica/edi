"""Compare the production online and ordinary file loaders with offline data."""

import pytest

from tests.integration.app.online_load_host import run_online_host


@pytest.fixture(scope='module')
def online_host(tmp_path_factory):
    with run_online_host(
        tmp_path_factory.mktemp('online-host'), load_groups_only=True, offline_http=True
    ) as host:
        yield host


@pytest.mark.parametrize('tag', ['experiment', 'measured'])
def test_online_fixture_loading(online_host, tag):
    online_host.check('disk_parity', tag)


@pytest.mark.parametrize(
    ('case', 'tag'),
    [
        ('new_target_import', 'local-cancel'),
        ('new_target_import', 'local-corrupt'),
        ('new_target_import', 'local-valid'),
        ('new_target_import', 'web-valid'),
        ('new_target_import', 'web-corrupt'),
        ('new_target_import', 'web-refused-probe'),
        ('late_delivery', 'structure'),
        ('late_delivery', 'experiment'),
        ('late_delivery', 'measured'),
        ('late_delivery', 'removed-target'),
        ('disabled_source', 'button'),
        ('disabled_source', 'stale-dispatch'),
    ],
)
def test_online_file_request_boundaries(online_host, case, tag):
    online_host.check(case, tag)


@pytest.mark.parametrize(
    ('case', 'tag'),
    [
        ('cod_http', 'spacegroup'),
        ('cod_http', 'extra-elements'),
        ('cod_http', 'comma'),
        ('cod_http', 'semicolon'),
        ('unavailable_http', 'service-503'),
        ('unavailable_http', 'download-503'),
        ('unavailable_http', 'absent-file'),
        ('unavailable_http', 'missing-entry'),
    ],
)
def test_online_http_request_and_reply(online_host, case, tag):
    online_host.check(case, tag)


@pytest.mark.parametrize('tag', ['structure', 'experiment'])
def test_online_load_actions(online_host, tag):
    online_host.check('actions_and_formats', tag)
