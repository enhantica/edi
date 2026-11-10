"""Owner 1dc6ac3b3: every built Command line example has equivalent linked entry tabs."""

import re

import pytest
from bs4 import BeautifulSoup

from tests.fixtures.tutorial_cases.browser import observe_html
from tests.system.py.test_tutorial_built_tables import built_site  # noqa: F401 - shared build

COMMAND = re.compile(r'(?m)^\s*(?:\$\s+)?(?:edi|python(?:3)?\s+-m\s+edi)\s+[\w-]+(?=\s|$)[^\n]*')


def commands(code):
    return [
        re.sub(r'^python(?:3)?\s+-m\s+edi\b', 'edi', line.strip().removeprefix('$ '))
        for line in COMMAND.findall(code)
    ]


def assert_command_pairs(page):
    soup = BeautifulSoup(page, 'html.parser')
    pairs = set()
    for code in soup.select('pre code'):
        if not commands(code.get_text()):
            continue
        pair = code.find_parent(class_='tabbed-set')
        assert pair is not None, (
            'Gate 5: every Command line command example is inside its entry-point tab pair'
        )
        pairs.add(id(pair))
        labels = pair.select_one('.tabbed-labels')
        labels = labels.find_all('label', recursive=False) if labels is not None else []
        names = [label.get_text(' ', strip=True) for label in labels]
        assert names == ['Standalone executable', 'Python package'], (
            'Gate 5: command tabs retain the two exact shared installation names'
        )
        blocks = pair.select(':scope > .tabbed-content > .tabbed-block')
        assert len(blocks) == 2, 'Gate 5: a command example has both executable and package panels'
        first, second = [commands(block.get_text()) for block in blocks]
        assert first and first == second, (
            'Gate 5: paired commands differ only by edi versus python -m edi'
        )
        for label in labels:
            target = soup.find('input', id=label.get('for', ''))
            assert target is not None and target.get('type') == 'radio', (
                'Gate 5: both visible tab labels activate their native radio panels'
            )
    return len(pairs)


def test_every_built_command_line_page_uses_equivalent_command_tab_pairs(
    built_site,  # noqa: F811 - shared real build fixture
):
    pages = list((built_site / 'cli').rglob('*.html'))
    assert pages, 'Gate 5: the real site contains Command line pages to check'
    pairs = 0
    for page in pages:
        pairs += assert_command_pairs(page.read_text())
    assert pairs, 'Gate 5: the page walk actually observes command examples'


def test_selecting_a_package_tab_switches_all_command_pairs_on_the_built_page(
    built_site,  # noqa: F811 - shared real build fixture
    tmp_path,
):
    page = built_site / 'cli/fit/index.html'
    source = page.read_text().replace(
        '<head>', '<head><base href="' + page.parent.as_uri() + '/">', 1
    )
    result = observe_html(source, tmp_path / 'command-tabs')
    assert len(result['tabs']) >= 2, (
        'Gate 5: synchronization is observed across multiple real command pairs'
    )
    assert all(checked == [False, True] for checked in result['tabs']), (
        'Gate 5: clicking Python package selects the package panel in every command pair'
    )


def control():
    labels = (
        '<div class="tabbed-labels"><label for="one">Standalone executable</label>'
        '<label for="two">Python package</label></div>'
    )
    panels = (
        '<div class="tabbed-content"><div class="tabbed-block"><pre><code>'
        'edi fit project</code></pre></div><div class="tabbed-block"><pre><code>'
        'python -m edi fit project</code></pre></div></div>'
    )
    return (
        '<div class="tabbed-set"><input type="radio" id="one"><input type="radio" id="two">'
        + labels
        + panels
        + '</div>'
    )


@pytest.mark.parametrize(
    'escape', ['outside', 'renamed', 'different-command', 'missing-panel', 'broken-label']
)
def test_command_pair_observer_refuses_unpaired_or_inequivalent_examples(escape):
    good = control()
    assert assert_command_pairs(good) == 1, (
        'Gate 5: the authored observer control contains one valid pair'
    )
    broken = {
        'outside': '<pre><code>edi fit project</code></pre>',
        'renamed': good.replace('Python package', 'Python'),
        'different-command': good.replace(
            'python -m edi fit project', 'python -m edi calc project'
        ),
        'missing-panel': good.replace('class="tabbed-block"', 'class="other"', 1),
        'broken-label': good.replace('for="two"', 'for="absent"'),
    }[escape]
    with pytest.raises(AssertionError, match='Gate 5:'):
        assert_command_pairs(broken)
