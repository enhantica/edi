"""Read the correlation model from the actual Python and CLI HTML writers."""

import json
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

import edi


class ModelReader(HTMLParser):
    def __init__(self):
        super().__init__()
        self.inside = False
        self.parts = []

    def handle_starttag(self, tag, attrs):
        self.inside = tag == 'script' and dict(attrs).get('id') == 'edi-report-model'

    def handle_endtag(self, tag):
        if tag == 'script':
            self.inside = False

    def handle_data(self, text):
        if self.inside:
            self.parts.append(text)


def surface_matrix(folder, surface):
    path = folder / (surface + '-template-proof.html')
    if surface == 'python':
        project = edi.Project.load(folder)
        project.report.save_html(path, offline=False, correlation_threshold=0.0)
    else:
        completed = subprocess.run(
            [
                sys.executable,
                '-m',
                'edi',
                'report',
                str(folder),
                '--output',
                str(path),
                '--online',
                '--correlation-threshold',
                '0',
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if completed.returncode:
            raise RuntimeError('Actual CLI report failed: ' + completed.stderr)
    reader = ModelReader()
    reader.feed(path.read_text(encoding='utf-8'))
    return json.loads(''.join(reader.parts)).get('correlations')


def main():
    folder = Path(sys.argv[1])
    result = {}
    for surface in ('python', 'cli'):
        try:
            result[surface] = surface_matrix(folder, surface)
        except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
            result[surface] = {'error': str(error)}
    print(json.dumps(result, allow_nan=False))


if __name__ == '__main__':
    main()
