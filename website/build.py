#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Build the public website (surfaces/) into _build/ and check its generated pages and links."""

from __future__ import annotations

import argparse
import contextlib
import errno
import functools
import hashlib
import html
import http.server
import importlib.metadata
import json
import os
import posixpath
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

import yaml
from checks.gui_capture import validate_bundle
from checks.gui_topics import validate_topics
from render_downloads import render as render_downloads
from render_experiments import render as render_experiments
from render_experiments import write_tutorial_tables
from render_interfaces import render as render_interfaces
from render_learning import render as render_learning
from render_notebook_pages import render_notebook_pages  # puts tools/checks on the path
from render_package_index import write_package_index
from render_parameter_reference import anchor
from render_parameter_reference import render as render_parameter_reference
from render_release_notes import render as render_release_notes
from render_tutorials import render_tutorials
from render_workflow import render as render_workflow

ROOT = Path(__file__).resolve().parent
CONCEPTS = {
    'surfaces': (
        'Choose your interface',
        'Application, Python and Command line have their own top-level sections.',
    ),
}


def _write_reference(built: Path, base_url: str) -> None:
    """Publish the same authored text for retrieval, with canonical working links."""
    docs = ROOT / 'surfaces' / 'docs'
    index = [
        '# EasyDiffraction',
        '',
        '> Scientific explanations and interface instructions for the new EasyDiffraction.',
        '',
        'Identify experiment type, radiation, model and units before selecting an equation.',
        'Cite its exact section. Stored-only fields are not active calculation terms.',
        'The model catalogue records the inspected source snapshot. Interface availability',
        ('comes from Features; planned or proposed work is not available functionality.'),
        'This export supplies reference content; it does not implement a chat integration.',
        '',
        f'- [Model and parameter catalogue]({base_url}physics/catalogue.json)',
        '',
        '## Documentation in Markdown',
        '',
    ]
    for source in sorted(docs.rglob('*.md')):
        relative = source.relative_to(docs)
        text = source.read_text(encoding='utf-8')
        # Entry pages share the title "Start here", so the index uses their specific one.
        specific = re.search(
            r'\A---\n.*?^html_title: "(.+?)"$.*?\n---\n', text, flags=re.DOTALL | re.MULTILINE
        )
        text = re.sub(r'\A---\n.*?\n---\n', '', text, count=1, flags=re.DOTALL).lstrip()
        route = relative.parent if relative.name == 'index.md' else relative.with_suffix('')
        canonical = base_url + (route.as_posix().strip('.') + '/').lstrip('/')

        def link(match: re.Match[str], canonical: str = canonical, source: Path = source) -> str:
            value = match.group(1)
            parsed = urlsplit(value)
            if parsed.scheme or parsed.netloc or value.startswith('/'):
                return match.group(0)
            if not parsed.path:
                return '](' + canonical + value + ')'
            target = (source.parent / unquote(parsed.path)).resolve()
            if not target.is_relative_to(docs):
                raise SystemExit(f'Reference link escapes docs: {source}: {value}')
            target_relative = target.relative_to(docs)
            if target.suffix == '.md':
                target_route = (
                    target_relative.parent
                    if target.name == 'index.md'
                    else target_relative.with_suffix('')
                )
                url = base_url + (target_route.as_posix().strip('.') + '/').lstrip('/')
            else:
                url = base_url + target_relative.as_posix()
            if parsed.fragment:
                url += '#' + parsed.fragment
            return '](' + url + ')'

        # Leave code examples unchanged: paths in code are instructions, not document links.
        blocks = re.split(r'(^```[^\n]*\n.*?^```[^\n]*$)', text, flags=re.MULTILINE | re.DOTALL)
        text = ''.join(
            block if number % 2 else re.sub(r'\]\(([^\s)]+)\)', link, block)
            for number, block in enumerate(blocks)
        )
        destination = built / 'reference' / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(f'Canonical page: {canonical}\n\n{text}', encoding='utf-8')
        title = re.search(r'^# (.+)$', text, flags=re.MULTILINE)
        label = specific[1] if specific else title[1] if title else relative
        index.append(f'- [{label}]({base_url}reference/{relative.as_posix()})')
    (built / 'llms.txt').write_text('\n'.join(index) + '\n', encoding='utf-8')


def _check_catalogue(built: Path) -> None:
    """A model/parameter lookup must resolve to an actual explanatory heading."""
    physics = built / 'physics'
    catalogue = json.loads((physics / 'catalogue.json').read_text(encoding='utf-8'))
    seen = set()

    class Headings(HTMLParser):
        def __init__(self) -> None:
            super().__init__()
            self.ids: set[str] = set()

        def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
            if tag in {'h1', 'h2', 'h3', 'h4'}:
                self.ids.update(value for key, value in attrs if key == 'id' and value)

    for group in ('models', 'parameters'):
        for entry in catalogue[group]:
            identity = (group, entry['category'], entry['id'])
            if identity in seen:
                raise SystemExit(f'Duplicate catalogue entry: {identity}')
            seen.add(identity)
            for field in ('explanation_url', 'parameter_url'):
                if field not in entry:
                    continue
                url = urlsplit(entry[field])
                target = (physics / url.path / 'index.html').resolve()
                if url.scheme or url.netloc or not target.is_relative_to(physics):
                    raise SystemExit(f'Invalid catalogue URL: {entry[field]}')
                parser = Headings()
                parser.feed(target.read_text(encoding='utf-8'))
                if not url.fragment or url.fragment not in parser.ids:
                    raise SystemExit(f'Catalogue heading missing: {entry[field]}')
    print('Scientific catalogue explanation/parameter headings: PASS', flush=True)


def _check_parameter_reference(built: Path) -> None:
    reference = ROOT / 'surfaces/docs/assets/reference'
    if not (reference / 'dictionary.json').exists():
        return
    dictionary = json.loads((reference / 'dictionary.json').read_text())
    links = json.loads((reference / 'parameter-links.json').read_text())
    expected = {row['uid'] for row in dictionary['items']} | {
        row['id'] for row in dictionary['categories']
    }
    if set(links) != expected:
        raise SystemExit('Parameter links must cover the native dictionary exactly')
    target = (built / 'physics/parameters/index.html').read_text()
    for uid, url in links.items():
        if url != 'physics/parameters/#' + anchor(uid) or f'id="{anchor(uid)}"' not in target:
            raise SystemExit(f'Missing native documentation target: {uid}')
    print('Complete native category/item documentation links: PASS', flush=True)


def _write_redirects(root: Path, base_url: str) -> None:
    """Keep links to relocated shared guides valid without a theme plugin."""
    redirects = json.loads((ROOT / 'redirects.json').read_text(encoding='utf-8'))
    for old, new in redirects.items():
        for route in (old, new):
            if not isinstance(route, str) or not re.fullmatch(r'(?:[a-z0-9_-]+/)+', route):
                raise SystemExit(f'Invalid redirect route: {route!r}')
        target = root / new / 'index.html'
        destination = root / old / 'index.html'
        if not target.is_file() or (
            destination.exists()
            and '<title>Page moved - EasyDiffraction</title>' not in destination.read_text()
        ):
            raise SystemExit(f'Redirect must point to a page and not replace one: {old} -> {new}')
        relative = escape(posixpath.relpath(new, old) + '/', quote=True)
        canonical = escape(base_url.rstrip('/') + '/' + new, quote=True)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            '<!doctype html><html lang="en"><head><meta charset="utf-8">'
            f'<meta http-equiv="refresh" content="0; url={relative}">'
            f'<link rel="canonical" href="{canonical}">'
            '<title>Page moved - EasyDiffraction</title></head><body>'
            f'<a href="{relative}">Continue to the User guide</a></body></html>\n',
            encoding='utf-8',
        )


def _check_links(root: Path, base_url: str | None) -> None:
    prefix = urlsplit(base_url).path.rstrip('/') if base_url else ''
    errors = []

    class Links(HTMLParser):
        def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
            if tag not in {'a', 'img', 'image', 'script', 'link'}:
                return
            for key, value in attrs:
                if key not in {'href', 'src'} or not value:
                    continue
                parsed = urlsplit(value)
                if parsed.scheme or parsed.netloc or not parsed.path:
                    continue
                path = unquote(parsed.path)
                if path.startswith('/'):
                    if prefix and path.startswith(prefix + '/'):
                        path = path[len(prefix) :]
                    target = root / path.lstrip('/')
                else:
                    target = self.file.parent / path
                target = target.resolve()
                if target.is_dir():
                    target /= 'index.html'
                if not target.is_relative_to(root) or not target.is_file():
                    errors.append(f'{self.file.relative_to(root)}: {value}')

    for file in root.rglob('*.html'):
        parser = Links()
        parser.file = file
        parser.feed(file.read_text(encoding='utf-8'))
    if errors:
        raise SystemExit('Broken generated links/assets:\n' + '\n'.join(errors[:10]))
    print('Generated internal links and assets: PASS', flush=True)


def _render_sources() -> None:
    """Regenerate the pages and assets that are built from source data."""
    render_interfaces()
    render_experiments()
    render_workflow()
    render_parameter_reference()
    render_learning()


def _normalized_base_url(parser: argparse.ArgumentParser, base_url: str) -> str:
    parsed = urlsplit(base_url)
    if (
        parsed.scheme not in {'http', 'https'}
        or not parsed.netloc
        or parsed.query
        or parsed.fragment
    ):
        parser.error('--base-url must be an HTTP(S) URL without a query or fragment')
    return base_url.rstrip('/') + '/'


def _check_navigation(config_data: dict) -> None:
    stages = list(config_data['extra']['workflow_icons'])
    for interface, folder in (
        ('Application', 'application'),
        ('Python', 'python'),
        ('Command line', 'cli'),
    ):
        section = next(entry[interface] for entry in config_data['nav'] if interface in entry)
        groups = {next(iter(entry)): next(iter(entry.values())) for entry in section}
        names = list(groups)
        if names != ['Start here', 'Analysis workflow', 'Tutorials']:
            raise SystemExit(
                f'{interface}: groups must be Start here, Analysis workflow and Tutorials'
            )
        for name, page in (
            ('Start here', f'{folder}/index.md'),
            ('Analysis workflow', f'{folder}/analysis-workflow/index.md'),
            ('Tutorials', f'{folder}/tutorials/index.md'),
        ):
            if groups[name][0] != page:
                raise SystemExit(f'{interface}: {name} must open {page}')
        found = [next(iter(entry)) for entry in groups['Analysis workflow'][1:]]
        if found != stages:
            raise SystemExit(f'{interface}: Analysis workflow must contain {stages}')
    physics = next(entry['Physics'] for entry in config_data['nav'] if 'Physics' in entry)
    if [next(iter(entry)) for entry in physics] != ['Start here', 'Physical models']:
        raise SystemExit('Physics: groups must be Start here and Physical models')
    print('Shared interface workflow navigation: PASS', flush=True)


def _front_matter(page: str) -> dict:
    """The YAML header of a docs page, or an empty one."""
    path = ROOT / 'surfaces/docs' / page
    if not path.is_file():
        return {}
    text = path.read_text(encoding='utf-8')
    if not text.startswith('---\n'):
        return {}
    return yaml.safe_load(text[4 : text.index('\n---', 4)]) or {}


def _check_nav_icons(config_data: dict) -> None:
    """A navigation group's entries all have an icon, or none has (the owner, 2026-11-09).

    An entry's icon is the one partials/nav-item.html draws: by its title from the interface,
    workflow or section icons, or from its page's `icon` or `category_glyph`. A group's own
    index page opens the group and is not one of its entries.
    """
    extra = config_data['extra']
    by_title = {*extra['interface_icons'], *extra['workflow_icons']}

    def has_icon(entry: object) -> bool:
        if isinstance(entry, str):
            meta = _front_matter(entry)
            return bool(meta.get('icon') or meta.get('category_glyph'))
        ((title, value),) = entry.items()
        if title in by_title:
            return True
        if isinstance(value, list):
            # A bold single-page group (Tutorials, AI assistant) shows its index page's icon.
            if len(value) == 1 and isinstance(value[0], str) and value[0].endswith('index.md'):
                return title in extra['section_icons'] or has_icon(value[0])
            return title in extra['section_icons']
        meta = _front_matter(value)
        return bool(meta.get('icon') or meta.get('category_glyph'))

    def walk(name: str, entries: list) -> None:
        listed = [
            entry
            for position, entry in enumerate(entries)
            if not (position == 0 and isinstance(entry, str) and entry.endswith('index.md'))
        ]
        icons = [has_icon(entry) for entry in listed]
        if any(icons) and not all(icons):
            without = [
                entry if isinstance(entry, str) else next(iter(entry))
                for entry, icon in zip(listed, icons, strict=True)
                if not icon
            ]
            raise SystemExit(
                f'Navigation group {name}: some entries have icons, these not: {without}'
            )
        for entry in listed:
            if isinstance(entry, dict):
                ((title, value),) = entry.items()
                if isinstance(value, list):
                    walk(f'{name} > {title}', value)

    for top in config_data['nav']:
        if isinstance(top, dict):
            ((title, value),) = top.items()
            if isinstance(value, list):
                walk(title, value)
    print('Navigation groups have icons on all entries or none: PASS', flush=True)


def _check_application_groups(config_data: dict) -> None:  # noqa: PLR0914 - one walk per menu level
    """The Application menu repeats the app: one page per sidebar group, in the app's order."""
    groups = json.loads((ROOT / 'application-groups.json').read_text(encoding='utf-8'))
    section = next(entry['Application'] for entry in config_data['nav'] if 'Application' in entry)
    workflow = next(
        entry['Analysis workflow'] for entry in section if 'Analysis workflow' in entry
    )
    for stage in workflow[1:]:
        ((title, pages),) = stage.items()
        expected = groups['stages'][title.lower()]
        found = [next(iter(page.items())) for page in pages[1:]]
        if found != [(entry['title'], entry['page']) for entry in expected]:
            raise SystemExit(f'{title}: the menu must follow application-groups.json')
    entries = [entry for stage in groups['stages'].values() for entry in stage]
    known = {name for entry in entries for name in entry.get('components', [])}
    known.update(groups['undocumented']['components'])
    categories = {entry.get('category') for entry in entries}
    categories.update(groups['undocumented']['categories'])
    app = ROOT.parent / 'app'
    for page in ('Project', 'Structure', 'Experiment', 'Analysis', 'Report'):
        source = (app / f'qml/Pages/{page}/{page}Page.qml').read_text(encoding='utf-8')
        found = set(re.findall(r'^\s+(\w+Group) \{', source, flags=re.MULTILINE)) - {
            'CategoryGroup'
        }
        if found - known:
            raise SystemExit(
                f'{page}: add these sidebar groups to the menu: {sorted(found - known)}'
            )
    model = (app / 'src/category_list_model.cpp').read_text(encoding='utf-8')
    placed = set(re.findall(r'QStringLiteral\("(\w+)"\), \{T::', model))
    if placed - categories:
        raise SystemExit(f'Add these app categories to the menu: {sorted(placed - categories)}')
    # Every group a capture actually saw needs an entry, including groups built at run time.
    names = {entry.get('category') for entry in entries} | {
        entry.get('app_group') for entry in entries
    }
    names.update(groups['undocumented']['categories'])
    for sidecar in (ROOT / 'surfaces/docs/assets/gui').glob('*/*.json'):
        items = json.loads(sidecar.read_text(encoding='utf-8')).get('items', {})
        seen = {key[6:] for key in items if key.startswith('group.') and key.count('.') == 1}
        if seen - names:
            raise SystemExit(
                f'{sidecar.name}: add these groups to the menu: {sorted(seen - names)}'
            )
    print('Application menu follows the app sidebar: PASS', flush=True)


def _check_icons(config_data: dict) -> None:
    """Interface symbols come from the app's font; only brand logos may come from elsewhere."""
    available = {path.stem for path in (ROOT / 'surfaces/overrides/.icons/fa5').glob('*.svg')}
    extra = config_data['extra']
    used = {
        *extra['workflow_icons'].values(),
        *extra['section_icons'].values(),
        *extra['tab_icons'].values(),
        *extra['page_icons'].values(),
    }
    for icons in extra['interface_icons'].values():
        for icon in icons:
            if not icon.startswith(('simple/', 'fontawesome/brands/')):
                used.add(icon.removeprefix('fa5/'))
    sources = [
        *(ROOT / 'surfaces/docs').rglob('*.md'),
        ROOT.parent / 'data/release-interfaces.json',
    ]
    for source in sources:
        text = source.read_text(encoding='utf-8')
        foreign = re.search(
            r':(?:material|lucide|octicons|fontawesome-(?:solid|regular))-[a-z0-9-]+:', text
        )
        declared = re.search(r'\A---\n(?:.*\n)*?icon: (.+)\n(?:.*\n)*?---\n', text)
        if foreign or (declared and not declared[1].startswith('fa5/')):
            raise SystemExit(f'{source}: use a Font Awesome 5 icon (fa5), see ADR-0014')
        used.update(re.findall(r':fa5-([a-z0-9-]+):', text))
        if declared:
            used.add(declared[1].removeprefix('fa5/'))
    if used - available:
        raise SystemExit(
            f'Missing fa5 icons, add to render_fa5_icons.py: {sorted(used - available)}'
        )
    print('App icon set: PASS', flush=True)


def _check_dark(bundle: Path) -> None:
    """Every captured scene needs its dark image, unchanged since it was imported."""
    hashes = bundle / 'dark/hashes.json'
    if not hashes.is_file():
        return
    expected = json.loads(hashes.read_text(encoding='utf-8'))
    manifest = json.loads((bundle / 'manifest.json').read_text(encoding='utf-8'))
    scenes = {scene['image'] for scene in manifest['scenes'] if scene['status'] == 'captured'}
    if scenes - set(expected):
        raise SystemExit(f'{bundle.name}: no dark image for {sorted(scenes - set(expected))[:3]}')
    for image, digest in expected.items():
        if hashlib.sha256((bundle / 'dark' / image).read_bytes()).hexdigest() != digest:
            raise SystemExit(f'{bundle.name}: dark image changed: {image}')
    print(f'Dark {bundle.name} images: PASS', flush=True)


def _check_captures(config_data: dict) -> None:
    scenes = []
    capture = ROOT / 'surfaces/docs/assets/gui/y2o3'
    if (capture / 'manifest.json').exists():
        _, captured = validate_bundle(capture)
        scenes.extend(captured)
        print('Native GUI capture bundle: PASS', flush=True)
    for folder in ('scan', 'joint'):
        reference = ROOT / 'surfaces/docs/assets/gui' / folder
        if (reference / 'manifest.json').exists():
            _, captured = validate_bundle(reference, workflow='reference')
            scenes.extend(captured)
            print(f'Native {folder} reference bundle: PASS', flush=True)
    for folder in ('sc', 'magnetic'):
        reference = ROOT / 'surfaces/docs/assets/gui' / folder
        if (reference / 'manifest.json').exists():
            _, captured = validate_bundle(reference, workflow='reference', groups=True)
            # Each group run starts by opening its project; no guide shows that shared scene.
            scenes.extend(scene for scene in captured if scene['id'] != 'group-open')
            print(f'Native {folder} group bundle: PASS', flush=True)
    for folder in ('y2o3', 'scan', 'joint', 'sc', 'magnetic'):
        _check_dark(ROOT / 'surfaces/docs/assets/gui' / folder)
    if scenes:
        validate_topics(ROOT, config_data, scenes)
        print('Workflow topics and native illustration coverage: PASS', flush=True)


from case_records import SECTIONS, records  # noqa: E402 - on the path render_notebook_pages sets

# The Python tutorial pages this build wrote, as (section, title, page), for the navigation.
TUTORIAL_PAGES: list[tuple[str, str, str]] = []
TUTORIAL_MARKER = '    # python-tutorial-pages\n'
CLI_TUTORIAL_MARKER = '    # cli-tutorial-pages\n'


def _cli_tutorial_pages() -> list[tuple[str, str, str]]:
    """The committed Command line tutorials (render_cli_tutorials.py): section, title, page."""
    pages = []
    for record in records(ROOT.parent):
        page = f'cli/tutorials/cases/{record["id"]}.md'
        if (ROOT / 'surfaces/docs' / page).is_file():
            pages.append((record['section'], record['nav_title'] or record['id'], page))
    return pages


APP_TUTORIAL_MARKER = '    # app-tutorial-pages\n'


def _app_tutorial_pages() -> list[tuple[str, str, str]]:
    """The Application tutorials (render_app_tutorials.py): section, title, page."""
    pages = []
    for record in records(ROOT.parent):
        page = f'application/tutorials/cases/{record["id"]}.md'
        if (ROOT / 'surfaces/docs' / page).is_file():
            pages.append((record['section'], record['nav_title'] or record['id'], page))
    return pages


def _with_assistant(
    pages: list[tuple[str, str, str]], interface: str
) -> list[tuple[str, str, str]]:
    """`pages` with the interface's AI assistant tutorial last in Getting started, if it exists."""
    page = f'{interface}/tutorials/assistant.md'
    if not (ROOT / 'surfaces/docs' / page).is_file():
        return pages
    # The app's own is the built-in assistant (owner record 2026-11-09); the others use one's own.
    label = 'Built-in assistant' if interface == 'application' else 'AI assistant'
    return [*pages, ('Getting started', label, page)]


def _tutorial_navigation(pages: list[tuple[str, str, str]]) -> str:
    """The Python tutorials' navigation: a collapsible group per section, in section order."""
    lines = []
    for section in SECTIONS:
        entries = [(title, path) for name, title, path in pages if name == section]
        if entries:
            lines.append(f'    - {json.dumps(section)}:\n')
            lines.extend(f'      - {json.dumps(title)}: {path}\n' for title, path in entries)
    return ''.join(lines)


def _config_text(name: str, original: str, shared_controls: Path, base_url: str | None) -> str:
    """Return the concept's MkDocs configuration with versioned assets and the site URL."""
    text = original.replace(
        TUTORIAL_MARKER, _tutorial_navigation(_with_assistant(TUTORIAL_PAGES, 'python'))
    )
    text = text.replace(
        CLI_TUTORIAL_MARKER, _tutorial_navigation(_with_assistant(_cli_tutorial_pages(), 'cli'))
    )
    text = text.replace(
        APP_TUTORIAL_MARKER,
        _tutorial_navigation(_with_assistant(_app_tutorial_pages(), 'application')),
    )
    text = text.replace(
        'assets/site-components.css?v=shared',
        'assets/site-components.css?v='
        + hashlib.sha256(shared_controls.read_bytes()).hexdigest()[:12],
    )
    if name == 'surfaces':
        assets = ROOT / 'surfaces/docs/assets'
        digest = hashlib.sha256(
            (assets / 'gui-capture.css').read_bytes()
            + (assets / 'gui-capture.js').read_bytes()
            + (assets / 'interfaces.css').read_bytes()
        ).hexdigest()[:12]
        text = text.replace('extra:\n', f'extra:\n  gui_assets_version: {digest}\n', 1)
    if base_url:
        text, count = re.subn(
            r'^site_url:.*$',
            f'site_url: {base_url}' + (f'{name}/' if name != 'surfaces' else ''),
            text,
            flags=re.MULTILINE,
        )
        if count != 1:
            raise SystemExit(f'{name}: expected exactly one site_url setting')
    return text


def _run_zensical(name: str, shared_controls: Path, base_url: str | None) -> None:
    config = ROOT / name / 'mkdocs.yml'
    temporary = None
    original = config.read_text(encoding='utf-8')
    text = _config_text(name, original, shared_controls, base_url)
    if text != original:
        with tempfile.NamedTemporaryFile(
            mode='w',
            dir=config.parent,
            prefix='.preview-',
            suffix='.yml',
            encoding='utf-8',
            delete=False,
        ) as stream:
            stream.write(text)
            temporary = Path(stream.name)
        config = temporary
    try:
        # The site's own Markdown helpers (edi_highlight.py) import from the website folder.
        path = os.pathsep.join(filter(None, [str(ROOT), os.environ.get('PYTHONPATH', '')]))
        subprocess.run(
            [sys.executable, '-m', 'zensical', 'build', '--strict', '-f', str(config)],
            cwd=ROOT / name,
            check=True,
            env={**os.environ, 'PYTHONPATH': path},
        )
    finally:
        if temporary:
            temporary.unlink(missing_ok=True)


# The assistant prompts link the docs they are published with: the token becomes the build's base
# URL, so a main build names main's site and the dev build the dev site.
DOCS_BASE = 'DOCS_BASE/'
# The address the assistant prompts and llms.txt give, whatever the build's base (owner record
# 2026-11-09).
OFFICIAL_BASE = 'https://easydiffraction.org/'


def _check_tutorial_images() -> None:
    """Refuse a PNG among the tutorial screenshots, which are WebP (owner record 2026-11-09)."""
    gui = ROOT / 'surfaces/docs/assets/gui'
    found = sorted(
        path.relative_to(gui).as_posix()
        for folder in ('cases', 'assistant')
        for path in (gui / folder).rglob('*.png')
    )
    if found:
        raise SystemExit('tutorial screenshots must be WebP: ' + ', '.join(found[:5]))


# The site-wide table rule (owner record 2026-11-09): every docs table fills the content width,
# from one rule in site-components.css; no other stylesheet sets a table's width or display.
TABLE_SELECTOR = r'(table(:not\(\[class\]\))?|\.md-typeset__(table|scrollwrap))$'
TABLE_SAMPLE = (
    'user-guide/features',
    'user-guide/tutorials',
    'physics/models',
    'python/tutorials',
    'about',
)


def _check_table_width(built: Path) -> None:
    """Refuse a table width rule outside site-components.css, and a sample page without it."""
    shared = (built / 'assets/site-components.css').read_text(encoding='utf-8')
    if '.md-typeset table:not([class]){display:table;width:100%}' not in shared:
        raise SystemExit('site-components.css: the full-width table rule is missing')
    problems = []
    for sheet in sorted((built / 'assets').glob('*.css')):
        if sheet.name == 'site-components.css':
            continue
        rules = re.findall(r'([^{}]+)\{([^{}]*)\}', sheet.read_text(encoding='utf-8'))
        for selector, body in rules:
            # A rule on the table or its wrapper itself, not on its cells.
            tables = any(re.search(TABLE_SELECTOR, part.strip()) for part in selector.split(','))
            if tables and re.search(r'(^|;)\s*(width|display)\s*:', body):
                problems.append(f'{sheet.name}: {selector.strip()}')
    for page in TABLE_SAMPLE:
        text = (built / page / 'index.html').read_text(encoding='utf-8')
        if 'assets/site-components.css' not in text:
            problems.append(f'{page}: the shared stylesheet is not loaded')
        if re.search(r'<table[^>]*style="[^"]*width', text):
            problems.append(f'{page}: a table sets its own width')
    if problems:
        raise SystemExit('docs tables must fill the content width: ' + '; '.join(problems[:5]))


def _check_feature_types() -> None:
    """Refuse a Features row without experiment-type tags, or with a tag the code refuses.

    The owner's rule (record 2026-11-09): each row's tags come from website/feature_types.yml. A
    row that names the setting it stands for (its `code`) may carry a type only when an experiment
    of a matching type takes it. Which types take a setting comes from feature_applicability.json,
    generated with the built module and checked against it by `pixi run cli-projects`, so the site
    build never imports a native module.
    """
    from render_experiments import TYPE_TOKENS, feature_code, feature_types  # noqa: PLC0415

    applicability = json.loads((ROOT / 'feature_applicability.json').read_text(encoding='utf-8'))

    page = (ROOT / 'surfaces/docs/user-guide/features.md').read_text(encoding='utf-8')
    untagged = [
        line.split('](', 1)[0][3:]
        for line in page.splitlines()
        if line.startswith('| [') and 'ed-tag' not in line.split('|')[1]
    ]
    if untagged:
        raise SystemExit('Features rows without experiment-type tags: ' + ', '.join(untagged))
    dimensions = {'sampleForm': 0, 'beamMode': 1, 'probe': 2}
    kinds = [tuple(kind) for kind in applicability['types']]
    refused = []
    for text, entries in feature_types().items():
        code = feature_code(text)
        if not code:
            continue
        key = ';'.join(f'{path}={value}' for path, value in sorted(code.items()))
        if key not in applicability['accepts']:
            raise SystemExit(
                f'Features row {text!r} names {key}, which website/feature_applicability.json '
                'does not record: run python tools/docs/feature_applicability.py --write'
            )
        takes = {tuple(kind) for kind in applicability['accepts'][key]}
        for types in entries:
            if types == 'all':
                refused.append(f'{text}: all types, but it names {code}')
                continue
            named = [TYPE_TOKENS[token] for token in types]
            consistent = [
                kind
                for kind in kinds
                if all(
                    kind[dimensions[family]] in {v for f, v in named if f == family}
                    for family in {f for f, _ in named}
                )
            ]
            accepting = [kind for kind in consistent if kind in takes]
            for family, value in named:
                if not any(kind[dimensions[family]] == value for kind in accepting):
                    refused.append(f'{text}: {value} does not take {code}')
    if refused:
        raise SystemExit('Features tags the code refuses:\n' + '\n'.join(refused))
    print('Features experiment-type tags: PASS')


def _check_availability_marks() -> None:
    """Refuse a bare ✓, ✔ or — in an availability table of any docs page.

    The owner's rule (2026-11-09): availability is a status icon with its label, as the Features
    page draws it. A table is an availability table when a cell holds a status icon, the
    not-available mark, ✓ or ✔; in one, a cell of only ✓, ✔ or — is refused. A — elsewhere (a field
    a format does not have) is not availability.
    """
    marks = ('✓', '✔', '—')
    found = []
    for page in sorted((ROOT / 'surfaces/docs').rglob('*.md')):
        lines = page.read_text(encoding='utf-8').splitlines()
        table: list[tuple[int, list[str]]] = []
        for number, line in enumerate([*lines, ''], start=1):
            text = line.strip()
            if text.startswith('|'):
                table.append((number, [cell.strip() for cell in text.strip('|').split('|')]))
                continue
            cells = [cell for _, row in table for cell in row]
            if table and any(
                ':status-' in cell or ':fa5-times-circle:' in cell or cell in marks[:2]
                for cell in cells
            ):
                found.extend(
                    f'{page.relative_to(ROOT)}:{row_number}: {cell}'
                    for row_number, row in table
                    for cell in row
                    if cell in marks
                )
            table = []
    if found:
        raise SystemExit('Availability tables with bare marks:\n' + '\n'.join(found))
    print('Availability tables use status icons: PASS')


def _warn_missing_screenshots() -> None:
    """Name the app tutorial steps still showing the placeholder: a warning, never an error.

    The owner's rule (2026-11-10): a missing or stale screenshot does not stop the site; the page
    shows a neutral placeholder until the next capture.
    """
    found = [
        f'{page.name}: {page.read_text(encoding="utf-8").count("gui-placeholder-box")}'
        for page in sorted((ROOT / 'surfaces/docs/application/tutorials/cases').glob('*.md'))
        if 'gui-placeholder-box' in page.read_text(encoding='utf-8')
    ]
    if found:
        print('WARNING: screenshots coming soon on ' + ', '.join(found), flush=True)
    else:
        print('Every app tutorial step has its screenshot: PASS', flush=True)


def _check_app_stage_symbols() -> None:
    """Refuse an app tutorial stage sentence that names more than two parameters.

    The owner's rule (records 7101f0fd9 and b8df97176, 2026-11-09): a stage names its group as the
    category selector shows it, and a part of one by at most a one-word name filter; never a
    list of parameters. A parameter is a table label or a word typed in the name filter
    (app_groups.py).
    """
    from app_groups import symbols  # noqa: PLC0415

    found = []
    for page in sorted((ROOT / 'surfaces/docs/application/tutorials/cases').glob('*.md')):
        for number, line in enumerate(page.read_text(encoding='utf-8').splitlines(), start=1):
            shown = symbols(line)
            if len(shown) > 2:
                found.append(f'{page.name}:{number}: {", ".join(shown)}')
    if found:
        raise SystemExit('App tutorial stages that list parameters:\n' + '\n'.join(found))
    print('App tutorial stages name groups, not parameters: PASS')


def _check_cif_highlighting(built: Path) -> None:
    """Refuse a CIF or Edi code block that is not highlighted as the app's Text view colours it.

    The owner's record (2026-11-09): every CIF and Edi block on the site goes through
    edi_highlight.py, fenced as ```edi or ```cif.
    """
    from edi_highlight import looks_like_cif  # noqa: PLC0415

    found = []
    for page in sorted(built.rglob('*.html')):
        text = page.read_text(encoding='utf-8')
        for match in re.finditer(
            r'<div class="([^"]*)"><pre[^>]*><span></span><code>(.*?)</code>', text, re.DOTALL
        ):
            if re.search(r'language-(edi|cif)', match[1]):
                continue
            code = html.unescape(re.sub(r'<[^>]+>', '', match[2]))
            if looks_like_cif(code):
                found.append(f'{page.relative_to(built)}: {code.strip().splitlines()[0][:60]}')
    if found:
        raise SystemExit('CIF or Edi blocks without highlighting:\n' + '\n'.join(found[:20]))
    print('CIF and Edi blocks highlighted: PASS')


def _check_features_notes() -> None:
    """Refuse a paragraph directly under a table of the Features page.

    The owner's rule (record 2026-11-09): a note's content goes into the hover titles of the cells
    it qualifies or into the linked explanation page. One introductory paragraph per section stays,
    above its table.
    """
    lines = (
        (ROOT / 'surfaces/docs/user-guide/features.md').read_text(encoding='utf-8').splitlines()
    )
    notes = []
    for index, line in enumerate(lines):
        if not line.startswith('|') or (
            index + 1 < len(lines) and lines[index + 1].startswith('|')
        ):
            continue
        after = next((text for text in lines[index + 1 :] if text.strip()), '')
        if after and not after.startswith(('#', '|', '<span id=', '---')):
            notes.append(f'line {index + 1}: {after[:60]}')
    if notes:
        raise SystemExit('Features page: a paragraph sits under a table:\n' + '\n'.join(notes))
    print('No notes under Features tables: PASS')


def _check_heading_icons(built: Path) -> None:
    """Refuse a page whose headings of one level have icons on some and not others.

    The owner's rule (record 2026-11-09) for navigation groups, extended to each page's heading
    levels, which "On this page" lists: icons on all of a level's headings, or on none.
    """
    problems = []
    for page in sorted(built.rglob('index.html')):
        text = page.read_text(encoding='utf-8')
        start = text.find('<article')
        content = text[start : text.find('</article>', start)] if start >= 0 else ''
        levels: dict[str, list[bool]] = {}
        for level, heading in re.findall(
            r'<h([234])\b[^>]*>(.*?)</h\1>', content, flags=re.DOTALL
        ):
            shown = re.sub(r'<a class="headerlink".*?</a>', '', heading, flags=re.DOTALL)
            levels.setdefault(level, []).append(
                any(mark in shown for mark in ('<svg', 'twemoji', 'ed-reference-icon'))
            )
        problems += [
            f'{page.parent.relative_to(built)} h{level}: {sum(icons)} of {len(icons)}'
            for level, icons in levels.items()
            if any(icons) and not all(icons)
        ]
    if problems:
        raise SystemExit(
            'headings of one level need icons on all or none: ' + '; '.join(problems[:8])
        )
    print('Page headings have icons on all of a level or none: PASS', flush=True)


def _check_tutorial_tags(built: Path) -> None:
    """Refuse a tutorials-catalog row without its tags (owner record 2026-11-09)."""
    pages = [
        built / page / 'index.html'
        for page in (
            'user-guide/tutorials',
            'application/tutorials',
            'python/tutorials',
            'cli/tutorials',
        )
    ]
    missing = []
    for page in pages:
        text = page.read_text(encoding='utf-8')
        rows = re.findall(r'<tr data-example-row\b.*?</tr>', text, flags=re.DOTALL)
        if not rows:
            raise SystemExit(f'{page.relative_to(built)}: no tutorial rows')
        for row in rows:
            tags = re.search(
                r'<span class="ed-example-tags">(.*?)</span></td>', row, flags=re.DOTALL
            )
            if not tags or 'class="ed-tag ' not in tags[1]:
                title = re.search(r'<td[^>]*>(?:<a[^>]*>)?([^<]*)', row)
                missing.append(f'{page.relative_to(built)}: {title[1] if title else row[:80]}')
    if missing:
        raise SystemExit('tutorial rows without tags: ' + '; '.join(missing[:5]))


class _Utf8Handler(http.server.SimpleHTTPRequestHandler):
    """The local server's handler: text files as UTF-8, as GitHub Pages serves them."""

    def guess_type(self, path: str | Path) -> str:
        kind = super().guess_type(path)
        return kind + '; charset=utf-8' if kind in {'text/plain', 'text/markdown'} else kind


class _QuietServer(http.server.ThreadingHTTPServer):
    """The local server, quiet about a request the browser cancels.

    Navigating away mid-load closes the connection; that is not an error worth a traceback.
    """

    def handle_error(self, request: object, client_address: tuple) -> None:
        if isinstance(sys.exc_info()[1], (BrokenPipeError, ConnectionResetError)):
            return
        super().handle_error(request, client_address)


def _serve(folder: Path) -> None:
    """Serve the built site on 127.0.0.1:8873."""
    try:
        server = _QuietServer(
            ('127.0.0.1', 8873), functools.partial(_Utf8Handler, directory=str(folder))
        )
    except OSError as error:
        if error.errno != errno.EADDRINUSE:
            raise
        # A site-serve left running serves the same folder, so the new build is already there.
        raise SystemExit(
            f'Port 8873 is in use: a server already running there serves the freshly built '
            f'{folder}, so reload the browser, or stop it with: lsof -ti :8873 | xargs kill'
        ) from None
    with contextlib.suppress(KeyboardInterrupt):
        server.serve_forever()


def _write_docs_base(built: Path, base_url: str) -> None:
    """Put the base URL into the built assistant pages; refuse a link the build lacks."""
    for page in sorted(built.rglob('*')):
        if not page.is_file() or page.suffix not in {'.html', '.md', '.json', '.txt'}:
            continue
        text = page.read_text(encoding='utf-8')
        if DOCS_BASE not in text:
            continue
        for target in re.findall(re.escape(DOCS_BASE) + r'([\w./-]*)', text):
            path = built / target
            if not (path.is_file() or (path / 'index.html').is_file()):
                raise SystemExit(
                    f'{page.relative_to(built)}: {DOCS_BASE}{target} is not in the build'
                )
        page.write_text(text.replace(DOCS_BASE, base_url), encoding='utf-8')


def _feedback_dialog_texts(qml: str) -> dict:
    """The app's Help and feedback wording, read from its dialog so the site's form matches.

    ADR-0063 keeps one source for each text.
    """

    def one(pattern: str, what: str) -> re.Match:
        found = re.search(pattern, qml)
        if not found:
            raise SystemExit(f'FeedbackDialog.qml: could not find {what}')
        return found

    def by_kind(anchor: str, what: str) -> dict:
        start = qml.find(anchor)
        end = qml.find('})[dialog.kind]', start)
        texts = (
            dict(re.findall(r'"(\w+)": qsTr\("([^"]+)"\)', qml[start:end]))
            if start >= 0 and end > start
            else {}
        )
        if not texts:
            raise SystemExit(f'FeedbackDialog.qml: could not find {what}')
        return texts

    reasons = re.findall(r'ListElement \{\s*value: "(\w+)"\s*text: qsTr\("([^"]+)"\)', qml)
    if not reasons:
        raise SystemExit('FeedbackDialog.qml: could not find the reasons')
    contact = {
        key: one(
            rf'objectName: "feedback\.{key}"[^}}]*?placeholderText: qsTr\("([^"]+)"\)',
            f'the {key} field',
        ).group(1)
        for key in ('name', 'email', 'affiliation')
    }
    # The privacy line as the app shows it without the log and system details, which only the
    # app sends.
    privacy = one(
        r'includeBox\.checked \? qsTr\("[^"]*"\) : qsTr\("([^"]*)"\)\) '
        r'\+ " " \+ qsTr\("([^"]*)"\)',
        'the privacy line',
    )
    # What the app's form says while sending and after the answer, and the label of its button
    # once sent.
    status = one(
        r'text: dialog\.sending \? qsTr\("([^"]*)"\) : dialog\.sent \? qsTr\("([^"]*)"\) : '
        r'dialog\.lastStatus === 429 \? '
        r'qsTr\("([^"]*)"\) : dialog\.lastStatus === 0 \? qsTr\("([^"]*)"\) : qsTr\("([^"]*)"\)',
        'the sending status texts',
    )
    close = one(r'text: dialog\.sent \? qsTr\("([^"]*)"\)', 'the Close button').group(1)
    return {
        'status': dict(
            zip(('sending', 'sent', 'tooMany', 'offline', 'failed'), status.groups(), strict=True)
        ),
        'close': close,
        'reasons': [{'value': value, 'text': text} for value, text in reasons],
        'contact': contact,
        'subject': by_kind('objectName: "feedback.subject"', 'the subject prompts'),
        'message': by_kind('areaObjectName: "feedback.text"', 'the message prompts'),
        'privacy': f'{privacy.group(1)} {privacy.group(2)}',
    }


def _write_feedback_form(built: Path) -> None:
    """Give the Get in touch form the app's feedback address and wording, one source each."""
    preferences = (ROOT.parent / 'app/qml/Globals/Preferences.qml').read_text(encoding='utf-8')
    found = re.findall(
        r'^\s*property string feedbackEndpoint: "(https://[^"]+)"', preferences, flags=re.MULTILINE
    )
    if len(found) != 1:
        raise SystemExit('Preferences.qml: expected one https feedbackEndpoint default')
    texts = _feedback_dialog_texts(
        (ROOT.parent / 'app/qml/Components/FeedbackDialog.qml').read_text(encoding='utf-8')
    )
    form = {'endpoint': found[0], **texts}
    (built / 'assets/feedback-form.js').write_text(
        f'window.edFeedbackForm = {json.dumps(form, ensure_ascii=False)};\n', encoding='utf-8'
    )


def _build_concept(name: str, shared_controls: Path, base_url: str | None, output: Path) -> None:
    _run_zensical(name, shared_controls, base_url)
    built = ROOT / name / 'site'
    if not (built / 'index.html').is_file():
        raise SystemExit(f'{name}: the build did not produce its homepage')
    if name == 'surfaces':
        _write_reference(built, OFFICIAL_BASE)
        _check_tutorial_images()
        _check_tutorial_tags(built)
        _check_table_width(built)
        _check_heading_icons(built)
        _check_features_notes()
        _check_availability_marks()
        _check_app_stage_symbols()
        _warn_missing_screenshots()
        _check_cif_highlighting(built)
        _check_feature_types()
        _write_docs_base(built, OFFICIAL_BASE)
        _write_feedback_form(built)
        _check_catalogue(built)
        _check_parameter_reference(built)
    assembled = output if name == 'surfaces' else output / name
    if assembled.exists() and name != 'surfaces':
        shutil.rmtree(assembled)
    shutil.copytree(built, assembled, dirs_exist_ok=name == 'surfaces')
    if name == 'surfaces':
        _write_redirects(assembled, base_url or 'http://127.0.0.1:8873/')


RELEASES_API = 'https://api.github.com/repos/enhantica/edi/releases?per_page=100&page={}'
RELEASES_CACHE = ROOT / '.cache/edi-releases.json'


def _release_page(number: int) -> list[dict]:
    request = urllib.request.Request(  # noqa: S310 - a fixed https address
        RELEASES_API.format(number),
        headers={'Accept': 'application/vnd.github+json', 'User-Agent': 'edi-site-build'},
    )
    with urllib.request.urlopen(request, timeout=10) as response:  # noqa: S310
        return json.loads(response.read())


def _local_releases() -> list[list[dict]] | None:
    """Fetch the release list for a local build as pages.yml does, cached for an hour.

    CI builds without it, and an offline build keeps the placeholder page.
    """
    if os.environ.get('CI'):
        return None
    if RELEASES_CACHE.is_file() and time.time() - RELEASES_CACHE.stat().st_mtime < 3600:
        return json.loads(RELEASES_CACHE.read_bytes())
    pages: list[list[dict]] = []
    while not pages or len(pages[-1]) == 100:
        try:
            pages.append(_release_page(len(pages) + 1))
        except (OSError, ValueError) as error:
            print(f"What's new: could not fetch the releases ({error}); showing the placeholder.")
            return None
    RELEASES_CACHE.parent.mkdir(exist_ok=True)
    RELEASES_CACHE.write_text(json.dumps(pages), encoding='utf-8')
    return pages


def main() -> None:  # noqa: PLR0915 - the build, step by step
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('concept', choices=[*CONCEPTS, 'all'], nargs='?', default='all')
    parser.add_argument('--base-url', help='Public site root, including the repository URL prefix')
    parser.add_argument('--github-releases', type=Path, help='Paginated GitHub release JSON')
    # The published site refuses a tutorial notebook that was not run; a local build shows its code
    # under a note, or skips the notebook pages for speed (owner record 2026-11-09).
    parser.add_argument(
        '--require-outputs', action='store_true', help='Refuse a tutorial notebook without outputs'
    )
    parser.add_argument(
        '--no-notebooks', action='store_true', help='Skip the tutorial notebook pages'
    )
    parser.add_argument('--serve', action='store_true', help='Serve the built site afterwards')
    args = parser.parse_args()
    if args.require_outputs and args.no_notebooks:
        parser.error('--require-outputs and --no-notebooks exclude each other')
    shared_controls = ROOT / 'surfaces/docs/assets/site-components.css'
    _render_sources()
    if args.base_url:
        args.base_url = _normalized_base_url(parser, args.base_url)
    config_data = yaml.load((ROOT / 'surfaces/mkdocs.yml').read_text(), Loader=yaml.BaseLoader)
    _check_navigation(config_data)
    _check_nav_icons(config_data)
    _check_application_groups(config_data)
    _check_icons(config_data)
    _check_captures(config_data)
    version = importlib.metadata.version('zensical')
    if version != '0.0.73':
        raise SystemExit(f'Expected Zensical 0.0.73; found {version}. Install requirements.txt.')
    names = list(CONCEPTS) if args.concept == 'all' else [args.concept]
    output = ROOT / '_build'
    if args.concept == 'all' and output.exists():
        shutil.rmtree(output)
    changelog = ROOT / 'surfaces/docs/changelog.md'
    desktop = ROOT / 'surfaces/docs/application/desktop.md'
    cli = ROOT / 'surfaces/docs/cli/standalone.md'
    overviews = [
        ROOT / 'surfaces/docs' / folder / 'tutorials/index.md'
        for folder in ('user-guide', 'application', 'python', 'cli')
    ]
    originals = {
        path: path.read_text(encoding='utf-8') for path in (changelog, desktop, cli, *overviews)
    }
    try:
        if 'surfaces' in names:
            TUTORIAL_PAGES[:] = render_notebook_pages(
                ROOT.parent / 'docs/user/tutorials',
                require_outputs=args.require_outputs,
                skip=args.no_notebooks,
            )
            write_tutorial_tables(records(ROOT.parent), {page for _, _, page in TUTORIAL_PAGES})
            render_tutorials(ROOT / 'surfaces/docs/assets/tutorials', ROOT / '.tutorials')
        if args.github_releases:
            releases = json.loads(args.github_releases.read_bytes())
            changelog.write_text(render_release_notes(releases), encoding='utf-8')
            desktop.write_text(render_downloads(originals[desktop], releases), encoding='utf-8')
            cli.write_text(
                render_downloads(originals[cli], releases, kind='cli'), encoding='utf-8'
            )
        elif 'surfaces' in names and (releases := _local_releases()) is not None:
            changelog.write_text(render_release_notes(releases), encoding='utf-8')
        for name in names:
            _build_concept(name, shared_controls, args.base_url, output)
    finally:
        for path, original in originals.items():
            path.write_text(original, encoding='utf-8')
    if 'surfaces' in names:
        write_package_index(output, releases if args.github_releases else [])
        # What list_tutorials and download_tutorial read, at the site's tutorials/ (ADR-0075).
        shutil.copytree(ROOT / '.tutorials', output / 'tutorials', dirs_exist_ok=True)
    _check_links(output.resolve(), args.base_url)
    command = f'python -m http.server 8873 --bind 127.0.0.1 --directory {output}'
    print(f'Preview: {command}', flush=True)
    if args.serve:
        _serve(output)


if __name__ == '__main__':
    main()
