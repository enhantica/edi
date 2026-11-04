"""Written tutorials take their inputs from the injected collection."""

import pytest

from tests.fixtures.online_sources.build_boundary_collection import build
from tests.integration.app.online_load_host import run_online_host


@pytest.fixture(scope='module')
def collection(tmp_path_factory):
    return build(tmp_path_factory.mktemp('collection-inputs') / 'source')


@pytest.fixture(scope='module')
def tutorial_host(tmp_path_factory, collection):
    with run_online_host(
        tmp_path_factory.mktemp('tutorial-collection-host'),
        failure_entries=False,
        offline_http=True,
        collection_root=collection,
        session_type='CollectionBoundarySession',
    ) as host:
        yield host


def test_interface_tour_waits_for_download_and_restores_edits(tutorial_host):
    tutorial_host.check('tour_download_preserves_owner')


@pytest.mark.parametrize('action', ['next', 'save'])
def test_tutorial_uses_injected_collection_files(tutorial_host, action):
    tutorial_host.check('tutorial_files', action)
