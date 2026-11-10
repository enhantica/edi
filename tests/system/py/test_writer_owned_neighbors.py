"""Only writer-owned direct entity documents are exempt from exact save receipts."""

import pytest

from tests.system.py import test_save_policy_continuations as policy
from tests.system.py import test_sealed_publication_contract as sealed

tutorial_observer = policy.tutorial_observer


@pytest.mark.parametrize('route', sealed.ROUTES)
@pytest.mark.parametrize('folder', ['structures', 'experiments'])
@pytest.mark.parametrize('phase', ['pre-core', 'copy'])
@pytest.mark.parametrize('mutation', ['unchanged', 'same-size'])
def test_every_save_retains_exact_neighbors_of_its_generated_entity_documents(
    tutorial_observer, tmp_path, route, folder, phase, mutation
):
    row = policy.observe(
        tutorial_observer,
        tmp_path,
        f'sealed-publication/{route}/{phase}/{mutation}/plain/neighbors-{folder}',
    )
    assert row['role'] == f'neighbors-{folder}' and row['injected'], (
        'The witness reaches the actual retained entity-folder neighbors after planning'
    )
    assert not row['wrongPublications'], (
        'No save delegate publishes changed notes or nested entity documents '
        'under the direct generated-document exemption'
    )
    assert row['sourceConserved'], (
        'The save preserves every retained source byte beyond the injected external accident'
    )
    if (row['refused'] or row['replanned']) and not row['committed']:
        assert row['destinationUnchanged'], (
            'A refusal before publication leaves every previous user destination byte intact'
        )
    else:
        assert row['committed'] and row['observedPublications'] > 0, (
            'An accepted neighbor receipt reaches an actual observable user publication'
        )
    if mutation == 'unchanged':
        assert row['committed'] and not row['refused'] and not row['replanned'], (
            'Generated-document exemptions permit the ordinary successful unchanged save'
        )
