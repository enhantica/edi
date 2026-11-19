"""First-open downloads and offline feedback use the ordinary desktop session."""

import pytest

from tests.fixtures.large_collection.inputs import generate
from tests.integration.app.online_load_host import run_online_host


@pytest.fixture(scope='module')
def collection_host(tmp_path_factory):
    mailbox = tmp_path_factory.mktemp('large-collection')
    online, _bundle = generate(mailbox / 'inputs')
    with run_online_host(
        mailbox,
        collection_root=online,
        session_type='BundleDownloadSession',
        failure_entries=False,
    ) as host:
        yield host


@pytest.mark.parametrize('case', ['small_offline', 'large_online', 'large_offline'])
def test_collection_first_open(collection_host, case):
    collection_host.check(case)
