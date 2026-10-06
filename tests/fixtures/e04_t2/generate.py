"""Freeze  loop expectations from STAR text; no edi import or GUI output."""

from __future__ import annotations

import hashlib
import json
import shlex
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def loops(path):
    lines = path.read_text().splitlines()
    result = []
    for start, source_line in enumerate(lines):
        if source_line.strip() != 'loop_':
            continue
        headers = []
        index = start + 1
        while index < len(lines) and lines[index].startswith('_'):
            headers.append(lines[index].strip())
            index += 1
        values = []
        while index < len(lines):
            line = lines[index].strip()
            if line.startswith(('_', 'loop_', 'data_')):
                break
            values.extend(shlex.split(line, comments=True))
            index += 1
        if not headers or len(values) % len(headers):
            raise ValueError(f'malformed fixture loop: {path}')
        categories = {field[1:].split('.')[0] for field in headers}
        if len(categories) != 1:
            raise ValueError(f'mixed fixture categories: {path}')
        result.append({
            'category': categories.pop(),
            'columns': [h.split('.')[1] for h in headers],
            'rows': len(values) // len(headers),
        })
    return result


def generate():
    projects = sorted((ROOT / 'docs/user/cli').glob('*/project/project.edi'))
    projects += sorted((ROOT / 'tests/fixtures/e04_t1').glob('*-project/project.edi'))
    cases = []
    categories = set()
    for project in projects:
        for path in sorted(project.parent.rglob('*.edi')):
            page = {
                'structures': 'structure',
                'experiments': 'experiment',
                'analysis': 'analysis',
            }.get(path.parent.name, 'project')
            for loop in loops(path):
                categories.add(loop['category'])
                cases.append({
                    'tag': f'{path.relative_to(ROOT)}/{loop["category"]}',
                    'project': str(project.parent.relative_to(ROOT)),
                    'page': page,
                    'block': path.stem,
                    'file': str(path.relative_to(ROOT)),
                    'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                    **loop,
                })
    output = {
        'provenance': '.edi loop_ declarations, no app category lists',
        'categories': sorted(categories),
        'loops': cases,
    }
    (Path(__file__).parent / 'loops.json').write_text(json.dumps(output, indent=2) + '\n')


def generate_profile_adaptation():
    """Freeze one replacement-model input identity; retain the original loop oracle."""
    relative = 'docs/user/cli/pd-neut-cwl_pbso4_beba-asymmetry/project/experiments/d1a.edi'
    frozen = json.loads((Path(__file__).parent / 'loops.json').read_text())
    original = {row['sha256'] for row in frozen['loops'] if row['file'] == relative}
    if len(original) != 1:
        raise ValueError('The original PbSO4 loop oracle must name one complete input digest')
    output = {
        'classification': 'Replacement-model input identity: regression pin, not numerical oracle',
        'authority': 'ADR-0080 retires the TCH + BeBa model',
        'file': relative,
        'before_sha256': original.pop(),
        'after_sha256': hashlib.sha256((ROOT / relative).read_bytes()).hexdigest(),
        'after_selector': 'cwl-pseudo-voigt-berar-baldinozzi',
    }
    (Path(__file__).parent / 'replacement-input.json').write_text(
        json.dumps(output, indent=2) + '\n'
    )


if __name__ == '__main__':
    generate()
