"""Owner 7836b4a78: observe the same five-facet filter geometry on real built overviews."""

import pytest

from tests.fixtures.tutorial_cases.browser import observe_html
from tests.system.py.test_tutorial_built_tables import (
    built_site,  # noqa: F401 - shared native build
)

FACETS = ['purpose', 'fittingMode', 'sampleForm', 'probe', 'beamMode']


def assert_filter_geometry(group):
    selectors = group['selectors']
    assert [row['facet'] for row in selectors] == FACETS, (
        'Gate 3/4: the shared filter exposes exactly the five case facets in order'
    )
    rectangles = [row['rect'] for row in selectors]
    width = rectangles[0]['right'] - rectangles[0]['left']
    height = rectangles[0]['bottom'] - rectangles[0]['top']
    assert width > 0 and height > 0, 'Gate 3/4: filters are actually laid out in the browser'
    assert all(
        abs((box['right'] - box['left']) - width) <= 1
        and abs((box['bottom'] - box['top']) - height) <= 1
        for box in rectangles
    ), 'Gate 3/4: all five selectors have equal rendered sizes'
    search, reset = group['search'], group['reset']
    assert search and reset, 'Gate 3/4: search and reset remain in the shared filter'
    assert abs((reset['right'] - reset['left']) - height) <= 1, (
        'Gate 3/4: reset is square with the same height as the selectors'
    )
    assert all(abs((box['bottom'] - box['top']) - height) <= 1 for box in [search, reset]), (
        'Gate 3/4: search, reset and selectors share one control height'
    )
    assert abs((reset['right'] - search['left']) - width) <= 1, (
        'Gate 3/4: search and reset together occupy one selector-width slot'
    )
    slots = rectangles + [{'left': search['left'], 'top': search['top'], 'right': reset['right']}]
    for index, box in enumerate(slots):
        assert abs(box['left'] - slots[index % 2]['left']) <= 1, (
            'Gate 3/4: controls occupy two equal columns'
        )
        assert abs(box['top'] - slots[index - index % 2]['top']) <= 1, (
            'Gate 3/4: every pair is on one line'
        )
    assert (
        slots[0]['right'] < slots[1]['left']
        and slots[0]['top'] < slots[2]['top'] < slots[4]['top']
    ), 'Gate 3/4: the filter has two separated columns and three successive rows'


@pytest.mark.parametrize('interface', ['application', 'python', 'cli'])
def test_built_interface_lists_share_the_five_selector_search_and_square_reset_layout(
    interface,
    built_site,  # noqa: F811 - shared real build fixture
    tmp_path,
):
    page = built_site / interface / 'tutorials/index.html'
    source = page.read_text().replace(
        '<head>', '<head><base href="' + page.parent.as_uri() + '/">', 1
    )
    result = observe_html(source, tmp_path / 'browser')
    assert len(result['filters']) == 1, (
        'Gate 3/4: each actual overview has one shared filter block'
    )
    assert_filter_geometry(result['filters'][0])


@pytest.mark.parametrize(
    'damage', ['extra-facet', 'width', 'single-column', 'reset-width', 'reset-height']
)
def test_filter_geometry_observer_refuses_drift(damage):
    def rect(x, y, width=160, height=30):
        return {'left': x, 'top': y, 'right': x + width, 'bottom': y + height}

    good = {
        'selectors': [
            {'facet': facet, 'rect': rect((i % 2) * 170, (i // 2) * 40)}
            for i, facet in enumerate(FACETS)
        ],
        'search': rect(170, 80, 120),
        'reset': rect(300, 80, 30),
    }
    assert_filter_geometry(good)
    if damage == 'extra-facet':
        good['selectors'].append(good['selectors'][0])
    elif damage == 'width':
        good['selectors'][3]['rect']['right'] += 7
    elif damage == 'single-column':
        good['selectors'][1]['rect'] = rect(0, 40)
    else:
        good['reset']['right' if damage == 'reset-width' else 'bottom'] += 7
    with pytest.raises(AssertionError, match='Gate 3/4:'):
        assert_filter_geometry(good)
