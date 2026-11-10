"""Owner dcb14f59b and 67cd65307: actual tutorial image and assistant links resolve."""

from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse

import pytest
from bs4 import BeautifulSoup

from tests.fixtures.tutorial_cases.assistant_hub import follow_page
from tests.fixtures.tutorial_cases.assistant_versions import assistant_version_sites  # noqa: F401
from tests.fixtures.tutorial_cases.contract import cases_for
from tests.fixtures.tutorial_cases.screenshots import assert_no_tutorial_png, assert_page_webp

ROUTES = [
    interface + '/tutorials/' + suffix + 'index.html'
    for interface, key in [('application', 'app'), ('python', 'python'), ('cli', 'cli')]
    for suffix in ['', 'assistant/', *['cases/' + case + '/' for case in cases_for(key)]]
]


@pytest.mark.parametrize('route', ROUTES)
def test_every_built_tutorial_image_resolves_to_webp(
    route,
    assistant_version_sites,  # noqa: F811 - public builder
):
    root = assistant_version_sites['preview']
    page = root / route
    assert page.is_file(), (
        'Gate 4: each declared tutorial page publishes its image entrances: ' + route
    )
    assert_page_webp(page, root)


def test_additional_built_tutorial_pages_also_use_webp(
    assistant_version_sites,  # noqa: F811 - public builder
):
    root = assistant_version_sites['preview']
    actual = {
        page.relative_to(root).as_posix()
        for interface in ['application', 'python', 'cli']
        for page in (root / interface / 'tutorials').rglob('index.html')
    }
    for route in sorted(actual - set(ROUTES)):
        assert_page_webp(root / route, root)


def test_built_tutorial_screenshot_folders_have_no_unused_png(
    assistant_version_sites,  # noqa: F811 - public builder
):
    assert_no_tutorial_png(assistant_version_sites['preview'])


def test_application_assistant_links_the_command_line_assistant_tutorial(
    assistant_version_sites,  # noqa: F811 - public builder
):
    root = assistant_version_sites['preview']
    page = follow_page(root / 'application/assistant/index.html', root)
    soup = BeautifulSoup(page.read_text(), 'html.parser')
    targets = [
        urlparse(urljoin(page.as_uri(), link['href'])) for link in soup.select('main a[href]')
    ]
    target = root / 'cli/tutorials/assistant/index.html'
    assert any(
        url.scheme == 'file'
        and Path(unquote(url.path)).resolve() in {target.resolve(), target.parent.resolve()}
        for url in targets
    ), 'Gate 4/5: the app assistant page links the Command line AI assistant tutorial'
    assert target.is_file(), 'Gate 4/5: the linked Command line assistant tutorial resolves'
