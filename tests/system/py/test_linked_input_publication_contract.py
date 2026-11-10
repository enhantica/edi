"""Included scan bytes are sealed before folder, archive or browser publication."""

import pytest

from tests.system.py import test_save_policy_continuations as policy
from tests.system.py.test_request_owner_boundaries import ROUTES

tutorial_observer = policy.tutorial_observer
MUTATIONS = ('unchanged', 'same-size', 'remove', 'symlink', 'directory', 'rename', 'unreadable')
CASES = [
    (route, phase, mutation, 'plain')
    for route in ROUTES
    for phase in ('pre-core', 'copy')
    for mutation in MUTATIONS
]
CASES += [
    (route, phase, mutation, spelling)
    for route in (
        'save',
        'save-as',
        'existing-copy-folder',
        'fresh-zip',
        'web-folder',
        'web-save',
        'web-zip',
        'web-browser',
        'web-download',
    )
    for phase in ('pre-core', 'copy')
    for mutation in ('unchanged', 'same-size')
    for spelling in ('pipe', 'newline', 'unicode')
]


@pytest.mark.parametrize(('route', 'phase', 'mutation', 'spelling'), CASES)
def test_every_save_validates_linked_raw_bytes_before_any_user_publication(
    tutorial_observer, tmp_path, route, phase, mutation, spelling
):
    row = policy.observe(
        tutorial_observer, tmp_path, f'sealed-linked/{route}/{phase}/{mutation}/{spelling}'
    )
    assert row['injected'], (
        'The linked-input accident reaches a real late copy or publication frontier'
    )
    assert row['sourceConserved'], (
        'The save never changes the linked input beyond the independent external accident'
    )
    assert not row['wrongPublications'], (
        'No destination observes unplanned raw bytes, omitted frames or changed file types'
    )
    if (row['refused'] or row['replanned']) and not row['committed']:
        assert row['destinationUnchanged'], (
            'A linked-input refusal preserves every original destination byte and entry'
        )
    else:
        assert row['committed'] and row['observedPublications'] > 0, (
            'An accepted snapshot reaches its actual native, archive or browser publication'
        )
    if mutation == 'unchanged':
        assert not row['refused'] and not row['replanned'], (
            'An unchanged legal linked folder remains savable, including separator spellings'
        )
