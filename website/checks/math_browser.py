#!/usr/bin/env python3
"""Check visible SVG maths and horizontal scrolling in Chromium and mobile WebKit."""

from __future__ import annotations

import argparse
import functools
import http.server
import json
import os
import threading
from itertools import product
from pathlib import Path

from network_browser import ROOT, QuietHandler, require
from playwright.sync_api import sync_playwright

METRICS = """() => {
  const blocks = [...document.querySelectorAll('div.arithmatex')];
  const dimensions = blocks.map(block => {
    const svg = block.querySelector('mjx-container[display="true"] > svg');
    const box = svg?.getBoundingClientRect();
    block.scrollLeft = block.scrollWidth;
    const scroll = block.scrollLeft;
    block.scrollLeft = 0;
    return {width:box?.width, height:box?.height, scroll,
      wider:block.scrollWidth > block.clientWidth + 1};
  });
  return {dimensions, overflow:document.documentElement.scrollWidth > innerWidth,
    errors:document.querySelectorAll('[data-mjx-error],mjx-merror').length};
}"""


def check_page(
    page, base: str, route: str, engine: str, width: int, scheme: str, output: Path
) -> dict:
    page.goto(base + route, wait_until='networkidle')
    page.evaluate('() => MathJax.startup.promise')
    page.evaluate('scheme => document.body.dataset.mdColorScheme=scheme', scheme)
    actual = page.evaluate(METRICS)
    require(actual['dimensions'] and not actual['errors'] and not actual['overflow'], actual)
    require(
        all(row.get('width', 0) > 1 and row.get('height', 0) > 1 for row in actual['dimensions']),
        actual,
    )
    require(all(not row['wider'] or row['scroll'] > 0 for row in actual['dimensions']), actual)
    if (
        engine == 'webkit'
        and width == 390
        and scheme == 'default'
        and route.endswith('absorption/')
    ):
        page.evaluate('document.querySelector(\'link[href*="equations.css"]\').disabled=true')
        broken = page.evaluate(METRICS)
        require(any(row.get('width', 0) <= 1 for row in broken['dimensions']), broken)
        page.evaluate('document.querySelector(\'link[href*="equations.css"]\').disabled=false')
        require(
            all(row.get('width', 0) > 1 for row in page.evaluate(METRICS)['dimensions']),
            'restored fix',
        )
    if width == 390 and route.endswith('absorption/'):
        page.locator('#eq-lobanov').scroll_into_view_if_needed()
        page.screenshot(path=str(output / f'{engine}-{scheme}-lobanov.png'))
    return {'engine': engine, 'width': width, 'scheme': scheme, 'route': route, **actual}


def exercise(browser, engine: str, base: str, output: Path) -> list[dict]:
    results = []
    for width, scheme in product((390, 1440), ('default', 'slate')):
        context = browser.new_context(viewport={'width': width, 'height': 900})
        try:
            page = context.new_page()
            results.extend(
                {
                    'version': browser.version,
                    **check_page(page, base, route, engine, width, scheme, output),
                }
                for route in (
                    'physics/corrections/absorption/',
                    'physics/displacement/',
                    'physics/reliability/',
                )
            )
        finally:
            context.close()
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser', choices=['chromium', 'webkit', 'both'], default='both')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    server = http.server.ThreadingHTTPServer(
        ('127.0.0.1', 0), functools.partial(QuietHandler, directory=str(ROOT / '_build'))
    )
    threading.Thread(target=server.serve_forever, daemon=True).start()
    results = []
    engines = ['chromium', 'webkit'] if args.browser == 'both' else [args.browser]
    try:
        with sync_playwright() as playwright:
            for engine in engines:
                options = {}
                if engine == 'chromium':
                    options['executable_path'] = os.environ.get('BROWSER_EXECUTABLE', 'chromium')
                browser = getattr(playwright, engine).launch(**options)
                try:
                    results.extend(
                        exercise(
                            browser, engine, f'http://127.0.0.1:{server.server_port}/', args.output
                        )
                    )
                finally:
                    browser.close()
        (args.output / 'math.json').write_text(
            json.dumps({'status': 'PASS', 'checks': results}, indent=2) + '\n'
        )
        print(
            json.dumps({'status': 'PASS', 'checks': len(results), 'engines': engines}), flush=True
        )
    finally:
        server.shutdown()


if __name__ == '__main__':
    main()
