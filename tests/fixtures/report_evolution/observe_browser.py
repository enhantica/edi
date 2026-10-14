"""Observe actual saved HTML plot data and layout in an installed browser."""

import json
import os
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

OBSERVER = r"""<script>
window.addEventListener('load', () => {
  const report = () => {
    const plots = [...document.querySelectorAll('.evolution-figure .js-plotly-plot')];
    const result = {selectors: document.querySelectorAll('.evolution-figure select').length,
      viewport: innerWidth, plots: plots.map(plot => {
        const b = plot.getBoundingClientRect();
        return {box: [b.x, b.y, b.width, b.height], traces: plot.data,
          svgCount: plot.querySelectorAll("svg,canvas").length,
          xTitle: plot.layout?.xaxis?.title?.text, yTitle: plot.layout?.yaxis?.title?.text};
      })};
    fetch('/proof?case=CASE', {method: 'POST', body: JSON.stringify(result)});
  };
  requestAnimationFrame(() => requestAnimationFrame(report));
});
</script>"""


def observe(html):
    candidates = [shutil.which(name) for name in ('firefox', 'chromium', 'google-chrome')]
    candidates += [
        '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
        '/Applications/Firefox.app/Contents/MacOS/firefox',
    ]
    browser = next(
        (candidate for candidate in candidates if candidate and Path(candidate).is_file()), None
    )
    if not browser:
        raise RuntimeError('The actual HTML layout observer requires Firefox or Chromium')
    temporary = Path(tempfile.mkdtemp(prefix='edi-evolution-browser-'))
    documents = {
        '/' + name: (html + OBSERVER.replace('CASE', name)).encode() for name in ('wide', 'narrow')
    }
    documents['/'] = (
        b'<!doctype html><iframe width="1200" height="2400" src="/wide"></iframe>'
        b'<iframe width="380" height="2400" src="/narrow"></iframe>'
    )
    received = queue.Queue()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path not in documents:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(documents[self.path])

        def do_POST(self):
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size < 1000000:
                self.send_error(400)
                return
            received.put((self.path.split('case=', 1)[-1], json.loads(self.rfile.read(size))))
            self.send_response(204)
            self.end_headers()

        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    profile = temporary / 'profile'
    profile.mkdir()
    url = f'http://127.0.0.1:{server.server_port}/'
    args = (
        [browser, '--headless', '--no-remote', '--profile', str(profile), url]
        if 'firefox' in Path(browser).name
        else [
            browser,
            '--headless',
            '--disable-gpu',
            '--no-first-run',
            f'--user-data-dir={profile}',
            url,
        ]
    )
    with (temporary / 'browser.log').open('w') as log:
        process = subprocess.Popen(
            args, stdout=log, stderr=log, env={**os.environ, 'MOZ_HEADLESS': '1'}
        )
        try:
            deadline = time.monotonic() + 15
            results = dict(
                received.get(timeout=max(0.01, deadline - time.monotonic())) for _ in range(2)
            )
        finally:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)
            server.shutdown()
            server.server_close()
            shutil.rmtree(temporary)
    return results


if __name__ == '__main__':
    try:
        result = observe(Path(sys.argv[1]).read_text(encoding='utf-8'))
    except (OSError, RuntimeError, ValueError, queue.Empty, subprocess.TimeoutExpired) as error:
        result = {'error': str(error)}
    print(json.dumps(result))
