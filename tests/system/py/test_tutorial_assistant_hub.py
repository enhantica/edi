"""Owner e0a1dc918 replaces the three-page plan with a single User guide overview."""

import pytest
from bs4 import BeautifulSoup

from tests.fixtures.tutorial_cases.assistant_hub import (
    assert_availability,
    hub_navigation,
    local_page,
    observe_bold_group,
    plain,
    redirect_target,
)
from tests.fixtures.tutorial_cases.assistant_versions import assistant_version_sites  # noqa: F401
from tests.fixtures.tutorial_cases.interfaces import assert_scope_prefix
from tests.system.py.test_tutorial_built_tables import children, label


@pytest.fixture(scope='module')
def assistant_hub(assistant_version_sites):  # noqa: F811 - actual public builder
    root = assistant_version_sites['preview']
    page, group, tutorials = hub_navigation(root)
    soup = BeautifulSoup(page.read_text(), 'html.parser')
    assert soup.select_one('main h1') and plain(soup.select_one('main h1')) == 'AI assistant', (
        'Gate 3/4: the User guide group opens the one AI assistant overview'
    )
    return root, page, soup, group, tutorials


def test_shared_assistant_page_has_the_four_environment_availability_table(assistant_hub):
    assert_availability(assistant_hub[2])


def test_user_guide_assistant_group_is_bold_like_tutorials(assistant_hub, tmp_path):
    root, _page, _soup, group, tutorials = assistant_hub
    weights = observe_bold_group(root, group, tutorials, tmp_path / 'browser')
    assert (
        all(weight is not None for weight in weights)
        and float(weights[0]) >= 600
        and weights[0] == weights[1]
    ), 'Gate 3/4: the shared AI group is bold with the same computed weight as Tutorials'


@pytest.mark.parametrize('interface', ['application', 'python', 'cli'])
def test_old_interface_assistant_addresses_redirect_and_have_no_separate_content(
    interface, assistant_hub
):
    root, hub, _soup, _group, _tutorials = assistant_hub
    old = root / interface / 'assistant/index.html'
    assert old.is_file(), 'Gate 3/4: former assistant addresses remain resolvable redirects'
    assert redirect_target(old, root) == hub, (
        'Gate 3/4: former interface overviews redirect to the one User guide page'
    )
    old_soup = BeautifulSoup(old.read_text(), 'html.parser')
    assert old_soup.select_one('main h1') is None, (
        'Gate 3/4: redirected interface addresses do not retain separate AI overview pages'
    )


@pytest.mark.parametrize(
    ('interface', 'folder'),
    [('Application', 'application'), ('Python', 'python'), ('Command line', 'cli')],
)
def test_interface_navigation_keeps_only_its_ai_tutorial(interface, folder, assistant_hub):
    root, _page, _soup, _group, _tutorials = assistant_hub
    home = root / 'index.html'
    soup = BeautifulSoup(home.read_text(), 'html.parser')
    nav = soup.select_one('.md-nav--primary')
    nodes = [item for item in nav.find_all('li') if label(item) == interface]
    assert len(nodes) == 1, 'Gate 3/4: each interface retains exactly its own navigation section'
    groups = children(nodes[0])
    starts = [item for item in groups if label(item) == 'Start here']
    assert len(starts) == 1, 'Gate 3/4: the interface retains its one Start here group'
    assert not any(label(item) == 'AI assistant' for item in children(starts[0])), (
        'Gate 3/4: interface Start here groups have no duplicate AI assistant overview'
    )
    tutorials = [item for item in groups if label(item) == 'Tutorials']
    assert len(tutorials) == 1, 'Gate 3/4: the interface retains its one Tutorials group'
    tutorial = tutorials[0]
    target = root / folder / 'tutorials/assistant/index.html'
    matches = [
        link
        for link in tutorial.select('a[href]')
        if local_page(link['href'], home, root) == target
    ]
    assert len(matches) == 1, 'Gate 3/4: every interface Tutorial section links its AI tutorial'
    if folder == 'application':
        assert_scope_prefix(plain(matches[0]), ['app'])


@pytest.mark.parametrize(
    'damage', [None, 'web-builtin', 'python-own-missing', 'missing-row', 'swapped-columns']
)
def test_availability_observer_refuses_changed_support_and_table_shape(damage):
    html = (
        '<main><table><thead><tr><th>Interface</th><th>Built-in assistant</th>'
        '<th>Your own assistant</th><th>Notes</th></tr></thead><tbody>'
    )
    for name, builtin in [
        ('Desktop app', '✓'),
        ('Web app', '—'),
        ('Python', '—'),
        ('Command line', '—'),
    ]:
        html += (
            '<tr><td>' + name + '</td><td>' + builtin + '</td><td>✓</td><td>Control note</td></tr>'
        )
    soup = BeautifulSoup(html + '</tbody></table></main>', 'html.parser')
    assert_availability(soup)
    if damage == 'web-builtin':
        soup.select('tbody tr')[1].find_all('td')[1].string = '✓'
    elif damage == 'python-own-missing':
        soup.select('tbody tr')[2].find_all('td')[2].string = '—'
    elif damage == 'missing-row':
        soup.select('tbody tr')[-1].decompose()
    elif damage == 'swapped-columns':
        soup.select('th')[1].string, soup.select('th')[2].string = (
            'Your own assistant',
            'Built-in assistant',
        )
    if damage:
        with pytest.raises(AssertionError, match='Gate 3/4:'):
            assert_availability(soup)


@pytest.mark.parametrize('bold', [True, False])
def test_bold_group_witness_reads_actual_css_on_the_inactive_homepage(tmp_path, bold):
    (tmp_path / 'ai').mkdir()
    (tmp_path / 'ai/index.html').write_text('overview control')
    source = """<html><head><style>.bold {font-weight:700}</style></head><body>
    <nav class="md-nav--primary"><ul><li><a>User guide</a><nav><ul>
      <li><a>Analysis workflow</a></li>
      <li><a class="AI_CLASS" href="ai/">AI assistant</a></li>
      <li><a class="bold">Tutorials</a></li>
    </ul></nav></li></ul></nav></body></html>""".replace('AI_CLASS', 'bold' if bold else '')
    (tmp_path / 'index.html').write_text(source)
    _page, group, tutorials = hub_navigation(tmp_path)
    weights = observe_bold_group(tmp_path, group, tutorials, tmp_path / 'browser')
    assert weights == (['700', '700'] if bold else ['400', '700']), (
        'Gate 3/4: the passive browser witness distinguishes actual group weight from its title'
    )
