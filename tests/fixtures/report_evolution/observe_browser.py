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
const errors = [];
window.addEventListener('error', e => errors.push(String(e.message)));
window.addEventListener('unhandledrejection', e => errors.push(String(e.reason)));
const observeLoaded = () => {
  const deadline = performance.now() + RENDER_TIMEOUT;
  const report = ready => {
    const plots = [...document.querySelectorAll('.js-plotly-plot')]
      .filter(plot => plot.closest('.evolution-figure'));
    const result = {selectors: document.querySelectorAll('.evolution-figure select').length,
      viewport: innerWidth, errors, ready,
      patterns: [...document.querySelectorAll('.js-plotly-plot')]
        .filter(plot => plot.closest('.pattern-figure')).map(plot => ({
        traces: (plot.data || []).map(trace => ({
          name: trace.name, line: trace.line, marker: trace.marker,
          mode: trace.mode, x: Array.from(trace.x ?? []), y: Array.from(trace.y ?? []),
          error_x: trace.error_x, error_y: trace.error_y})),
        svgCount: plot.querySelectorAll('svg,canvas').length,
        xTitle: plot.layout?.xaxis?.title?.text, yTitle: plot.layout?.yaxis?.title?.text,
        background: plot._fullLayout?.plot_bgcolor ?? plot.layout?.plot_bgcolor})),
      tables: [...document.querySelectorAll('table')].map(table => ({
        columns: [...table.querySelectorAll('thead th')].map(cell => cell.textContent.trim()),
        rows: [...table.querySelectorAll('tbody tr')].map(row =>
          [...row.querySelectorAll('td')].map(cell => cell.textContent.trim()))})),
      figures: [...document.querySelectorAll('.evolution-figure')].map(f => ({
        className: f.className, text: f.textContent,
        children: [...f.children].map(c => c.className)})), plots: plots.map(plot => {
        const b = plot.getBoundingClientRect();
        return {box: [b.x, b.y, b.width, b.height], traces: plot.data,
          svgCount: plot.querySelectorAll("svg,canvas").length,
          title: plot.layout?.title?.text,
          xTitle: plot.layout?.xaxis?.title?.text, yTitle: plot.layout?.yaxis?.title?.text};
      })};
    fetch('/proof?case=CASE', {method: 'POST', body: JSON.stringify(result)});
  };
  const inspect = () => {
    const plots = [...document.querySelectorAll('.js-plotly-plot')];
    const figures = [...document.querySelectorAll('.pattern-figure,.evolution-figure')];
    const ready = figures.every(figure => figure.matches('.js-plotly-plot')
      || figure.querySelector('.js-plotly-plot') !== null)
      && plots.every(plot => Array.isArray(plot.data)
        && plot.querySelector('svg,canvas') !== null);
    if (ready || performance.now() >= deadline) report(ready);
    else setTimeout(inspect, 25);
  };
  inspect();
};
if (document.readyState === 'complete') observeLoaded();
else window.addEventListener('load', observeLoaded, {once: true});
</script>"""


def receive_pages(received, process, deadline):
    results = {}
    while set(results) != {'wide', 'narrow'}:
        try:
            name, facts = received.get(timeout=max(0.01, deadline - time.monotonic()))
        except queue.Empty as error:
            missing = sorted({'wide', 'narrow'} - results.keys())
            message = f'Browser pages did not report: {missing}; exit={process.poll()}'
            raise RuntimeError(message) from error
        if name not in {'wide', 'narrow'} or name in results:
            raise RuntimeError('Browser proof must identify each viewport exactly once')
        results[name] = facts
    return results


def observe(html, *, render_timeout_ms=5000):
    if type(render_timeout_ms) is not int or not 0 < render_timeout_ms <= 5000:
        raise ValueError('The browser drawing deadline must be an integer from 1 to 5000 ms')
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
        '/' + name: (
            html + OBSERVER.replace('CASE', name).replace('RENDER_TIMEOUT', str(render_timeout_ms))
        ).encode()
        for name in ('wide', 'narrow')
    }
    documents['/'] = (
        b'<!doctype html><iframe width="1200" height="2400" src="/wide"></iframe>'
        b'<iframe width="220" height="2400" src="/narrow"></iframe>'
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
    environment = {**os.environ, 'MOZ_HEADLESS': '1'}
    # The native runner's report-writer fault shim must stay in that runner. Firefox's
    # sandbox also forks processes; loading the writer interposer there can crash them.
    fault_directory = environment.get('EDI_REPORT_ACCEPTANCE_PRELOADED')
    if fault_directory:
        for key in ('LD_PRELOAD', 'DYLD_INSERT_LIBRARIES'):
            libraries = [
                item
                for item in environment.get(key, '').split(':')
                if item and Path(item).parent != Path(fault_directory)
            ]
            if libraries:
                environment[key] = ':'.join(libraries)
            else:
                environment.pop(key, None)
    with (temporary / 'browser.log').open('w') as log:
        process = subprocess.Popen(args, stdout=log, stderr=log, env=environment)
        try:
            # Allow browser startup and both frames to load on slower CI runners.
            # Each page still has its own drawing deadline.
            results = receive_pages(received, process, time.monotonic() + 60)
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
        result = {'error': type(error).__name__ + ': ' + str(error)}
    print(json.dumps(result))
