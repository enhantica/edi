#!/usr/bin/env python3
"""Exercise interface previews, download routes and CLI invocation parity."""

from __future__ import annotations

import argparse
import functools
import http.server
import json
import threading
from pathlib import Path

from network_browser import ROOT, Browser, QuietHandler, require

BUTTON = """
const element=document.querySelector(arg), rect=element.getBoundingClientRect(), \
style=getComputedStyle(element);
return {width:rect.width,height:rect.height,radius:style.borderRadius,font:style.fontSize,
  weight:style.fontWeight,padding:style.padding,border:style.borderWidth,bg:style.backgroundColor};
"""


def check_buttons(browser: Browser, base: str) -> None:
    browser.goto(base)
    browser.hover('.md-header .md-logo')
    reference = browser.execute(BUTTON, '.ed-landing__actions .md-button')
    for route in (
        'application/',
        'application/browser/',
        'application/desktop/',
        'python/',
        'python/setup/',
        'cli/',
        'cli/standalone/',
    ):
        browser.goto(base + route)
        count = browser.execute(
            "document.querySelectorAll('article .md-button').forEach((button,"
            "i)=>button.dataset.checkButton=i); return document.querySelectorAll('article "
            ".md-button').length;"
        )
        for index in range(count):
            selector = f'[data-check-button="{index}"]'
            browser.hover('.md-header .md-logo')
            before = browser.execute(BUTTON, selector)
            require(
                all(
                    before[key] == reference[key]
                    for key in ('radius', 'font', 'weight', 'padding', 'border')
                ),
                (route, before, reference),
            )
            if browser.execute('return document.querySelector(arg).disabled;', selector):
                continue
            browser.hover(selector)
            after = browser.execute(BUTTON, selector)
            require(
                abs(before['width'] - after['width']) < 0.05
                and abs(before['height'] - after['height']) < 0.05,
                (route, before, after),
            )
            require(
                before['font'] == after['font']
                and before['weight'] == after['weight']
                and before['bg'] != after['bg'],
                (route, before, after),
            )


def exercise(browser: Browser, base: str, output: Path) -> list[dict]:
    checks = []
    for width in (1440, 390):
        browser.viewport(width, 1000)
        check_buttons(browser, base)
        for route in ('application/', 'python/', 'cli/'):
            browser.goto(base + route)
            result = browser.execute("""
const hero=document.querySelector('[data-interface-hero]');
const svg=hero.querySelector('svg');
const scale=svg.getBoundingClientRect().width/svg.viewBox.baseVal.width;
return {overflow:document.documentElement.scrollWidth>innerWidth,
  width:hero.getBoundingClientRect().width, \
column:document.querySelector('article').getBoundingClientRect().width,
  title:svg.querySelector('title').textContent,
  captions:hero.querySelectorAll('figcaption').length,
  radius:svg.querySelector('.gui-image-frame').rx.baseVal.value*scale,
  expectedRadius:svg.getBoundingClientRect().width*parseFloat(getComputedStyle(svg).\
getPropertyValue('--ed-screenshot-radius'))/100};
""")
            require(not result['overflow'] and not result['captions'], result)
            require(abs(result['width'] - result['column']) < 1, result)
            require(abs(result['radius'] - result['expectedRadius']) < 0.05, result)
            require(0.01 < result['radius'] / result['width'] < 0.015, result)
            browser.execute("document.querySelector('[data-gui-open]').click();")
            browser.until("document.querySelector('.gui-lightbox')?.open")
            require(
                browser.execute("""
const stage=document.querySelector('.gui-lightbox-stage').getBoundingClientRect();
const capture=document.querySelector('.gui-lightbox .gui-capture'), \
svg=capture.getBoundingClientRect();
const ratio=capture.querySelector('.gui-image-frame').rx.baseVal.value/capture.viewBox.baseVal.\
width;
return svg.width <= stage.width + 1 && svg.height <= stage.height + 1 && \
Math.abs(ratio-.012)<.00001;
"""),
                result,
            )
            browser.execute("document.querySelector('.gui-lightbox-close').click();")
            browser.until("!document.documentElement.classList.contains('gui-lightbox-open')")
            browser.shot(output / f'{browser.kind}-{width}-{route.strip("/")}.png')
            checks.append({'width': width, 'route': route, 'hero': 'PASS'})
        browser.goto(base)
        desktop = browser.execute(
            """return document.querySelector('.ed-landing__interfaces a[href*="desktop"]')"""
            ".getAttribute('href');"
        )
        require(desktop.endswith('application/desktop/#download'), desktop)
        browser.goto(base + 'application/desktop/#download')
        require(
            browser.execute(
                "return document.querySelectorAll('.ed-downloads a.md-button').length === 3 && "
                "[...document.querySelectorAll('.ed-downloads a.md-button')].every(link => "
                "link.href === 'https://github.com/enhantica/edi/releases' && "
                "link.querySelector('svg[aria-hidden=true] path') && "
                "link.querySelector('.ed-download-label small').textContent.trim());"
            )
        )
        require(not browser.execute('return document.documentElement.scrollWidth > innerWidth;'))
        browser.goto(base + 'cli/standalone/#download')
        require(
            browser.execute(
                "return document.querySelectorAll('.ed-downloads button:disabled').length === 3;"
            )
        )
    for page in (ROOT / 'surfaces/docs/cli').glob('*.md'):
        if page.name in {'index.md', 'setup.md', 'python.md', 'standalone.md'}:
            continue
        browser.goto(base + 'cli/' + page.stem + '/')
        pairs = browser.execute("""
return [...document.querySelectorAll('.tabbed-set')].map(group => {
  const panes=group.querySelectorAll('.tabbed-block');
  return [...panes].map(pane=>pane.textContent.trim());
});
""")
        for pair in pairs:
            require(
                len(pair) == 2 and pair[0] == pair[1].replace('python -m edi', 'edi'),
                (page.name, pair),
            )
    require(not browser.errors, browser.errors)
    return checks


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser', choices=['chromium', 'safari'], default='chromium')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    server = http.server.ThreadingHTTPServer(
        ('127.0.0.1', 0), functools.partial(QuietHandler, directory=str(ROOT / '_build'))
    )
    threading.Thread(target=server.serve_forever, daemon=True).start()
    browser = Browser(args.browser)
    try:
        result = {
            'status': 'PASS',
            'browser': args.browser,
            'checks': exercise(browser, f'http://127.0.0.1:{server.server_port}/', args.output),
        }
        (args.output / f'interfaces-{args.browser}.json').write_text(
            json.dumps(result, indent=2) + '\n'
        )
        print(json.dumps(result), flush=True)
    finally:
        browser.close()
        server.shutdown()


if __name__ == '__main__':
    main()
