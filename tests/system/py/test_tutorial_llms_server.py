"""Owner 3d85ed388: real local site-serve sends llms.txt as UTF-8 text."""

import os
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

from tests.fixtures.tutorial_cases.contract import ROOT


def test_actual_local_server_declares_utf8_for_the_published_llms_file(tmp_path):
    root = tmp_path / 'site'
    root.mkdir()
    (root / 'llms.txt').write_text('Co₂SiO₄ — \u03c3, μB\n', encoding='utf-8')
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0))
        port = probe.getsockname()[1]
    log_path = tmp_path / 'actual-site-serve.log'
    with log_path.open('w') as log:
        process = subprocess.Popen(
            [
                sys.executable,
                str(ROOT / 'tests/fixtures/tutorial_cases/serve_built_site.py'),
                str(ROOT / 'website/build.py'),
                str(root),
                str(port),
            ],
            stdout=log,
            stderr=subprocess.STDOUT,
            env={**os.environ, 'PYTHONUNBUFFERED': '1'},
            start_new_session=True,
        )
        try:
            deadline = time.monotonic() + 10
            while True:
                assert process.poll() is None, (
                    'Gate 3/5: the actual site-serve process stays alive'
                )
                try:
                    response = urllib.request.urlopen(
                        f'http://127.0.0.1:{port}/llms.txt', timeout=1
                    )
                    break
                except (urllib.error.URLError, TimeoutError):
                    if time.monotonic() >= deadline:
                        raise AssertionError(
                            'Gate 3/5: actual site-serve must answer llms.txt within its '
                            'startup deadline'
                        ) from None
                    time.sleep(0.05)
            with response:
                payload = response.read()
                assert payload == (root / 'llms.txt').read_bytes(), (
                    'Gate 3/5: the real local server serves this exact built '
                    'llms.txt, not another publication'
                )
                assert response.headers.get_content_type() == 'text/plain', (
                    'Gate 3/5: local site-serve marks llms.txt as text/plain'
                )
                assert response.headers.get_content_charset() == 'utf-8', (
                    'Gate 3/5: local site-serve sends charset=utf-8 for llms.txt'
                )
                assert payload.decode('utf-8').encode('utf-8') == payload, (
                    'Gate 3/5: the actual HTTP body retains every UTF-8 byte'
                )
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
            process.wait(timeout=5)
