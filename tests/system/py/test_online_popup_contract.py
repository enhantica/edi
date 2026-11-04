"""Owner-declared popup columns, actions, reference metadata and tooltips."""

import pytest

from tests.integration.app.online_load_host import run_online_host


@pytest.fixture(scope='module')
def popup_host(tmp_path_factory):
    with run_online_host(
        tmp_path_factory.mktemp('popup-contract'),
        load_groups_only=True,
        hover_enabled=True,
        failure_entries=False,
        offline_http=True,
        session_type='PopupContractSession',
    ) as host:
        yield host


@pytest.mark.parametrize('source', ['cod', 'collection'])
def test_structure_columns_are_shared_without_kind(popup_host, source):
    popup_host.check('columns', source)


@pytest.mark.parametrize('source', ['cod', 'collection', 'experiment', 'data'])
def test_popup_fields_and_formula_guidance(popup_host, source):
    popup_host.check('fields', source)


@pytest.mark.parametrize('kind', ['structure', 'experiment', 'data'])
def test_each_popup_lists_only_its_kind(popup_host, kind):
    popup_host.check('kind', kind)


@pytest.mark.parametrize('kind', ['structure', 'experiment', 'data'])
def test_popup_formula_search_ignores_amounts_and_prioritizes_exact(popup_host, kind):
    popup_host.check('formula_order', kind)


@pytest.mark.parametrize('name_field', ['commonname', 'mineral', 'chemname', 'title'])
def test_cod_name_is_applied_and_exact_formula_query_is_retained(popup_host, name_field):
    popup_host.check('cod_name_and_formula', name_field)


@pytest.mark.parametrize('authors', ['multi', 'single'])
def test_cod_publication_text_opens_its_injected_doi(popup_host, authors):
    popup_host.check('reference', authors)


def test_nonorthogonal_cell_values_are_visible_in_the_cell_column(popup_host):
    popup_host.check('cell')


@pytest.mark.parametrize('source', ['cod', 'collection'])
@pytest.mark.parametrize('width', ['minimum', 'wide'])
def test_complete_results_table_fits_the_popup(popup_host, source, width):
    popup_host.check('fits', source + '-' + width)


@pytest.mark.parametrize('action', ['button', 'double-click'])
def test_selection_load_and_double_click_use_the_ordinary_loader(popup_host, action):
    popup_host.check('load', action)


@pytest.mark.parametrize('kind', ['structure', 'experiment', 'data'])
@pytest.mark.parametrize('area', ['menu', 'popup'])
@pytest.mark.parametrize('enabled', [False, True])
def test_load_tooltips_follow_the_preferences_switch(popup_host, kind, area, enabled):
    popup_host.check('tooltips', f'{kind}-{area}-{str(enabled).lower()}')
