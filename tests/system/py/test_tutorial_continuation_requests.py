"""Tutorial replies keep their originating request across owner and source changes."""

import copy
import json
import os
import shutil
from pathlib import Path

import pytest

from tests.integration.app.online_load_host import run_online_host

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope='module')
def continuation_host(tmp_path_factory):
    base = tmp_path_factory.mktemp('request-continuations')
    collection = base / 'collection'
    shutil.copytree(ROOT / 'tests/fixtures/online_sources/easydiffraction', collection)
    index = collection / 'index.json'
    document = json.loads(index.read_text())
    for kind, entry_id in [('structure', 'tutorial-lbco'), ('data', 'tutorial-hrpt')]:
        entry = copy.deepcopy(next(row for row in document['entries'] if row['kind'] == kind))
        entry['id'] = entry_id
        document['entries'].append(entry)
    index.write_text(json.dumps(document))
    with run_online_host(
        base / 'mailbox',
        load_groups_only=False,
        failure_entries=False,
        offline_http=False,
        collection_root=collection,
        session_type='RequestContinuationSession',
        output_log=os.environ.get('EDI_CONTINUATION_HOST_LOG', str(base / 'host.log')),
    ) as host:
        yield host


@pytest.mark.parametrize(
    'accident',
    [
        'repeat',
        'back',
        'stop-new',
        'new-tutorial',
        'project-replace',
        'source-change',
        'save-files',
    ],
)
@pytest.mark.parametrize(
    'order', ['old-success', 'old-failure', 'new-before-old-success', 'new-before-old-failure']
)
def test_tutorial_reply_completes_only_its_originating_request(continuation_host, accident, order):
    continuation_host.check('tutorial_request_ownership', accident + '-' + order)


def test_staging_and_save_files_terminal_replies_keep_their_actual_request_ids(continuation_host):
    continuation_host.check('tutorial_producer_tags_each_terminal_reply')
