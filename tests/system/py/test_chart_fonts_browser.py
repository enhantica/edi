"""Actual font fields sampled through the ordinary nonblocking Qt web app loop."""

import pytest

from tests.fixtures.chart_fonts.harness import observe
from tests.system.py.test_chart_fonts import CASES


@pytest.fixture(scope='module')
def browser_fonts(tmp_path_factory):
    return observe(tmp_path_factory.mktemp('chart-font-browser'))


@pytest.mark.parametrize('case', CASES)
def test_web_ticks_and_titles_share_the_app_font(browser_fonts, case):
    assert set(browser_fonts['cases']) == set(CASES), (
        'The browser observes every declared chart and pane exactly once'
    )
    record = browser_fonts['cases'][case]
    assert not record.get('error'), (
        'The actual web chart must populate before font comparison: ' + str(record)
    )
    for phase in ('default', 'changed', 'restored'):
        actual = record[phase]
        expected = actual['app']
        assert expected['family'] and expected['pixels'] > 0, (
            'The actual browser app font has a concrete family and positive pixel size'
        )
        assert (
            actual['title']['family'] == expected['family']
            and actual['title']['pixels'] == expected['pixels']
        ), 'The actual browser axis-title reference uses the shared app font family and pixel size'
        fields, counts = actual['fields'], actual['counts']
        assert fields and all(
            field['family'] == expected['family'] and field['pixels'] == expected['pixels']
            for field in fields
        ), 'Every web tick, title, key and structure label uses its axis-title font: ' + str(
            actual
        )
        if case.startswith('structure-'):
            assert counts['painted'] > 0, (
                'Structure font comparison reaches populated real painted labels'
            )
        elif case == 'correlations':
            assert (
                counts['parameters'] >= 2
                and counts['matrix-names'] >= 2 * counts['parameters']
                and counts['key'] > 0
            ), 'Browser correlation fonts cover both matrix edges and numeric key labels'
        else:
            assert (
                counts['ticks'] >= 2
                and counts['titles'] >= 2
                and {'x-theme', 'y-theme'} <= {field['role'] for field in fields}
            ), 'Browser font equality covers both axis themes, real ticks and own titles'
            if case == 'powder-bragg':
                assert counts['structures'] > 0 and counts['structure-name'] > 0, (
                    'Browser Bragg fonts include actual strip structure names'
                )
            if case in {'stacked', 'map'} and counts['rowLabels']:
                assert counts['row-names'] > 0, (
                    'Browser row-labelled scan charts compare the actual shown dataset-name fonts'
                )
            if case == 'map':
                assert counts['key'] == 2, (
                    'Browser Map font comparison reaches both numeric key endpoints'
                )
    assert (
        record['changed']['app']['family'] != record['default']['app']['family']
        and record['changed']['app']['pixels'] == record['default']['app']['pixels'] + 5
    ), 'The actual browser font stimulus changes the shared family and a nontrivial pixel size'
    assert record['restored']['app'] == record['default']['app'], (
        'The actual browser restores the original shared font after the round trip'
    )
