"""Scoped leaf actors keep their subjects; aggregate checks retain the whole inventory."""

from types import SimpleNamespace as Record

import pytest

from tests.fixtures.e04_t1 import project_actor as actor

APP = 'test_every_example_opens_through_its_page_row:magnetic'
RETAINED = 'test_retained_fixture_directories_keep_their_independent_project_population:legacy'
VERIFICATION = (
    'test_verification_directories_keep_their_independent_project_population:verification'
)


@pytest.fixture
def inventory(monkeypatch):
    monkeypatch.setattr(actor, 'PROJECT_CASES', [APP, RETAINED, VERIFICATION, 'control'])
    monkeypatch.setattr(actor, 'ORACLE', {'app_ids': ['magnetic']})


def item(name, key=None, identity=None, *, uses=True):
    return Record(
        originalname=name,
        callspec=Record(params={key: identity}),
        fixturenames=['existing_projects_run'] if uses else [],
    )


@pytest.mark.usefixtures('inventory')
@pytest.mark.parametrize(
    ('name', 'key', 'identity', 'expected'),
    [
        (
            'test_each_registered_example_executes_in_the_production_host',
            'example_id',
            'magnetic',
            APP,
        ),
        (
            'test_verification_directory_executes_in_the_production_host',
            'example_id',
            'verification',
            VERIFICATION,
        ),
        (
            'test_retained_fixture_directory_executes_in_the_production_host',
            'example_id',
            'legacy',
            RETAINED,
        ),
        (
            'test_existing_project_receipts_cover_every_registered_example',
            'example',
            'magnetic',
            APP,
        ),
        (
            'test_existing_project_receipts_cover_every_registered_example',
            'example',
            'legacy',
            RETAINED,
        ),
        (
            'test_verification_directory_receipt_retains_every_original_project',
            'example',
            'verification',
            VERIFICATION,
        ),
    ],
)
def test_each_leaf_keeps_exactly_its_requested_native_case(name, key, identity, expected):
    actual = actor.project_cases_for_session(Record(items=[item(name, key, identity)]))
    assert actual == (expected,), 'Every leaf retains its exact native actor and project identity'


@pytest.mark.usefixtures('inventory')
@pytest.mark.parametrize(
    'name', ['test_existing_projects_open_and_populate_pages', 'new_consumer']
)
def test_aggregate_and_unknown_consumers_keep_every_native_case(name):
    assert actor.project_cases_for_session(Record(items=[item(name)])) == (
        APP,
        RETAINED,
        VERIFICATION,
        'control',
    ), 'An aggregate or unknown consumer must retain all actors and controls'


@pytest.mark.usefixtures('inventory')
def test_shared_requests_deduplicate_without_losing_cases_or_inventory_order():
    leaves = [
        item('test_existing_project_receipts_cover_every_registered_example', 'example', 'legacy'),
        item(
            'test_each_registered_example_executes_in_the_production_host',
            'example_id',
            'magnetic',
        ),
        item(
            'test_existing_project_receipts_cover_every_registered_example', 'example', 'magnetic'
        ),
        item('unrelated', uses=False),
    ]
    assert actor.project_cases_for_session(Record(items=leaves)) == (APP, RETAINED), (
        'Shared fixtures execute the union of requested actors once in declared inventory order'
    )


@pytest.mark.usefixtures('inventory')
def test_unknown_project_identity_refuses_instead_of_dropping_the_leaf():
    session = Record(
        items=[
            item(
                'test_each_registered_example_executes_in_the_production_host',
                'example_id',
                'missing',
            )
        ]
    )
    with pytest.raises(AssertionError, match='declared project inventory'):
        actor.project_cases_for_session(session)
