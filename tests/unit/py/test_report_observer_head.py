"""Qualify head insertion against actual HTMLParser position state and malformed input."""

import pytest

from tests.fixtures.report_evolution import observe_browser


@pytest.mark.parametrize(
    'prefix', ['<!doctype html><html><head>', '<!doctype html>\n<html>\n<head>']
)
def test_structure_observer_preserves_actual_html_before_and_after_the_head(prefix):
    suffix = '<meta charset="utf-8"></head><body>independent body</body></html>'
    observed = observe_browser._observed_html(prefix + suffix, 'wide', 250, True)
    assert observed.startswith(prefix), (
        'Actual HTML head observation retains every declared prefix byte'
    )
    assert observed.endswith(suffix), (
        'Actual HTML head observation retains every declared suffix byte'
    )
    assert observed.count('const structureDraws') == 1, (
        'The actual structure drawing observer is inserted once before application scripts'
    )


@pytest.mark.parametrize('html', ['<body>no head</body>', '<head></head><head></head>'])
def test_structure_observation_refuses_missing_or_duplicate_actual_heads(html):
    with pytest.raises(ValueError, match=r'(?:actual HTML head|one actual HTML head)'):
        observe_browser._observed_html(html, 'wide', 250, True)
