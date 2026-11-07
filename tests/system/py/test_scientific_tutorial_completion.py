"""Both scientific lessons reach the end using their actual Next actions."""

import copy
import json
import os
import shutil
from pathlib import Path

import pytest

from tests.integration.app.online_load_host import run_online_host

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope='module')
def lesson_host(tmp_path_factory):
    base = tmp_path_factory.mktemp('scientific-lessons')
    collection = base / 'collection'
    shutil.copytree(ROOT / 'tests/fixtures/online_sources/easydiffraction', collection)
    index = collection / 'index.json'
    value = json.loads(index.read_text())
    for kind, entry_id in [('structure', 'tutorial-lbco'), ('data', 'tutorial-hrpt')]:
        entry = copy.deepcopy(next(row for row in value['entries'] if row['kind'] == kind))
        entry['id'] = entry_id
        value['entries'].append(entry)
    index.write_text(json.dumps(value))
    with run_online_host(
        base / 'mailbox',
        failure_entries=False,
        offline_http=True,
        collection_root=collection,
        session_type='ExperimentWorkflowSession',
        request_timeout=180,
        output_log=os.environ.get('EDI_LESSON_HOST_LOG', str(base / 'lesson-host.log')),
    ) as host:
        host.lesson_failures = {}
        for lesson in ('simulation', 'fitting'):
            try:
                host.check('prepare_lesson', lesson)
            except AssertionError as error:
                if host.communication_failed:
                    raise
                host.lesson_failures[lesson] = str(error)
        yield host


@pytest.mark.parametrize('lesson', ['simulation', 'fitting'])
def test_actual_scientific_tutorial_reaches_its_end(lesson_host, lesson):
    assert lesson not in lesson_host.lesson_failures, (
        'The actual lesson walk must complete: ' + lesson_host.lesson_failures.get(lesson, '')
    )
    lesson_host.check('lesson_completed', lesson)


@pytest.mark.parametrize('lesson', ['simulation', 'fitting'])
def test_completed_lesson_has_the_independent_scientific_state(lesson_host, lesson):
    assert lesson not in lesson_host.lesson_failures, (
        'The scientific-state witness requires a completed lesson: '
        + lesson_host.lesson_failures.get(lesson, '')
    )
    lesson_host.check('lesson_science', lesson)


@pytest.mark.parametrize('lesson', ['simulation', 'fitting'])
def test_completed_lesson_returns_to_the_original_user_project(lesson_host, lesson):
    assert lesson not in lesson_host.lesson_failures, (
        'Owner restoration must follow the actual completed lesson: '
        + lesson_host.lesson_failures.get(lesson, '')
    )
    lesson_host.check('lesson_owner', lesson)
