#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Build the public website (surfaces/) into _build/ and check its generated pages and links."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import posixpath
import re
import shutil
import subprocess
import sys
import tempfile
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

import yaml
from checks.gui_capture import validate_bundle
from checks.gui_topics import validate_topics
from render_downloads import render as render_downloads
from render_experiments import render as render_experiments
from render_interfaces import render as render_interfaces
from render_learning import render as render_learning
from render_parameter_reference import anchor
from render_parameter_reference import render as render_parameter_reference
from render_release_notes import render as render_release_notes
from render_workflow import render as render_workflow

ROOT = Path(__file__).resolve().parent
CONCEPTS = {
    'surfaces': (
        'Choose your interface',
        'Application, Python and Command Line have their own top-level sections.',
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
            if not isinstance(route, str) or not re.fullmatch(r'(?:[a-z0-9-]+/)+', route):
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
        ('Command Line', 'cli'),
    ):
        section = next(entry[interface] for entry in config_data['nav'] if interface in entry)
        groups = {next(iter(entry)): next(iter(entry.values())) for entry in section}
        names = list(groups)
        if names != ['Start here', 'Analysis workflow', 'Examples']:
            raise SystemExit(
                f'{interface}: groups must be Start here, Analysis workflow and Examples'
            )
        for name, page in (
            ('Start here', f'{folder}/index.md'),
            ('Analysis workflow', f'{folder}/analysis-workflow/index.md'),
            ('Examples', f'{folder}/examples/index.md'),
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


def _check_application_groups(config_data: dict) -> None:
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
    names = {entry.get('category') for entry in entries} | {entry.get('app_group') for entry in entries}
    names.update(groups['undocumented']['categories'])
    for sidecar in (ROOT / 'surfaces/docs/assets/gui').glob('*/*.json'):
        items = json.loads(sidecar.read_text(encoding='utf-8')).get('items', {})
        seen = {key[6:] for key in items if key.startswith('group.') and key.count('.') == 1}
        if seen - names:
            raise SystemExit(f'{sidecar.name}: add these groups to the menu: {sorted(seen - names)}')
    print('Application menu follows the app sidebar: PASS', flush=True)


def _check_icons(config_data: dict) -> None:
    """Interface symbols come from the app's font; only brand logos may come from elsewhere."""
    available = {path.stem for path in (ROOT / 'surfaces/overrides/.icons/fa5').glob('*.svg')}
    extra = config_data['extra']
    used = {*extra['workflow_icons'].values(), *extra['section_icons'].values()}
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
            scenes.extend(captured)
            print(f'Native {folder} group bundle: PASS', flush=True)
    for folder in ('y2o3', 'scan', 'joint', 'sc', 'magnetic'):
        _check_dark(ROOT / 'surfaces/docs/assets/gui' / folder)
    if scenes:
        validate_topics(ROOT, config_data, scenes)
        print('Workflow topics and native illustration coverage: PASS', flush=True)


def _config_text(name: str, original: str, shared_controls: Path, base_url: str | None) -> str:
    """Return the concept's MkDocs configuration with versioned assets and the site URL."""
    text = original
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
        subprocess.run(
            [sys.executable, '-m', 'zensical', 'build', '--strict', '-f', str(config)],
            cwd=ROOT / name,
            check=True,
        )
    finally:
        if temporary:
            temporary.unlink(missing_ok=True)


def _build_concept(name: str, shared_controls: Path, base_url: str | None, output: Path) -> None:
    _run_zensical(name, shared_controls, base_url)
    built = ROOT / name / 'site'
    if not (built / 'index.html').is_file():
        raise SystemExit(f'{name}: the build did not produce its homepage')
    if name == 'surfaces':
        _write_reference(built, base_url or 'http://127.0.0.1:8873/')
        _check_catalogue(built)
        _check_parameter_reference(built)
    assembled = output if name == 'surfaces' else output / name
    if assembled.exists() and name != 'surfaces':
        shutil.rmtree(assembled)
    shutil.copytree(built, assembled, dirs_exist_ok=name == 'surfaces')
    if name == 'surfaces':
        _write_redirects(assembled, base_url or 'http://127.0.0.1:8873/')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('concept', choices=[*CONCEPTS, 'all'], nargs='?', default='all')
    parser.add_argument('--base-url', help='Public site root, including the repository URL prefix')
    parser.add_argument('--github-releases', type=Path, help='Paginated GitHub release JSON')
    args = parser.parse_args()
    shared_controls = ROOT / 'surfaces/docs/assets/site-components.css'
    _render_sources()
    if args.base_url:
        args.base_url = _normalized_base_url(parser, args.base_url)
    config_data = yaml.load((ROOT / 'surfaces/mkdocs.yml').read_text(), Loader=yaml.BaseLoader)
    _check_navigation(config_data)
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
    originals = {path: path.read_text(encoding='utf-8') for path in (changelog, desktop, cli)}
    try:
        if args.github_releases:
            releases = json.loads(args.github_releases.read_bytes())
            changelog.write_text(render_release_notes(releases), encoding='utf-8')
            desktop.write_text(render_downloads(originals[desktop], releases), encoding='utf-8')
            cli.write_text(
                render_downloads(originals[cli], releases, kind='cli'), encoding='utf-8'
            )
        for name in names:
            _build_concept(name, shared_controls, args.base_url, output)
    finally:
        if args.github_releases:
            for path, original in originals.items():
                path.write_text(original, encoding='utf-8')
    _check_links(output.resolve(), args.base_url)
    command = f'python -m http.server 8873 --bind 127.0.0.1 --directory {output}'
    print(f'Preview: {command}', flush=True)


if __name__ == '__main__':
    main()
