"""Real Qt download ownership, tutorial sources, integrity and outage recovery."""

import json
import shutil

import pytest

from tests.fixtures.online_sources.build_boundary_collection import build
from tests.integration.app.online_load_host import run_online_host


@pytest.fixture(scope='module')
def collection(tmp_path_factory):
    return build(tmp_path_factory.mktemp('collection-inputs') / 'source')


@pytest.fixture(scope='module')
def boundaries(tmp_path_factory, collection):
    with run_online_host(
        tmp_path_factory.mktemp('boundary-host'),
        load_groups_only=True,
        failure_entries=False,
        offline_http=True,
        collection_root=collection,
        session_type='CollectionBoundarySession',
    ) as host:
        yield host


@pytest.mark.parametrize('case', ['close', 'create', 'ordinary-open', 'reverse', 'old-error'])
def test_example_completion_keeps_request_ownership(boundaries, case):
    boundaries.check('example_ownership', case)


@pytest.mark.parametrize('route', ['structure', 'experiment', 'data', 'project'])
@pytest.mark.parametrize('claim', ['digest', 'size', 'absent'])
def test_app_download_content_claims(boundaries, route, claim):
    boundaries.check('integrity', route + '-' + claim)


@pytest.mark.parametrize('source', ['cod', 'collection'])
def test_popup_rejects_partially_consumed_formula(boundaries, source):
    boundaries.check('formula_seam', source)


def test_examples_retry_after_startup_outage(tmp_path):
    source = tmp_path / 'outage'
    source.mkdir()
    mailbox = tmp_path / 'mailbox'
    mailbox.mkdir()
    with run_online_host(
        mailbox,
        load_groups_only=True,
        failure_entries=False,
        offline_http=True,
        collection_root=source,
        session_type='CollectionBoundarySession',
    ) as host:
        host.check('initial_outage')
        recovered = build(tmp_path / 'recovered', include_catalogue=True)
        shutil.copytree(recovered, source, dirs_exist_ok=True)
        host.check('recovery_open')


def test_no_project_entries_explains_unavailability(tmp_path, collection):
    source = tmp_path / 'no-projects'
    shutil.copytree(collection, source)
    index = source / 'index.json'
    value = json.loads(index.read_text())
    value['entries'] = [e for e in value['entries'] if e['kind'] != 'project']
    index.write_text(json.dumps(value))
    mailbox = tmp_path / 'mailbox'
    mailbox.mkdir()
    with run_online_host(
        mailbox,
        load_groups_only=True,
        failure_entries=False,
        offline_http=True,
        collection_root=source,
        session_type='CollectionBoundarySession',
    ) as host:
        host.check('empty_projects_notice')


def test_downloaded_example_has_writable_copy_and_save_as(boundaries):
    boundaries.check('downloaded_working_copy')


@pytest.mark.parametrize('stage', ['index', 'file', 'examples-index', 'examples-file'])
@pytest.mark.parametrize('outcome', ['primary', 'fallback', 'both-fail', 'missing'])
def test_one_logical_collection_uses_ordered_locations(tmp_path, stage, outcome):
    with run_online_host(
        tmp_path,
        load_groups_only=True,
        failure_entries=False,
        offline_http=True,
        session_type='CollectionBoundarySession',
    ) as host:
        host.check('logical_source', stage + '-' + outcome)


def test_source_selector_has_no_separate_mirror(boundaries):
    boundaries.check('logical_source', 'selector')
