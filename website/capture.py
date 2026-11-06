#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Capture one concept with Playwright and an installed Chromium-compatible browser."""

from __future__ import annotations

import argparse
import functools
import http.server
import json
import os
import threading
from pathlib import Path

from playwright.sync_api import Locator, Page, sync_playwright

ROOT = Path(__file__).resolve().parent


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    """Serve preview files without per-request terminal noise."""

    def log_message(self, format: str, *args: object) -> None:
        pass


def _capture_tabs(page: Page, output: Path, name: str) -> None:
    section = page.locator('#run-the-refinement')
    section.scroll_into_view_if_needed()
    page.evaluate('window.scrollBy(0, -150)')
    page.screenshot(
        path=str(output / f'{name}-guide-tabs.png'), animations='disabled', full_page=False
    )
    python_tab = page.locator('.md-content label').filter(has_text='Python').first
    python_tab.click()
    visible_code = page.locator('.tabbed-content').get_by_text('import edi', exact=False)
    if not visible_code.is_visible():
        raise RuntimeError('Python interface tab did not reveal its code example')
    if not page.locator('#__tabbed_1_2').is_checked():
        raise RuntimeError('Python interface tab did not become selected')
    page.screenshot(
        path=str(output / f'{name}-guide-python.png'), animations='disabled', full_page=False
    )


def _capture_drawer(page: Page, output: Path, name: str) -> None:
    header = page.locator('.md-header .md-logo')
    header_size = header.locator('svg.ed-wordmark').bounding_box()
    if header.locator('svg').count() != 1 or header.locator('img').count():
        raise RuntimeError('Header must contain one SVG, without light/dark image alternatives')
    colors = []
    for scheme in ['default', 'slate']:
        colors.append(
            header.locator('g[style="fill: currentColor"] path').first.evaluate(
                '(e) => getComputedStyle(e).fill'
            )
        )
        page.locator('.md-header label[for="__drawer"]').click()
        title = page.locator('.md-nav--primary > .md-nav__title')
        if title.locator('svg.ed-wordmark').count() != 1 or title.locator('img').count():
            raise RuntimeError('Drawer must contain one SVG, without image alternatives')
        extra_text = title.evaluate(
            '(e) => Array.from(e.childNodes).filter(n => n.nodeType === 3)'
            '.map(n => n.textContent).join("").trim()'
        )
        size = title.locator('svg.ed-wordmark').bounding_box()
        if extra_text or not size or not header_size:
            raise RuntimeError('Drawer repeats the brand label or has no visible wordmark')
        if size['width'] < 95 or abs(size['height'] - header_size['height']) > 1:
            raise RuntimeError('Drawer wordmark must match the header size')
        page.screenshot(
            path=str(output / f'{name}-drawer-{scheme}.png'), animations='disabled', full_page=True
        )
        page.locator('.md-header label[for="__drawer"]').evaluate('(label) => label.click()')
        if scheme == 'default':
            page.get_by_title('Switch to dark mode', exact=True).click()
    if colors[0] == colors[1]:
        raise RuntimeError('Wordmark lettering did not follow the theme color')


def _pages_to_check(name: str, docs_path: str) -> list[tuple[str, str]]:
    pages = [('', 'home'), (docs_path, 'guide')]
    if name == 'surfaces':
        pages.extend([
            ('user-guide/', 'user-guide'),
            ('user-guide/analysis-workflow/structure/', 'workflow'),
            ('user-guide/features/', 'features'),
            ('physics/profiles/cw/', 'physics-cw'),
            ('physics/profiles/tof/', 'physics-tof'),
            ('physics/corrections/absorption/', 'physics-absorption'),
            ('physics/corrections/extinction/', 'physics-extinction'),
            ('physics/reliability/', 'physics-reliability'),
        ])
        covered = {slug for slug, _ in pages}
        for source in sorted((ROOT / 'surfaces/docs/physics').rglob('*.md')):
            relative = source.relative_to(ROOT / 'surfaces/docs')
            route = relative.parent if source.name == 'index.md' else relative.with_suffix('')
            slug = route.as_posix() + '/'
            if slug not in covered:
                pages.append((slug, slug.rstrip('/').replace('/', '-')))
    return pages


def _check_features(page: Page, slug: str, checks: list) -> None:
    statuses = page.locator('main table span[role="img"]')
    if not statuses.count() or statuses.evaluate_all(
        '(items) => items.some(e => !e.querySelector("svg") || !e.ariaLabel)'
    ):
        raise RuntimeError('Feature status icons must be accessible SVGs')
    tables = page.locator('main table').evaluate_all(
        '(tables) => tables.map(t => '
        '({headers:[...t.querySelectorAll("th")].map(h=>h.querySelector("[role=img]")'
        '?.getAttribute("aria-label") '
        '|| h.innerText.trim()),'
        'iconHeaders:[...t.querySelectorAll("th")].slice(1)'
        '.every(h=>h.querySelector("[role=img] '
        'svg")),'
        'featureWidth:t.querySelector("th").getBoundingClientRect().width,'
        'width:t.getBoundingClientRect().width}))'
    )
    if not tables or any(
        table['headers']
        != [
            'Feature',
            'Web application',
            'Desktop application',
            'Python library',
            'Command Line',
        ]
        or not table['iconHeaders']
        or table['featureWidth'] < table['width'] * 0.5
        for table in tables
    ):
        raise RuntimeError(
            'Feature tables need compact interface columns and labelled icon headers'
        )
    checks.append({'page': slug, 'accessible_svg_status_icons': True})


def _check_equations(page: Page, slug: str, checks: list) -> None:
    math_count = page.locator('.arithmatex').count()
    if slug.startswith('physics/') and math_count:
        page.wait_for_function(
            'Boolean(window.MathJax && MathJax.startup && MathJax.startup.promise)'
        )
        page.evaluate('() => MathJax.startup.promise')
        if page.locator('[data-mjx-error], mjx-merror').count():
            raise RuntimeError(f'{slug}: an equation failed to render')
        unrendered = page.locator('.arithmatex').evaluate_all(
            '(items) => items.filter(e => !e.querySelector("mjx-container[jax=SVG]")).length'
        )
        if unrendered:
            raise RuntimeError(f'{slug}: {unrendered} equations are not rendered as SVG')
        collapsed = page.locator('mjx-container[display="true"] > svg').evaluate_all(
            '(items) => items.filter(e => { const r=e.getBoundingClientRect(); '
            'return r.width<=1 || r.height<=1; }).length'
        )
        if collapsed:
            raise RuntimeError(f'{slug}: display equations collapsed to invisible dimensions')
        checks.append({
            'page': slug,
            'equations_rendered_without_errors': True,
            'equations_checked': math_count,
        })


def _record_page(page: Page, slug: str, label: str, output: Path, name: str, checks: list) -> None:
    page.screenshot(path=str(output / f'{name}-{label}.png'), full_page=False)
    if label == 'home':
        page.screenshot(path=str(output / f'{name}-home-full.png'), full_page=True)
    checks.append({
        'page': slug or '/',
        'heading': page.locator('main h1').first.inner_text(),
        'no_horizontal_overflow': page.evaluate(
            'document.documentElement.scrollWidth <= innerWidth'
        ),
        'images_loaded': page.evaluate(
            'Array.from(document.querySelectorAll("main img"))'
            '.every(i => i.complete && i.naturalWidth > 0)'
        ),
        'left_navigation_visible': page.locator('.md-sidebar--primary').is_visible(),
        'page_outline_visible': page.locator('.md-sidebar--secondary').is_visible(),
    })


def _check_header(page: Page, name: str, checks: list) -> Locator:
    logo = page.locator('.md-header .md-logo svg.ed-wordmark')
    if logo.count() != 1 or not logo.is_visible():
        raise RuntimeError('Official wordmark is missing from the header')
    if page.locator('.md-header__topic').first.is_visible():
        raise RuntimeError('Duplicate brand label is visible')
    if name == 'surfaces':
        tabs = [text.strip() for text in page.locator('.md-tabs__link').all_inner_texts()]
        if tabs != [
            'Home',
            'User guide',
            'Application',
            'Python',
            'Command Line',
            'Physics',
            'About',
        ]:
            raise RuntimeError(f'Unexpected section order: {tabs}')
        checks.append({'shared_guide_before_interfaces': True, 'header_wordmark_only': True})
    return logo


def _check_mobile(
    page: Page, home: str, output: Path, name: str, logo: Locator, checks: list
) -> None:
    page.set_viewport_size({'width': 390, 'height': 844})
    page.goto(home, wait_until='networkidle', timeout=12000)
    if not logo.is_visible():
        raise RuntimeError('Official wordmark is missing on mobile')
    page.screenshot(path=str(output / f'{name}-mobile.png'), full_page=True)
    checks.append({
        'page': '/ mobile',
        'no_horizontal_overflow': page.evaluate(
            'document.documentElement.scrollWidth <= innerWidth'
        ),
    })


def _check_responsive(page: Page, origin: str, output: Path, checks: list) -> None:
    for slug in ['', 'user-guide/features/', 'physics/corrections/extinction/']:
        for width in [320, 390, 768, 1024, 1280, 1360, 1440, 1600, 2560]:
            print(f'Checking {slug or "/"} at {width}px', flush=True)
            page.set_viewport_size({'width': width, 'height': 1000})
            page.goto(f'{origin}/{slug}', wait_until='networkidle', timeout=12000)
            if slug.startswith('physics/'):
                page.evaluate('() => MathJax.startup.promise')
            if page.evaluate('document.documentElement.scrollWidth > innerWidth'):
                raise RuntimeError(f'{slug or "/"}: horizontal overflow at {width}px')
        checks.append({'page': slug or '/', 'responsive_widths_320_to_2560': True})
    page.set_viewport_size({'width': 390, 'height': 844})
    page.goto(f'{origin}/physics/corrections/extinction/', wait_until='networkidle')
    page.evaluate('() => MathJax.startup.promise')
    page.screenshot(path=str(output / 'surfaces-physics-mobile-dark.png'), full_page=False)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('concept', choices=['surfaces'])
    name = parser.parse_args().concept
    server = http.server.ThreadingHTTPServer(
        ('127.0.0.1', 0), functools.partial(QuietHandler, directory=str(ROOT / '_build'))
    )
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = f'http://127.0.0.1:{server.server_port}'
    output = ROOT / '_build-checks'
    output.mkdir(exist_ok=True)
    base_path = '' if name == 'surfaces' else f'{name}/'
    docs_path = 'application/analysis/' if name == 'surfaces' else 'guides/refine/'
    checks = []
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=os.environ.get('BROWSER_EXECUTABLE', 'chromium'),
            headless=True,
            timeout=12000,
            args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu'],
        )
        page = browser.new_page(viewport={'width': 1600, 'height': 1050}, device_scale_factor=1)
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on(
            'response',
            lambda response: (
                errors.append(f'HTTP {response.status}: {response.url}')
                if response.url.startswith(origin) and response.status >= 400
                else None
            ),
        )
        for slug, label in _pages_to_check(name, docs_path):
            print(f'Checking {slug or "/"}', flush=True)
            response = page.goto(
                f'{origin}/{base_path}{slug}', wait_until='networkidle', timeout=12000
            )
            if not response or response.status != 200:
                raise RuntimeError(f'{slug}: page did not return HTTP 200')
            page.locator('main').wait_for()
            if label == 'features':
                _check_features(page, slug, checks)
            _check_equations(page, slug, checks)
            _record_page(page, slug, label, output, name, checks)
            if name == 'workflows' and label == 'guide':
                _capture_tabs(page, output, name)
                checks.append({'page': docs_path, 'python_interface_tab_works': True})
        logo = _check_header(page, name, checks)
        _check_mobile(page, f'{origin}/{base_path}', output, name, logo, checks)
        _capture_drawer(page, output, name)
        checks.append({'single_svg_header_and_drawer': True, 'theme_aware_lettering': True})
        if name == 'surfaces':
            _check_responsive(page, origin, output, checks)
        browser.close()
    server.shutdown()
    report = {'concept': name, 'checks': checks, 'browser_errors': errors}
    (output / f'{name}-browser-checks.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2), flush=True)
    if not all(check.get('no_horizontal_overflow', True) for check in checks):
        raise RuntimeError('horizontal overflow')
    if not all(check.get('images_loaded', True) for check in checks):
        raise RuntimeError('image failed to load')
    if errors:
        raise RuntimeError('browser errors')


if __name__ == '__main__':
    main()
