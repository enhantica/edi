# SPDX-License-Identifier: BSD-3-Clause
"""Measure every table on every built docs page in a headless browser.

    python tools/docs/check_table_widths.py website/_build OUT_DIR [PAGE.html ...]

The owner's rules (record 9e9ac914b, 2026-11-09 and 2026-11-10): every docs table fills the content
width, tables of the same shape on one page (as many columns, the same first header) line their
columns up on every content tab, and inline code never wraps between two letters. For each page at
1440 and 820 px windows, with each of its content tabs shown in turn, a table more than 1 px
narrower or wider than the content column fails, so does a group of same-shape tables whose column
boundaries differ by more than 1 px, and so does an inline code element whose line break falls
inside a word (it may break after '.', '_', '[' or a space). The report is OUT_DIR/report.json;
screenshots of the named pages go there too. It needs Playwright and its Chromium,
which no pixi environment declares yet, so it runs where they are installed.
"""

import functools
import http.server
import json
import sys
import threading
from pathlib import Path

try:
    from playwright.sync_api import Error as PlaywrightError
    from playwright.sync_api import sync_playwright
except ImportError as error:
    raise SystemExit('check_table_widths needs Playwright with its Chromium installed') from error

site, out = Path(sys.argv[1]), Path(sys.argv[2])
shots = sys.argv[3:]
out.mkdir(parents=True, exist_ok=True)


class Quiet(http.server.SimpleHTTPRequestHandler):
    """The site's files, without a line per request."""

    def log_message(self, *args: object) -> None:
        """Say nothing."""


server = http.server.ThreadingHTTPServer(
    ('127.0.0.1', 0), functools.partial(Quiet, directory=str(site))
)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f'http://127.0.0.1:{server.server_address[1]}/'

MEASURE = """() => {
  const column = document.querySelector('.md-content .md-typeset');
  if (!column) return null;
  const style = getComputedStyle(column);
  const box = column.getBoundingClientRect();
  const pad = parseFloat(style.paddingLeft) + parseFloat(style.paddingRight);
  const shown = t => t.offsetParent !== null && !t.closest('.highlight, .md-search, [hidden]');
  const tables = [...column.querySelectorAll('table')].filter(shown);
  // Code broken inside a word: each later line must start after '.', '_', '[' or a space.
  const broken = [];
  for (const code of column.querySelectorAll('code')) {
    if (code.closest('pre') || !shown(code) || code.getClientRects().length < 2) continue;
    const text = code.textContent;
    const walker = document.createTreeWalker(code, NodeFilter.SHOW_TEXT);
    let offset = 0, lastTop = null;
    while (walker.nextNode()) {
      const node = walker.currentNode;
      for (let i = 0; i < node.data.length; i++) {
        const range = document.createRange(); range.setStart(node, i); range.setEnd(node, i + 1);
        const rect = range.getBoundingClientRect();
        if (rect.width === 0 && rect.height === 0) continue;
        if (lastTop !== null && rect.top > lastTop + 2) {
          const before = text[offset + i - 1];
          const allowed = !before || '._[ '.includes(before) || node.data[i] === ' ';
          if (!allowed) broken.push(text.slice(0, 60));
        }
        lastTop = rect.top;
      }
      offset += node.data.length;
    }
  }
  return {inner: box.width - pad, left: box.left + parseFloat(style.paddingLeft), broken,
    tables: tables.map(t => {
      const r = t.getBoundingClientRect();
      const head = t.tHead ? [...t.tHead.rows[0].cells].map(c => c.textContent.trim()) : [];
      const row = t.tBodies[0] && t.tBodies[0].rows[0];
      const columns = row ? [...row.cells].map(c => c.getBoundingClientRect().left - r.left) : [];
      return {width: r.width, left: r.left, right: r.right, head, columns,
        cls: t.className, wrapper: t.parentElement.className};
    })};
}"""

pages = sorted(p.relative_to(site).as_posix() for p in site.rglob('*.html'))
report = {'failures': [], 'misaligned': [], 'broken_code': [], 'pages': len(pages), 'tables': 0}
# Each content tab of a page shown in turn: the first of every set, then the second, and so on.
TABS = """(n) => {
  let any = false;
  for (const set of document.querySelectorAll('.tabbed-set')) {
    const inputs = set.querySelectorAll(':scope > input');
    if (inputs[n]) {
      inputs[n].checked = true;
      inputs[n].dispatchEvent(new Event('change', {bubbles: true}));
      any = true;
    }
  }
  return any;
}"""
with sync_playwright() as p:
    browser = p.chromium.launch()
    for width in (1440, 820):
        page = browser.new_page(viewport={'width': width, 'height': 900})
        for rel in pages:
            if 'http-equiv="refresh"' in (site / rel).read_text(errors='replace')[:2000]:
                continue
            page.goto(base + rel, wait_until='load')
            # Same-shape tables of the page, across its tabs: their column boundaries by the shape.
            shapes = {}
            seen = set()
            for tab in range(12):
                if tab and not page.evaluate(TABS, tab):
                    break
                page.wait_for_timeout(50 if tab else 0)
                try:
                    data = page.evaluate(MEASURE)
                except PlaywrightError:
                    page.wait_for_load_state('load')
                    data = page.evaluate(MEASURE)
                if not data:
                    break
                for text in data['broken']:
                    if (rel, text) not in seen:
                        seen.add((rel, text))
                        report['broken_code'].append({'width': width, 'page': rel, 'code': text})
                for index, table in enumerate(data['tables']):
                    report['tables'] += 1
                    short = data['inner'] - table['width']
                    outside = table['right'] - (data['left'] + data['inner'])
                    if short > 1 or outside > 1:
                        report['failures'].append({
                            'width': width,
                            'page': rel,
                            'tab': tab,
                            'table': index,
                            'head': table['head'][:3],
                            'table_px': round(table['width']),
                            'column_px': round(data['inner']),
                            'outside_px': round(outside),
                            'wrapper': table['wrapper'],
                            'class': table['cls'],
                        })
                    if table['head'] and table['columns']:
                        key = (len(table['head']), table['head'][0])
                        shapes.setdefault(key, []).append(table['columns'])
            for key, members in shapes.items():
                if len(members) > 1:
                    spread = max(
                        max(cols[k] for cols in members) - min(cols[k] for cols in members)
                        for k in range(min(len(c) for c in members))
                    )
                    if spread > 1:
                        report['misaligned'].append({
                            'width': width,
                            'page': rel,
                            'head': key[1],
                            'tables': len(members),
                            'spread_px': round(spread),
                        })
        for rel in shots:
            page.goto(base + rel, wait_until='load')
            page.wait_for_timeout(300)
            page.screenshot(path=str(out / f'{rel.replace("/", "_")}-{width}.png'), full_page=True)
        page.close()
    browser.close()
server.shutdown()
(out / 'report.json').write_text(json.dumps(report, indent=1))
print(
    f'{report["pages"]} pages, {report["tables"]} table measurements, '
    f'{len(report["failures"])} short or overflowing, '
    f'{len(report["misaligned"])} misaligned groups, '
    f'{len(report["broken_code"])} inline code broken inside a word'
)
if report['failures'] or report['misaligned'] or report['broken_code']:
    raise SystemExit(1)
