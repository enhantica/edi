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

from playwright.sync_api import Page, sync_playwright

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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('concept', choices=['surfaces', 'workflows'])
    name = parser.parse_args().concept
    server = http.server.ThreadingHTTPServer(
        ('127.0.0.1', 0), functools.partial(QuietHandler, directory=str(ROOT / '_build'))
    )
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = f'http://127.0.0.1:{server.server_port}'
    output = ROOT / 'screenshots'
    output.mkdir(exist_ok=True)
    docs_path = 'application/refine/' if name == 'surfaces' else 'guides/refine/'
    checks = []
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=os.environ.get('BROWSER_EXECUTABLE', '/opt/brave.com/brave/brave'),
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
        for slug, label in [('', 'home'), (docs_path, 'guide')]:
            response = page.goto(
                f'{origin}/{name}/{slug}', wait_until='networkidle', timeout=12000
            )
            if not response or response.status != 200:
                raise RuntimeError(f'{slug}: page did not return HTTP 200')
            page.locator('main').wait_for()
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
            if name == 'workflows' and label == 'guide':
                _capture_tabs(page, output, name)
                checks.append({'page': docs_path, 'python_interface_tab_works': True})
        page.set_viewport_size({'width': 390, 'height': 844})
        page.goto(f'{origin}/{name}/', wait_until='networkidle', timeout=12000)
        page.screenshot(path=str(output / f'{name}-mobile.png'), full_page=True)
        checks.append({
            'page': '/ mobile',
            'no_horizontal_overflow': page.evaluate(
                'document.documentElement.scrollWidth <= innerWidth'
            ),
        })
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
