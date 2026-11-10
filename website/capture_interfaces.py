#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Capture a real Jupyter notebook and terminal from the selected GUI example."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen

from checks.network_browser import Browser

# The notebook is prepared in edi's own Python environment, which the capture process may lack.
try:
    import edi
    import nbformat
    from nbclient import NotebookClient
except ImportError:
    edi = nbformat = NotebookClient = None

ROOT = Path(__file__).resolve().parent


def prepare(edi_root: Path, output: Path, theme: str = 'light') -> None:
    fixture = json.loads((ROOT / 'surfaces/docs/assets/gui/y2o3/manifest.json').read_text())[
        'fixture'
    ]
    example = fixture['id']
    source = edi_root / 'docs/user/cli' / example / 'project'
    workspace = output / 'workspace'
    workspace.mkdir(parents=True)
    shutil.copytree(source, workspace / example)
    cells = nbformat.v4
    del theme  # the chart is the report's view, on its own light paper in both themes
    # The opening of the rewritten tutorial (owner record 2026-11-09): its import, its first staged
    # fit and the chart it shows after it.
    notebook = cells.new_notebook(
        cells=[
            cells.new_code_cell(
                'import easydiffraction as edi\n\n'
                f'project = edi.Project.load({example!r})\n'
                "experiment = project.experiments['spodi']\n"
                'for parameter in project.free_parameters:\n'
                '    parameter.free = False\n'
                'experiment.background.auto_estimate(n_points=21)\n\n'
                "experiment.linked_structures['y2o3'].scale.free = True\n"
                'experiment.instrument.calib_twotheta_offset.free = True\n'
                "project.structures['y2o3'].cell.length_a.free = True\n"
                "result = project.analysis.fit(verbosity='off')"
            ),
            cells.new_code_cell("project.display.pattern('spodi')"),
        ],
        metadata={
            'kernelspec': {
                'name': 'edi-hero',
                'display_name': 'Python 3 (edi)',
                'language': 'python',
            }
        },
    )
    kernel = output / 'jupyter/kernels/edi-hero'
    kernel.mkdir(parents=True)
    (kernel / 'kernel.json').write_text(
        json.dumps({
            'argv': [sys.executable, '-m', 'ipykernel_launcher', '-f', '{connection_file}'],
            'display_name': 'Python 3 (edi)',
            'language': 'python',
        })
    )
    os.environ['JUPYTER_PATH'] = str(output / 'jupyter')
    NotebookClient(
        notebook,
        timeout=120,
        kernel_name='edi-hero',
        resources={'metadata': {'path': str(workspace)}},
    ).execute()
    nbformat.write(notebook, workspace / 'fit.ipynb')
    # The chart is an HTML output, which JupyterLab shows only for a trusted notebook.
    subprocess.run(
        [sys.executable, '-m', 'jupyter', 'trust', str(workspace / 'fit.ipynb')], check=True
    )
    transcript = subprocess.run(
        [sys.executable, '-m', 'edi', 'fit', example, '--dry'],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=True,
    )
    (output / 'command-line.txt').write_text(
        '$ python -m edi fit '
        + example
        + ' --dry\n'
        + '\n'.join(line.rstrip() for line in transcript.stdout.splitlines())
        + '\n'
    )
    (output / 'capture.json').write_text(
        json.dumps(
            {
                'example': example,
                'edi_build_commit': edi.__build_commit__,
                'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'command': ['python', '-m', 'edi', 'fit', example, '--dry'],
            },
            indent=2,
        )
        + '\n'
    )


def _runtime_environment(edi_root: Path, output: Path, python: Path) -> dict:
    """Return the environment for the edi runtime and an isolated Jupyter setup."""
    environment = dict(os.environ)
    environment['PYTHONPATH'] = str(edi_root / 'lib')
    environment.setdefault('EDI_EXTENSION_DIR', str(edi_root / 'build/ci-consumer/python/edi'))
    environment['PATH'] = str(python.parent) + os.pathsep + environment['PATH']
    environment['LD_LIBRARY_PATH'] = str(python.parent.parent / 'lib')
    environment['IPYTHONDIR'] = str(output / 'ipython')
    environment['JUPYTER_CONFIG_DIR'] = str(output / 'config')
    environment['JUPYTERLAB_WORKSPACES_DIR'] = str(output / 'workspaces')
    return environment


def _start_jupyter(
    python: Path, output: Path, environment: dict, theme: str = 'light'
) -> subprocess.Popen:
    environment['JUPYTER_PATH'] = str(output / 'jupyter')
    settings = output / 'settings/@jupyterlab/terminal-extension'
    settings.mkdir(parents=True)
    (settings / 'plugin.jupyterlab-settings').write_text(
        json.dumps({'fontSize': 20, 'theme': theme})
    )
    themes = output / 'settings/@jupyterlab/apputils-extension'
    themes.mkdir(parents=True)
    (themes / 'themes.jupyterlab-settings').write_text(
        json.dumps({'theme': 'JupyterLab Dark' if theme == 'dark' else 'JupyterLab Light'})
    )
    environment['JUPYTERLAB_SETTINGS_DIR'] = str(output / 'settings')
    print('Notebook executed; starting JupyterLab.', flush=True)
    with (output / 'server.log').open('w') as log:
        return subprocess.Popen(
            [
                str(python),
                '-m',
                'jupyterlab',
                '--no-browser',
                '--port=8896',
                '--ServerApp.port_retries=0',
                '--ServerApp.ip=127.0.0.1',
                '--ServerApp.root_dir=' + str(output / 'workspace'),
                '--IdentityProvider.token=',
                '--LabApp.expose_app_in_browser=True',
            ],
            env=environment,
            cwd=output / 'workspace',
            stdout=log,
            stderr=log,
        )


def _wait_for_jupyter(server: subprocess.Popen, output: Path) -> None:
    deadline = time.monotonic() + 30
    while True:
        if server.poll() is not None:
            raise RuntimeError('Jupyter server stopped; see ' + str(output / 'server.log'))
        try:
            with urlopen('http://127.0.0.1:8896/api', timeout=1):
                break
        except OSError:
            if time.monotonic() >= deadline:
                raise TimeoutError('Jupyter server did not become ready') from None
            time.sleep(0.2)


def _capture_notebook(browser: Browser, output: Path) -> None:
    browser.viewport(1480, 800)
    browser.goto('http://127.0.0.1:8896/lab/tree/fit.ipynb')
    page = browser.page
    # The chart is drawn in the display view's frame.
    page.frame_locator('.jp-OutputArea iframe').first.locator('.js-plotly-plot').first.wait_for(
        timeout=60000
    )
    page.evaluate("window.jupyterapp.commands.execute('application:toggle-left-area')")
    decline = page.get_by_role('button', name='No', exact=True)
    if decline.is_visible():
        decline.click()
    page.locator('.jp-CodeCell').first.click()
    browser.wait(0.4)
    browser.shot(output / 'python-notebook.png')
    print('Notebook screenshot saved.', flush=True)


def _capture_terminal(browser: Browser, python: Path, output: Path) -> dict:
    page = browser.page
    page.evaluate("window.jupyterapp.commands.execute('terminal:create-new')")
    page.wait_for_selector('.jp-Terminal:visible .xterm', timeout=15000)
    page.locator('.jp-Terminal:visible .xterm').click()
    setup = (
        'export PATH='
        + str(python.parent)
        + ':$PATH; cd '
        + str(output / 'workspace')
        + "; export PS1='$ '; clear"
    )
    page.keyboard.type(setup, delay=1)
    page.keyboard.press('Enter')
    browser.wait(0.5)
    fixture = json.loads((output / 'capture.json').read_text())
    page.keyboard.type('python -m edi fit ' + fixture['example'] + ' --dry', delay=25)
    page.keyboard.press('Enter')
    page.wait_for_function(
        """() => {
          const buffer=window.jupyterapp.shell.currentWidget.content._term?.buffer.active;
          if (!buffer) return false;
          const lines=Array.from({length:buffer.length}, (_,\
i)=>buffer.getLine(i).translateToString());
          return lines.join(' ').includes('converged');
        }""",
        timeout=30000,
    )
    browser.wait(0.5)
    page.locator('.jp-Terminal:visible').screenshot(path=str(output / 'command-line.png'))
    print('Terminal screenshot saved.', flush=True)
    return fixture


def _publish(output: Path, fixture: dict, theme: str = 'light') -> None:
    destination = ROOT / 'surfaces/docs/assets/interfaces'
    if theme == 'dark':
        # Only the pictures differ by theme; the notebook, transcript and project come from light.
        (destination / 'dark').mkdir(parents=True, exist_ok=True)
        for name in ['python-notebook.png', 'command-line.png']:
            shutil.copy2(output / name, destination / 'dark' / name)
        return
    destination.mkdir(exist_ok=True)
    for name in [
        'python-notebook.png',
        'command-line.png',
        'command-line.txt',
        'capture.json',
    ]:
        shutil.copy2(output / name, destination / name)
    notebook = json.loads((output / 'workspace/fit.ipynb').read_text())
    # The download is for running: it carries the code, not the outputs the screenshot shows.
    for cell in notebook['cells']:
        if cell['cell_type'] == 'code':
            cell['outputs'] = []
            cell['execution_count'] = None
    notebook['metadata'].pop('signature', None)
    notebook['metadata']['kernelspec'] = {
        'name': 'python3',
        'display_name': 'Python 3',
        'language': 'python',
    }
    (destination / 'fit.ipynb').write_text(json.dumps(notebook, indent=1) + '\n')
    shutil.make_archive(
        str(destination / 'example-project'), 'zip', output / 'workspace', fixture['example']
    )


def capture(edi_root: Path, output: Path, python: Path, theme: str = 'light') -> None:
    environment = _runtime_environment(edi_root, output, python)
    subprocess.run(
        [
            str(python),
            str(Path(__file__).resolve()),
            '--prepare',
            '--edi-root',
            str(edi_root),
            '--output',
            str(output),
            '--theme',
            theme,
        ],
        env=environment,
        check=True,
    )
    server = _start_jupyter(python, output, environment, theme)
    browser = None
    try:
        _wait_for_jupyter(server, output)
        browser = Browser('chromium')
        _capture_notebook(browser, output)
        fixture = _capture_terminal(browser, python, output)
        _publish(output, fixture, theme)
    finally:
        if browser:
            browser.close()
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--edi-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--runtime-python', type=Path)
    parser.add_argument('--prepare', action='store_true')
    parser.add_argument('--theme', choices=('light', 'dark'), default='light')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    if args.prepare:
        prepare(args.edi_root.resolve(), args.output.resolve(), args.theme)
    elif args.runtime_python:
        capture(
            args.edi_root.resolve(),
            args.output.resolve(),
            args.runtime_python.resolve(),
            args.theme,
        )
    else:
        parser.error('--runtime-python is required for capture')


if __name__ == '__main__':
    main()
