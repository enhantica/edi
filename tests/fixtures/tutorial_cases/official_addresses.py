"""Owner ad40429ab: official publication addresses and executable user setup instructions."""

import html
import re
from urllib.parse import unquote, urlparse

from bs4 import BeautifulSoup

DOCS = 'https://easydiffraction.org/'
DOWNLOADS = 'https://download.easydiffraction.org/'
INDEX = DOWNLOADS + 'pypi/simple/'
APP = 'https://app.easydiffraction.org/'
URL = re.compile(r'https?://[^\s<>\])`"\']+')


def assert_public_addresses(text):
    decoded = html.unescape(unquote(text))
    assert 'enhantica.github.io' not in decoded.casefold(), (
        'Gate 3/5/6: user pages, notebooks, prompts and llms use '
        'official addresses, not GitHub Pages'
    )


def addresses(text):
    # Raw published URLs cover link attributes and visible prompts without building
    # the full DOM of every SVG-rich user page just to collect its addresses.
    return {match.rstrip('.,;') for match in URL.findall(html.unescape(text))}


def resolve_official(address, roots):
    parsed = urlparse(address)
    bases = {
        urlparse(base).hostname: (base, kind)
        for base, kind in [(DOCS, 'docs'), (DOWNLOADS, 'downloads'), (APP, 'app')]
    }
    host = unquote(parsed.hostname or '').casefold()
    if host not in bases:
        assert not host.endswith('.easydiffraction.org'), (
            'Gate 3/5/6: first-party service links use one of the declared official origins'
        )
        return None  # GitHub sources and independent scientific references remain external.
    assert parsed.scheme == 'https', 'Gate 3/5/6: official service links use HTTPS'
    assert parsed.username is None and parsed.port in {None, 443}, (
        'Gate 3/5/6: official service links retain their canonical origin'
    )
    _, kind = bases[host]
    path = unquote(parsed.path).lstrip('/')
    if kind == 'docs' and path.startswith('dev/'):
        kind, path = 'contributor', path.removeprefix('dev/')
    root = roots[kind].resolve()
    assert root.is_dir(), (
        'Gate 3/5/6: official address resolution requires the corresponding built service artifact'
    )
    target = root / path
    if target.is_dir():
        target /= 'index.html'
    assert target.resolve().is_relative_to(root) and target.is_file(), (
        'Gate 3/5/6: an official address maps to a real file inside its built service: ' + address
    )
    if parsed.fragment and target.suffix == '.html':
        fragment = unquote(parsed.fragment)
        soup = BeautifulSoup(target.read_text(), 'html.parser')
        assert (
            soup.find(id=fragment) is not None or soup.find(attrs={'name': fragment}) is not None
        ), 'Gate 3/5/6: official documentation anchors resolve in the built page'
    return target.resolve()


def assert_setup(text, *, install_routes=False):
    soup = BeautifulSoup(text, 'html.parser')
    plain = soup.get_text(' ', strip=True) if soup.find() else text
    assert not re.search(r'\b(?:VERSION|WHEEL_LINK)\b', plain), (
        'Gate 6: user setup instructions have no VERSION or WHEEL_LINK placeholders'
    )
    assert not re.search(r'\bimport\s+edi\b', plain), (
        'Gate 6: user setup checks import the public easydiffraction package'
    )
    assert re.search(r'\bimport\s+easydiffraction(?:\s+as\s+edi)?\b', plain), (
        'Gate 6: user setup shows a real public package import'
    )
    if not install_routes:
        return
    assert re.search(r'pixi\s+add\s+--pypi\s+easydiffraction\b', plain), (
        'Gate 6: the Pixi route installs the distribution with pixi add --pypi'
    )
    assert INDEX in plain and re.search(r'(?:extra-index-urls|index-url)\s*[=:]', plain), (
        'Gate 6: the Pixi route configures the official package index'
    )
    assert re.search(
        r'pip\s+install\s+easydiffraction\s+--extra-index-url\s+' + re.escape(INDEX), plain
    ), 'Gate 6: the pip route is a directly usable package install with the official extra index'
    heading = re.compile(r'^(?:from source|development|building from source)\b', re.IGNORECASE)
    markdown = re.sub(r'[*`_]', '', text)
    source_headings = re.findall(r'^\s*#{1,6}\s+(.+)$', markdown, re.MULTILINE)
    html_headings = [
        node.get_text(' ', strip=True) for node in soup.find_all(re.compile(r'^h[1-6]$'))
    ]
    assert not any(heading.search(value) for value in [*source_headings, *html_headings]), (
        'Gate 6: source builds belong in contributor docs, with only a link from user setup'
    )
    commands = re.findall(r'```[^\n]*\n(.*?)```', text, flags=re.DOTALL)
    commands.extend(node.get_text() for node in soup.select('pre code'))
    assert not any(
        re.search(
            r'^\s*(?:git\s+clone\b|(?:pixi\s+run\s+)?(?:cmake|ninja)\b'
            r'|pixi\s+run\s+core-build\b|(?:python3?\s+-m\s+)?pip\s+install\s+-e\b)',
            code,
            re.MULTILINE,
        )
        for code in commands
    ), 'Gate 6: user setup does not contain contributor build commands'
