"""Report settings hand inputs and published FNV/A4 reference values; no engine imports."""

import json
import re
import shutil
from pathlib import Path


def generate():
    reference = {
        'legacy': [
            '_report.html false',
            '_report.pdf true',
            '_report.tex true',
            '_report.html_offline true',
            '_report.excluded "charts reflections"',
            '_report.correlation_threshold 0.9',
            '_report.x_axis d_spacing',
        ],
        'settings': [
            '_report.html true',
            '_report.pdf true',
            '_report.cif false',
            '_report.html_offline true',
            '_report.excluded "reflections data"',
        ],
        'rows': [
            [
                'html',
                'input.html',
                '2031-02-03T04:05:06Z',
                '2030-01-02T03:04:05Z',
                '0123456789abcdef',
            ],
            [
                'pdf',
                'input.pdf',
                '2031-02-03T04:05:07Z',
                '2030-01-02T03:04:05Z',
                'fedcba9876543210',
            ],
        ],
        'row_keys': ['format', 'name', 'saved', 'project_last_modified', 'digest'],
        'fnv': {'': 'cbf29ce484222325', 'a': 'af63dc4c8601ec8c'},
        'pdf': {
            'media_box': [0, 0, 595, 842],
            'margin_mm': 25,
            'column_mm': 160,
            'body_pt': 10.04,
        },
        'html_reference': {
            'shell_cm': 21.59,
            'source': 'owner-lbco_simulation.html .report-shell',
            'sha256': '291066c82d3361376e61604b0b7bd5c9ee68cdad7cf8d46677eb04c893768275',
        },
        'correlation_rgb': {'-1': '#d73027', '0': '#ffffff', '1': '#4575b4'},
        'provenance': (
            'Report settings and A4 page conventions; '
            'published FNV author test vectors; '
            'colours from the ColorBrewer reference.'
        ),
    }
    Path(__file__).with_name('reference.json').write_text(json.dumps(reference, indent=2) + '\n')
    # Independent PSD matrix: P1=P3=-P2, all remaining variables independent.
    # All three endpoint colours therefore occur below the blank diagonal.
    repo = Path(__file__).resolve().parents[3]
    base = repo / 'tests/fixtures/report_options/pairs'
    if base.exists():
        target = Path(__file__).with_name('signed')
        shutil.copytree(base, target, dirs_exist_ok=True)
        file = target / 'analysis/analysis.edi'
        lines = []
        for input_line in file.read_text().splitlines():
            line = input_line
            if re.match(r'\d+ deterministic bank\.background\.P\d+\.intensity ', line):
                values = line.split()
                left = values[2].split('.')[-2]
                right = values[3].split('.')[-2]
                pair = frozenset((left, right))
                values[-1] = {
                    frozenset(('P1', 'P2')): '-1',
                    frozenset(('P1', 'P3')): '1',
                    frozenset(('P2', 'P3')): '-1',
                }.get(pair, '0')
                line = ' '.join(values)
            lines.append(line)
        file.write_text('\n'.join(lines) + '\n_correlation_chart.threshold 0\n')


if __name__ == '__main__':
    generate()
