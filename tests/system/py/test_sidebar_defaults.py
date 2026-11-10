"""Visit every real page/tab with a fresh store and preserve explicit user folds."""

import os
from pathlib import Path

import pytest

from tests.fixtures.fast_chart_redraws.rendering import ROOT, capture

PAGES = ['home', 'project', 'structure', 'experiment', 'analysis', 'report']


@pytest.fixture(scope='module')
def sidebar_captures(request, tmp_path_factory):
    pages = {
        item.callspec.params['page']
        for item in request.session.items
        if item.module is request.module and hasattr(item, 'callspec')
    }
    binary = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    root = tmp_path_factory.mktemp('sidebar-stores')
    result = {}
    for page in sorted(pages):
        store = root / page / 'EasyScience/EasyDiffraction.ini'
        store.parent.mkdir(parents=True)
        assert not store.exists(), (
            'Each sidebar page starts with a genuinely fresh preferences store'
        )
        result[page] = capture(
            [
                binary,
                '-input',
                ROOT / 'tests/system/app/SidebarDefaults.qml',
                '-o',
                '-,txt',
                'SidebarDefaults::test_every_tab:' + page,
            ],
            env=dict(os.environ, EDI_RENDER_ACCEPTANCE_STORE=str(store)),
            timeout=90,
        )
    if any(
        item.name == 'test_existing_sidebar_border_gate_uses_the_new_default'
        for item in request.session.items
        if item.module is request.module
    ):
        result['legacy'] = capture(
            [
                binary,
                '-input',
                ROOT / 'tests/unit/app/tst_e04_t4.qml',
                '-o',
                '-,txt',
                'E04T4FinalIdeas::test_folded_defaults_and_last_visible_border',
            ],
            timeout=90,
        )
    return result


@pytest.mark.parametrize('page', PAGES)
def test_first_group_default_and_remembered_fold_on_every_page(sidebar_captures, page):
    status, output = sidebar_captures[page]
    assert status == 0, 'The actual sidebar first-group contract must pass: ' + output
    assert f'PASS   : edi_app::SidebarDefaults::test_every_tab({page})' in output, (
        'Every actual page must execute the sidebar contract without skipping'
    )
    assert '::SidebarDefaults::cleanupTestCase()' in output, (
        'Each sidebar page process must finish cleanup'
    )


def test_existing_sidebar_border_gate_uses_the_new_default(sidebar_captures):
    status, output = sidebar_captures['legacy']
    assert status == 0, (
        'The existing first-group and separator gate must follow the new default: ' + output
    )
    assert (
        'PASS   : edi_app::E04T4FinalIdeas::test_folded_defaults_and_last_visible_border()'
        in output
    ), 'The adapted existing sidebar gate must execute without skipping'
