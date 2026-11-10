"""Every copied-tree save validates exact content before its user publication."""

import pytest

from tests.system.py import test_save_policy_continuations as policy

tutorial_observer = policy.tutorial_observer

# Derived from the public Session entry points and their physical branches:
# save (opened archive and all browser places), saveAs, saveProjectAs,
# saveWebProjectAs, downloadWebProject, completeAssistantSaveAs. A
# new unsaved model has no prior opaque tree. Ordinary Save retains opaque
# user files through its native writer and belongs to the same sealed boundary.
ROUTES = tuple(route for route in policy.ROUTES if route != 'unsaved-folder') + (
    'save-archive',
    'web-save-zip',
    'web-save-browser',
    'web-browser',
    'web-copy-browser',
    'assistant-folder',
    'assistant-zip',
    'assistant-copy-folder',
    'assistant-copy-zip',
)
MUTATIONS = (
    'unchanged',
    'same-size',
    'remove',
    'add',
    'hidden',
    'symlink',
    'directory',
    'rename',
    'unreadable',
)
CASES = [
    (route, phase, mutation, 'plain')
    for route in ROUTES
    for phase in ('pre-core', 'copy')
    for mutation in MUTATIONS
] + [
    (route, phase, 'same-size', spelling)
    for route in ROUTES
    for phase in ('pre-core', 'copy')
    for spelling in ('pipe', 'newline', 'unicode')
]


@pytest.mark.parametrize(('route', 'phase', 'mutation', 'spelling'), CASES)
def test_user_publication_contains_only_the_complete_planned_payload(
    tutorial_observer, tmp_path, route, phase, mutation, spelling
):
    row = policy.observe(
        tutorial_observer, tmp_path, f'sealed-publication/{route}/{phase}/{mutation}/{spelling}'
    )
    assert row['injected'], (
        'The late accident must reach a real copy, core-write or user publication boundary'
    )
    assert not row['wrongPublications'], (
        'No unplanned content, missing entry or changed entry type becomes user-visible, '
        'even when a later content check refuses or rolls back'
    )
    assert row['sourceConserved'], (
        'Saving never changes the authored source beyond the injected external accident'
    )
    if (row['refused'] or row['replanned']) and not row['committed']:
        assert row['destinationUnchanged'], (
            'A refused or replanned save leaves every prior destination byte and entry unchanged'
        )
    else:
        assert row['committed'] and row['observedPublications'] > 0, (
            'An accepted save reaches an observed actual user publication boundary'
        )


@pytest.mark.parametrize('route', ROUTES)
def test_unchanged_input_still_reaches_its_real_publication(tutorial_observer, tmp_path, route):
    row = policy.observe(
        tutorial_observer, tmp_path, f'sealed-publication/{route}/pre-core/unchanged/plain'
    )
    assert not row['refused'] and not row['replanned'], (
        'Content validation must continue to admit an unchanged planned payload'
    )
    assert row['committed'] and row['observedPublications'] > 0 and not row['wrongPublications'], (
        'Each unchanged-input control actually publishes its complete authored payload'
    )
