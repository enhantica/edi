"""Owner e0a1dc918: one assistant overview and internal redirect/link witnesses."""

import json
import re
import subprocess
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse

from bs4 import BeautifulSoup

from tests.fixtures.tutorial_cases.assistant_versions import PROMPT_BASE, USER_BASE
from tests.system.py.test_tutorial_built_tables import children, label


def local_page(address, source, root):
    parsed = urlparse(urljoin(source.as_uri(), address))
    public = next(
        (
            urlparse(base)
            for base in (USER_BASE, PROMPT_BASE)
            if parsed.scheme == 'https'
            and parsed.netloc == urlparse(base).netloc
            and parsed.path.startswith(urlparse(base).path)
        ),
        None,
    )
    if public is not None:
        path = root / unquote(parsed.path[len(public.path) :])
    else:
        assert parsed.scheme == 'file' and not parsed.netloc, (
            'Gate 3/4/5: assistant documentation links stay in their actual publication'
        )
        path = Path(unquote(parsed.path))
    if path.is_dir():
        path /= 'index.html'
    assert path.resolve().is_relative_to(root.resolve()) and path.is_file(), (
        'Gate 3/4/5: the assistant document link resolves inside the built site: ' + address
    )
    return path.resolve()


def redirect_target(page, root):
    soup = BeautifulSoup(page.read_text(), 'html.parser')
    refresh = soup.find('meta', attrs={'http-equiv': re.compile(r'^refresh$', re.IGNORECASE)})
    assert refresh is not None, (
        'Gate 3/4: former interface assistant pages redirect to the shared overview'
    )
    match = re.fullmatch(r'\s*\d+\s*;\s*url\s*=\s*(.+)', refresh.get('content', ''), re.IGNORECASE)
    assert match, 'Gate 3/4: the former assistant address has a real redirect target'
    return local_page(match[1].strip('"\''), page, root)


def follow_page(page, root):
    visited = set()
    while True:
        assert page not in visited, 'Gate 3/4: assistant documentation redirects never cycle'
        visited.add(page)
        soup = BeautifulSoup(page.read_text(), 'html.parser')
        if not soup.find('meta', attrs={'http-equiv': re.compile(r'^refresh$', re.IGNORECASE)}):
            return page
        page = redirect_target(page, root)


def hub_navigation(root):
    homepage = root / 'index.html'
    soup = BeautifulSoup(homepage.read_text(), 'html.parser')
    nav = soup.select_one('.md-nav--primary')
    assert nav is not None, 'Gate 3/4: the actual site exposes its primary navigation'
    guides = [node for node in nav.find_all('li') if label(node) == 'User guide']
    assert len(guides) == 1, 'Gate 3/4: one User guide owns the shared assistant overview'
    groups = children(guides[0])
    names = [label(node) for node in groups]
    assert names.count('AI assistant') == 1, 'Gate 3/4: User guide has one AI assistant group'
    index = names.index('AI assistant')
    assert (
        index > 0
        and index + 1 < len(names)
        and names[index - 1 : index + 2] == ['Analysis workflow', 'AI assistant', 'Tutorials']
    ), 'Gate 3/4: AI assistant sits directly after Analysis workflow and before Tutorials'
    group = groups[index]
    link = group.find('a', href=True)
    assert link is not None, 'Gate 3/4: the shared AI assistant group opens its overview page'
    return local_page(link['href'], homepage, root), group, groups[index + 1]


def plain(node):
    clone = BeautifulSoup(str(node), 'html.parser')
    for icon in clone.select('svg, a.headerlink'):
        icon.decompose()
    return ' '.join(clone.get_text(' ', strip=True).split())


def availability_flag(cell):
    text = ' '.join(cell.get_text(' ', strip=True).casefold().split())
    checks = cell.select('input[type=checkbox]')
    if checks:
        assert len(checks) == 1, 'Gate 3/4: one availability cell contains one check state'
        return checks[0].has_attr('checked')
    tokens = {
        text,
        *(node.get('aria-label', '').casefold() for node in cell.select('[aria-label]')),
    }
    if tokens & {'✓', '✔', '☑', 'yes', 'available', 'supported', 'check'}:
        return True
    if text in {'', '—', '\u2013', '-', 'no', 'not available', 'not supported', '✗', '✕', 'times'}:
        return False
    raise AssertionError(
        'Gate 3/4: the availability table exposes an unambiguous check state: ' + text
    )


def assert_availability(soup):
    candidates = []
    for table in soup.select('main table'):
        headers = [
            plain(cell).casefold().replace('\u2011', '-') for cell in table.select('thead th')
        ]
        if 'built-in assistant' in headers and 'your own assistant' in headers:
            candidates.append((table, headers))
    assert len(candidates) == 1, (
        'Gate 3/4: one shared availability table names both assistant routes'
    )
    table, headers = candidates[0]
    assert len(headers) == 4 and headers[1:] == [
        'built-in assistant',
        'your own assistant',
        'notes',
    ], 'Gate 3/4: availability columns are interface, built-in, own assistant and notes'
    rows = table.select('tbody tr')
    expected = [
        ('Desktop app', True, True),
        ('Web app', False, True),
        ('Python', False, True),
        ('Command line', False, True),
    ]
    assert len(rows) == len(expected), (
        'Gate 3/4: the overview covers exactly the four declared environments'
    )
    for row, (name, builtin, own) in zip(rows, expected, strict=True):
        cells = row.find_all(['td', 'th'], recursive=False)
        assert len(cells) == 4 and plain(cells[0]).casefold() == name.casefold(), (
            'Gate 3/4: the availability rows retain the four environments and their order'
        )
        assert availability_flag(cells[1]) == builtin and availability_flag(cells[2]) == own, (
            'Gate 3/4: built-in is desktop-only; own assistants support every declared environment'
        )
        assert plain(cells[3]), 'Gate 3/4: every availability row keeps its explanatory notes'


def css_path(node):
    parts = []
    while node is not None and node.name != '[document]':
        peers = list(node.parent.find_all(node.name, recursive=False))
        parts.append(node.name + ':nth-of-type(' + str(peers.index(node) + 1) + ')')
        node = node.parent
    return ' > '.join(reversed(parts))


def group_label(node):
    return (
        node.find('label', recursive=False)
        or node.find('a', recursive=False)
        or node.find('div', recursive=False)
    )


def observe_bold_group(root, group, tutorials, folder):
    from tests.system.py.test_tutorial_pattern_toolbar import chromium  # noqa: PLC0415

    folder.mkdir()
    selectors = [css_path(group_label(node)) for node in [group, tutorials]]
    script = """<script>window.addEventListener('load', () => {
      const selectors = SELECTORS;
      const weights = selectors.map(selector => {
        const node = document.querySelector(selector);
        const label = node && (node.querySelector('.md-ellipsis') || node);
        return label ? getComputedStyle(label).fontWeight : null;
      });
      const witness = document.createElement('pre'); witness.id = 'assistant-nav-witness';
      witness.textContent = JSON.stringify(weights); document.body.appendChild(witness);
    });</script>""".replace('SELECTORS', json.dumps(selectors))
    source = (
        (root / 'index.html')
        .read_text()
        .replace('<head>', '<head><base href="' + root.as_uri() + '/">', 1)
    )
    page = folder / 'index.html'
    page.write_text(source.replace('</body>', script + '</body>'))
    result = subprocess.run(
        [
            chromium(),
            '--headless',
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-background-networking',
            '--host-resolver-rules=MAP * ~NOTFOUND',
            '--allow-file-access-from-files',
            '--user-data-dir=' + str(folder / 'profile'),
            '--virtual-time-budget=1000',
            '--dump-dom',
            page.as_uri(),
        ],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    (folder / 'browser.stderr').write_text(result.stderr)
    assert result.returncode == 0, (
        'Gate 3/4: the offline browser observes the actual group typography'
    )
    witness = BeautifulSoup(result.stdout, 'html.parser').find(id='assistant-nav-witness')
    assert witness, 'Gate 3/4: the actual navigation emits its computed font weights'
    return json.loads(witness.get_text())
