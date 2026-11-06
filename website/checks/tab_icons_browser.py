"""Check icon spacing after Zensical installs its tab-label anchors."""

from __future__ import annotations

import argparse
import functools
import http.server
import json
import threading
from pathlib import Path

from network_browser import ROOT, Browser, QuietHandler, require

MEASURE = """
return [...document.querySelectorAll('.tabbed-labels .gui-fa, .tabbed-labels .twemoji')]
.filter(icon => icon.getBoundingClientRect().width > 0)
.map(icon => {
  const parent = icon.parentElement;
  const walker = document.createTreeWalker(parent, NodeFilter.SHOW_TEXT);
  let node;
  while ((node = walker.nextNode())) {
    if (!node.textContent.trim() || icon.contains(node) || \
node.parentElement.closest('.gui-sr-only')) continue;
    const range = document.createRange(); range.selectNodeContents(node);
    const text = range.getBoundingClientRect(), box = icon.getBoundingClientRect();
    return {label: parent.textContent.trim(), gap: text.left - box.right,
      display: getComputedStyle(parent).display, align: getComputedStyle(parent).alignItems};
  }
  return {error: 'No adjacent tab label'};
});
"""


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
    results = []
    try:
        for width in (1440, 390):
            browser.viewport(width, 1000)
            for route in ('analysis', 'workspace'):
                browser.goto(f'http://127.0.0.1:{server.server_port}/application/{route}/')
                measured = browser.execute(MEASURE)
                require(measured, (width, route, 'No tab icons'))
                for item in measured:
                    require('error' not in item and 3 <= item['gap'] <= 8, (width, route, item))
                    require(item['display'] == 'flex' and item['align'] == 'center', item)
                results.append({'width': width, 'route': route, 'tabs': measured})
                if route == 'refine':
                    browser.execute(
                        "document.querySelector('.tabbed-labels').scrollIntoView({block:'center'});"
                    )
                    browser.shot(args.output / f'tab-spacing-{width}.png')
        require(not browser.errors, browser.errors)
        report = {'status': 'PASS', 'browser': browser.kind, 'checks': results}
        (args.output / f'tab-icons-{browser.kind}.json').write_text(
            json.dumps(report, indent=2) + '\n'
        )
        print(json.dumps({'status': 'PASS', 'browser': browser.kind, 'widths': [1440, 390]}))
    finally:
        browser.close()
        server.shutdown()


if __name__ == '__main__':
    main()
