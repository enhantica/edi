"""Isolated orchestration inputs: authored notebook controls, never diffraction references."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from tests.fixtures.tutorial_cases.contract import ROOT, cases_for

CASES = cases_for('python')


def stage(destination, root=ROOT):
    destination.mkdir()
    shutil.copytree(
        root / 'website',
        destination / 'website',
        ignore=shutil.ignore_patterns(
            '_build',
            '__pycache__',
            '.cache',
            '.tutorials',
            'node_modules',
        ),
    )
    shutil.copytree(
        root / 'tools/checks',
        destination / 'tools/checks',
        ignore=shutil.ignore_patterns('__pycache__'),
    )
    (destination / 'docs/user/tutorials').mkdir(parents=True)
    Path(destination / 'docs/user/cli').symlink_to(
        root / 'docs/user/cli', target_is_directory=True
    )
    shutil.copytree(root / 'app/examples', destination / 'app/examples')
    return destination


def runner_sources(root, *, failed=None):
    folder = root / 'docs/user/tutorials'
    for case in CASES:
        body = [
            '# %% [markdown]',
            '# # Authored runner control',
            '# %%',
            'import builtins, json, os, sys',
            "assert not hasattr(builtins, '_tutorial_control_seen'), 'kernel namespace leaked'",
            'builtins._tutorial_control_seen = True',
            (
                "print('RUNNER_PROOF ' + json.dumps({'pid': os.getpid(), "
                "'cwd': os.getcwd(), 'prefix': sys.prefix}))"
            ),
            'from types import SimpleNamespace',
            "project = SimpleNamespace(display='orchestration control; no physics')",
            'project.display',
        ]
        if case == failed:
            body.append("raise RuntimeError('DELIBERATE_NOTEBOOK_CELL_FAILURE')")
        (folder / (case + '.py')).write_text('\n'.join(body) + '\n')


def run_notebooks(root, cases=()):
    return subprocess.run(
        [sys.executable, str(root / 'website/run_notebooks.py'), *cases],
        cwd=root,
        env={
            **os.environ,
            'EDI_SOURCE_BUILD': '1',
            'PIP_NO_INDEX': '1',
            'PIP_DISABLE_PIP_VERSION_CHECK': '1',
            'JUPYTER_PLATFORM_DIRS': '1',
        },
        capture_output=True,
        text=True,
        timeout=240,
        check=False,
    )


def executed_inputs(root, *, unrun=None, error=None):
    """Supply authored outputs to test conversion only; no scientific execution claim."""
    for case in CASES:
        cells = [
            {'cell_type': 'markdown', 'metadata': {}, 'source': '# Authored conversion control'},
            {
                'cell_type': 'code',
                'metadata': {'tags': ['hide-in-docs']},
                'source': "print('HIDDEN_INPUT_SENTINEL')",
                'execution_count': 1,
                'outputs': [
                    {'output_type': 'stream', 'name': 'stdout', 'text': 'HIDDEN_OUTPUT_SENTINEL'}
                ],
            },
            {
                'cell_type': 'code',
                'metadata': {},
                'source': "raise RuntimeError('CONVERSION_MUST_NOT_EXECUTE')",
                'execution_count': 2,
                'outputs': [
                    {
                        'output_type': 'display_data',
                        'metadata': {},
                        'data': {
                            'text/html': (
                                '<div id="opaque-report-output"><table><tr><td>'
                                'CONVERTED_OUTPUT_SENTINEL</td></tr></table></div>'
                            ),
                        },
                    }
                ],
            },
        ]
        if case == unrun:
            for cell in cells:
                if cell['cell_type'] == 'code':
                    cell.update(execution_count=None, outputs=[])
        if case == error:
            cells[-1]['outputs'] = [
                {
                    'output_type': 'error',
                    'ename': 'RuntimeError',
                    'evalue': 'FAILED_OUTPUT_SENTINEL',
                    'traceback': ['FAILED_OUTPUT_SENTINEL'],
                }
            ]
        document = {'nbformat': 4, 'nbformat_minor': 5, 'metadata': {}, 'cells': cells}
        (root / 'docs/user/tutorials' / (case + '.ipynb')).write_text(json.dumps(document))


CONVERT = """import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(sys.argv[1]) / 'website'))
from render_notebook_pages import render_notebook_pages
options = {'require_outputs': True} if '--require-outputs' in sys.argv[2:] else {}
notebooks = pathlib.Path(sys.argv[1]) / 'docs/user/tutorials'
print(json.dumps(render_notebook_pages(notebooks, **options)))
"""


def convert(root, *, require_outputs=False):
    return subprocess.run(
        [
            sys.executable,
            '-c',
            CONVERT,
            str(root),
            *(['--require-outputs'] if require_outputs else []),
        ],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
