"""The same actual font inventory on the pinned Qt browser kit."""

import pytest

from tests.fixtures.chart_fonts.harness import observe
from tests.system.py.test_chart_fonts import CASES, require_case


@pytest.fixture(scope='module')
def browser_fonts(tmp_path_factory):
    return observe(tmp_path_factory.mktemp('chart-font-browser'))


@pytest.mark.parametrize('case', CASES)
def test_web_ticks_and_titles_share_the_app_font(browser_fonts, case):
    require_case(browser_fonts['exit'].get('code'), browser_fonts['output'], case)
