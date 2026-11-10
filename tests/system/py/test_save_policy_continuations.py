"""Every project save route keeps its policy decision and its original request owner."""

import json
import os
import subprocess
from pathlib import Path

import pytest

from tests.system.py import test_tutorial_project_ownership as ownership

tutorial_observer = ownership.tutorial_observer

ROOT = Path(__file__).resolve().parents[3]
ROUTES = (
    'save',
    'save-as',
    'unsaved-folder',
    'fresh-folder',
    'existing-folder',
    'fresh-zip',
    'existing-zip',
    'fresh-copy-folder',
    'existing-copy-folder',
    'fresh-copy-zip',
    'existing-copy-zip',
    'web-save',
    'web-folder',
    'web-zip',
    'web-copy',
    'web-download',
)


def observe(binary, tmp_path, group):
    corpus = Path(
        os.environ.get('EDI_CRYSTA_CORPUS_ROOT', ROOT / 'build/crysta-src/tests/fitting')
    )
    source = corpus / 'cosio-d20-scan-3f/project'
    assert source.is_dir(), (
        'The save observer uses the independently retained three-frame scan input'
    )
    result = subprocess.run(
        [binary, str(source), group],
        text=True,
        capture_output=True,
        check=False,
        timeout=25,
        env={
            **os.environ,
            'QT_QPA_PLATFORM': 'offscreen',
            'QT_QUICK_BACKEND': 'software',
            'EDI_ONLINE_SOURCES': f'cod={tmp_path.as_uri()};easydiffraction={tmp_path.as_uri()}',
        },
    )
    (tmp_path / 'observation.log').write_text(result.stdout + result.stderr)
    assert result.returncode == 0, (
        'The actual Session must reach the requested save-policy or continuation boundary: '
        + result.stderr
    )
    rows = json.loads(result.stdout.splitlines()[-1])
    assert len(rows) == 1, 'Each scoped case observes exactly its own save request'
    return rows[0]


@pytest.mark.parametrize('route', ROUTES)
def test_every_project_save_route_asks_before_writing_and_honours_cancel(
    tutorial_observer, tmp_path, route
):
    row = observe(tutorial_observer, tmp_path, f'save-policy/{route}/linked/ask/cancel')
    assert row['questions'] == 1, (
        'Ask reaches the same decision boundary on every original save route'
    )
    assert not row['wroteBeforeAnswer'], (
        'No user destination is published before the owner save decision'
    )
    assert row['after'] == row['before'], (
        'Cancel preserves the original project, location and scientific state'
    )
    assert row['inputUnchanged'], 'Cancel preserves every original input byte'
    assert row['sourceBytesUnchanged'], 'Cancel preserves the independent external measured inputs'
    assert row['destinationUnchanged'], (
        'Cancel leaves the requested destination unchanged while owned private caches are allowed'
    )


@pytest.mark.parametrize('route', ROUTES)
@pytest.mark.parametrize('mode', ['all', 'linked'])
def test_each_save_route_applies_the_chosen_include_or_link_policy(
    tutorial_observer, tmp_path, route, mode
):
    row = observe(tutorial_observer, tmp_path, f'save-policy/{route}/linked/{mode}/copy')
    assert row['questions'] == 0, (
        'An explicit small-data include/link choice needs no extra question'
    )
    assert row['snapshots'], 'Every accepted save route reaches its real core writer'
    snapshot = row['snapshots'][-1]
    assert row['sourceBytesUnchanged'], 'A save never rewrites the original measured source files'
    if mode == 'linked':
        assert snapshot['source'] == row['expectedSource'], (
            'Keep linked retains the original physical source location'
        )
    assert snapshot['external'] is (mode == 'linked'), (
        'The actual written snapshot includes or links data according to the explicit owner choice'
    )
    assert snapshot['hashes'] == row['expectedHashes'], (
        'Every saved route retains exactly the independent input files and their measured bytes'
    )


@pytest.mark.parametrize('route', ROUTES)
@pytest.mark.parametrize('storage', ['linked-large', 'copied-large'])
def test_large_saved_payload_warns_for_copied_and_linked_data(
    tutorial_observer, tmp_path, route, storage
):
    row = observe(tutorial_observer, tmp_path, f'save-policy/{route}/{storage}/all/cancel')
    assert row['planBytes'] >= row['inputBytes'], (
        'The save estimate counts at least all measured input bytes the writer must carry'
    )
    assert row['questions'] == 1, (
        'A save over the threshold asks even when its data are already copied'
    )
    assert row['large'], 'The real warning identifies a payload over the owner size boundary'
    assert not row['wroteBeforeAnswer'], 'Large data never start writing before the warning answer'
    assert row['after'] == row['before'], (
        'Cancelling a large save leaves its original project unchanged'
    )
    assert row['inputUnchanged'], 'Cancelling a large save preserves every original measured byte'


@pytest.mark.parametrize(
    'route', ['fresh-folder', 'existing-folder', 'fresh-zip', 'web-save', 'web-download']
)
@pytest.mark.parametrize(
    ('storage', 'answer'),
    [('linked-large', 'copy'), ('linked-large', 'linked'), ('copied-large', 'copy')],
)
def test_each_large_save_answer_controls_the_written_payload(
    tutorial_observer, tmp_path, route, answer, storage
):
    row = observe(tutorial_observer, tmp_path, f'save-policy/{route}/{storage}/all/{answer}')
    assert row['questions'] == 1, 'Each large-save answer belongs to one actual policy question'
    assert row['snapshots'], 'Accepting a large-save choice reaches the actual output writer'
    snapshot = row['snapshots'][-1]
    if answer == 'copy' or storage.startswith('linked'):
        assert snapshot['external'] is (answer == 'linked'), (
            'Copy anyway includes the data; Keep linked retains an existing external source'
        )
    assert snapshot['hashes'] == row['expectedHashes'], (
        'Each warning answer retains every independent measured byte'
    )


@pytest.mark.parametrize('accident', ['close', 'create', 'open', 'source'])
def test_late_save_answer_cannot_act_on_a_successor_owner(tutorial_observer, tmp_path, accident):
    row = observe(tutorial_observer, tmp_path, f'save-continuation/{accident}')
    if row.get('closedByRefusal'):
        assert row['preserved'], (
            'A refused owner replacement preserves the still-current request owner'
        )
        return
    assert row['preserved'], (
        'An old save reply cannot write or adopt the successor project or input generation'
    )
    assert row['questions'] == 2, (
        'A stale answer never primes a later save or consumes the successor owner decision'
    )


def test_save_answer_without_a_pending_request_does_not_prime_the_next_save(
    tutorial_observer, tmp_path
):
    row = observe(tutorial_observer, tmp_path, 'save-continuation/stray')
    assert row['questions'] == 1, (
        'A stray accepted answer leaves the next genuine save decision unarmed'
    )


def test_current_save_reply_completes_its_own_requested_destination(tutorial_observer, tmp_path):
    row = observe(tutorial_observer, tmp_path, 'save-continuation/valid')
    assert row['questions'] == 1, 'The matching save response belongs to its one original question'
    assert row['published'], (
        'The matching current response still publishes the requested real destination'
    )


@pytest.mark.parametrize('order', ['old-first', 'new-first'])
def test_reordered_save_answers_complete_only_their_own_request(
    tutorial_observer, tmp_path, order
):
    row = observe(tutorial_observer, tmp_path, 'save-continuation/' + order)
    if row['serialized']:
        assert row['refusedNew'], (
            'A serialized decision refuses the newer request before any output'
        )
        assert row['oldPublished'], 'The still-current original request retains its matching reply'
        assert row['newUnchanged'], (
            'A refused newer request never publishes its proposed destination'
        )
        return
    assert row['preserved'], (
        'An old answer cannot consume a newer pending request or undo its completed save'
    )
    assert row['newPublished'], (
        'The matching newer answer still publishes its own requested destination'
    )
    assert row['oldUnchanged'], (
        'An obsolete request cannot write its earlier destination in either reply order'
    )


@pytest.mark.parametrize('route', ROUTES)
@pytest.mark.parametrize('answer', ['copy', 'linked'])
def test_each_ask_answer_controls_the_save_route_it_belongs_to(
    tutorial_observer, tmp_path, route, answer
):
    row = observe(tutorial_observer, tmp_path, f'save-policy/{route}/linked/ask/{answer}')
    assert row['questions'] == 1, (
        'A matching response belongs to the one actual question on its save route'
    )
    assert not row['wroteBeforeAnswer'], 'The chosen route waits for its own answer before writing'
    assert row['snapshots'], (
        'Each admitted Copy or Keep linked answer reaches the real requested writer'
    )
    snapshot = row['snapshots'][-1]
    assert snapshot['external'] is (answer == 'linked'), (
        'The matching answer controls actual inclusion on every route'
    )
    if answer == 'linked':
        assert snapshot['source'] == row['expectedSource'], (
            'Keep linked preserves the original physical source'
        )
    assert snapshot['hashes'] == row['expectedHashes'], (
        'Both matching answers retain all independent measured bytes'
    )
