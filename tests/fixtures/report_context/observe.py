"""Compare actual Python facade and CLI report writers with generation time neutralized."""

import contextlib
import html
import json
import re
import subprocess
import sys
from pathlib import Path

import edi


def model(text):
    match = re.search(
        r'<script[^>]*id=["\']edi-report-model["\'][^>]*>(.*?)</script>', text, re.DOTALL
    )
    if match is None:
        raise ValueError('The actual report HTML has no model JSON')
    document = json.loads(match[1])
    generated = document['generated']
    document['generated'] = ''
    return document, text.replace(
        match[1], json.dumps(document, separators=(',', ':'), ensure_ascii=False)
    ).replace(generated, '') if generated else text


folder = Path(sys.argv[1])
project = edi.Project.load(folder)
choices = {'colour_scheme': sys.argv[2], 'correlation_experiment': sys.argv[3]}
cli_choices = ['--colour-scheme', sys.argv[2], '--correlation-experiment', sys.argv[3]]
result = {
    'binding': str(edi._edi.__file__),
    'inputs': choices,
    'canonical_model': json.loads(project.report.model().to_json()),
}
result['python_model_json'] = project.report.model(**choices).to_json()
document = json.loads(result['python_model_json'])
document['generated'] = ''
result['python_model'] = document
for name, text in [
    ('python_html', project.report.as_html(**choices)),
    (
        'python_display',
        html.unescape(re.search(r'srcdoc="(.*?)"', project.report._repr_html_(), re.DOTALL)[1]),
    ),
]:
    result[name] = model(text)[0]
path = folder / 'context-output.html'
project.report.save_html(path, **choices)
result['python_save_html'] = model(path.read_text())[0]
completed = subprocess.run(
    [sys.executable, '-m', 'edi', 'report', str(folder), '--output', str(path), *cli_choices],
    capture_output=True,
    text=True,
    check=False,
    timeout=15,
)
if completed.returncode:
    raise RuntimeError(completed.stdout + completed.stderr)
result['cli_output'] = model(path.read_text())[0]
result['python_check'] = project.report.check()
completed = subprocess.run(
    [sys.executable, '-m', 'edi', 'report', str(folder), '--check'],
    capture_output=True,
    text=True,
    check=False,
    timeout=15,
)
result['cli_check'] = {'code': completed.returncode, 'text': completed.stdout + completed.stderr}
with contextlib.redirect_stdout(sys.stderr):
    project.report.save(**choices)
written = folder / 'reports' / (project.name + '.html')
result['python_save'] = model(written.read_text())[0]
completed = subprocess.run(
    [sys.executable, '-m', 'edi', 'report', str(folder), *cli_choices],
    capture_output=True,
    text=True,
    check=False,
    timeout=15,
)
if completed.returncode:
    raise RuntimeError(completed.stdout + completed.stderr)
result['cli_save'] = model(written.read_text())[0]
print(json.dumps(result, ensure_ascii=False, allow_nan=False))
