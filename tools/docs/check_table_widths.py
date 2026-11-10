# SPDX-License-Identifier: BSD-3-Clause
"""Measure every table on every built docs page in a headless browser.

    python tools/docs/check_table_widths.py website/_build OUT_DIR [PAGE.html ...]

The owner's rule (record 9e9ac914b and 2026-11-09): every docs table fills the content width, and
tables with the same columns on one page line their columns up. For each page at 1280 and 1440 px
windows, a table more than 2 px narrower or wider than the content column fails, and so does a
group of same-header tables whose columns start at different places. The report is OUT_DIR/
report.json; screenshots of the named pages go there too. It needs Playwright and its Chromium,
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
  return {inner: box.width - pad, left: box.left + parseFloat(style.paddingLeft),
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
report = {'failures': [], 'misaligned': [], 'pages': len(pages), 'tables': 0}
with sync_playwright() as p:
    browser = p.chromium.launch()
    for width in (1280, 1440):
        page = browser.new_page(viewport={'width': width, 'height': 900})
        for rel in pages:
            if 'http-equiv="refresh"' in (site / rel).read_text(errors='replace')[:2000]:
                continue
            page.goto(base + rel, wait_until='load')
            try:
                data = page.evaluate(MEASURE)
            except PlaywrightError:
                page.wait_for_load_state('load')
                data = page.evaluate(MEASURE)
            if not data:
                continue
            groups = {}
            for index, table in enumerate(data['tables']):
                report['tables'] += 1
                short = data['inner'] - table['width']
                outside = table['right'] - (data['left'] + data['inner'])
                if short > 2 or outside > 2:
                    report['failures'].append({
                        'width': width,
                        'page': rel,
                        'table': index,
                        'head': table['head'][:3],
                        'table_px': round(table['width']),
                        'column_px': round(data['inner']),
                        'outside_px': round(outside),
                        'wrapper': table['wrapper'],
                        'class': table['cls'],
                    })
                if table['head']:
                    groups.setdefault(tuple(table['head']), []).append((index, table['columns']))
            for head, members in groups.items():
                if (
                    len(members) > 1
                    and len({tuple(round(x) for x in cols) for _, cols in members}) > 1
                ):
                    report['misaligned'].append({
                        'width': width,
                        'page': rel,
                        'head': list(head)[:3],
                        'tables': len(members),
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
    f'{len(report["misaligned"])} misaligned groups'
)
if report['failures'] or report['misaligned']:
    raise SystemExit(1)
