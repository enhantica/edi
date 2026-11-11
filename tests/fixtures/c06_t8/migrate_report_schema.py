"""Project captured reports into ADR-0057 schema nine without rerunning a fit.

Captured numeric values remain regression/reference data of their original era.
The capture did not observe stop metadata: ADR-0057/0124's unavailable values are
none/nan/nan. This format projection makes no claim about a current fit's stop.
"""

from __future__ import annotations

import ast
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
FIELDS = ('stopping_rule', 'stopping_value', 'last_shift_su')
UNAVAILABLE = ('none', 'nan', 'nan')


def project_record(text: str) -> str:
    if not text.startswith('schema=8\n'):
        message = 'The format migration requires an unchanged schema-eight capture'
        raise ValueError(message)
    lines = text.splitlines(keepends=True)
    lines[0] = 'schema=9\n'
    if lines[1] == 'record=fit\n':
        index = next(i for i, line in enumerate(lines) if line.startswith('rwp=')) + 1
        lines[index:index] = [
            key + '=' + value + '\n' for key, value in zip(FIELDS, UNAVAILABLE, strict=True)
        ]
    return ''.join(lines)


def main():  # noqa: PLR0914 - retain the explicit before/after custody for each artifact
    receipt = HERE / 'schema9-projection.json'
    previous = json.loads(receipt.read_text()) if receipt.exists() else {}
    revision = (
        previous.get('source_commit')
        or subprocess.check_output(
            ['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True
        ).strip()
    )

    def captured(path):
        return subprocess.check_output([
            'git',
            '-C',
            str(ROOT),
            'show',
            revision + ':' + path.relative_to(ROOT).as_posix(),
        ])

    paths = sorted((ROOT / 'tests/fixtures/e05_t1').glob('*.record'))
    paths += sorted((ROOT / 'tests/fixtures/e04_t11_wasm').rglob('*native-report.txt'))
    paths += sorted((ROOT / 'tests/fixtures/web_parallel').glob('*native-report.txt'))
    paths += [ROOT / 'tests/fixtures/c11_t35_descent_selector/default-record-no-elapsed.txt']
    records = {}
    for path in paths:
        old = captured(path)
        projected = project_record(old.decode()).encode()
        path.write_bytes(projected)
        records[path.relative_to(ROOT).as_posix()] = {
            'before_sha256': hashlib.sha256(old).hexdigest(),
            'after_sha256': hashlib.sha256(projected).hexdigest(),
        }
    manifest_path = ROOT / 'tests/fixtures/e05_t1/cli.json'
    header_path = manifest_path.with_suffix('.hpp')
    old_json, old_header = captured(manifest_path), captured(header_path)
    manifest = json.loads(old_json)
    for case in manifest['cases']:
        old = ''.join(key + '=' + value + '\n' for key, value in case['record'].items())
        case['record'] = dict(line.split('=', 1) for line in project_record(old).splitlines())
    # Reuse the existing standard-library artifact writer without importing edi or fitting.
    generator = ROOT / 'tests/fixtures/e05_t1/generate.py'
    tree = ast.parse(generator.read_text())
    writer = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == 'write_artifacts'
    )
    namespace = {'json': json, 'HERE': manifest_path.parent}
    # Execute only the repository-owned standard-library writer, never an engine import.
    exec(compile(ast.Module(body=[writer], type_ignores=[]), str(generator), 'exec'), namespace)  # noqa: S102
    namespace['write_artifacts'](manifest)
    for path, old in ((manifest_path, old_json), (header_path, old_header)):
        records[path.relative_to(ROOT).as_posix()] = {
            'before_sha256': hashlib.sha256(old).hexdigest(),
            'after_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    for name in ('stops.json', 'refusal.json'):
        path = manifest_path.with_name(name)
        old = captured(path)
        data = json.loads(old)
        if 'cases' in data:
            mappings = [case['record'] for case in data['cases']]
        else:
            mappings = [data['record']]
        for mapping in mappings:
            text = ''.join(key + '=' + value + '\n' for key, value in mapping.items())
            projected = dict(line.split('=', 1) for line in project_record(text).splitlines())
            mapping.clear()
            mapping.update(projected)
        path.write_text(json.dumps(data, indent=2) + '\n')
        records[path.relative_to(ROOT).as_posix()] = {
            'before_sha256': hashlib.sha256(old).hexdigest(),
            'after_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    receipt.write_text(
        json.dumps(
            {
                'source_commit': revision,
                'authority': '01fd45799',
                'contract': 'ADR-0057 schema 9; unavailable stop metadata per ADR-0124',
                'claim': (
                    'Format projection only; every captured pre-existing byte is recoverable; '
                    'no fit rerun'
                ),
                'records': records,
            },
            indent=2,
        )
        + '\n'
    )


if __name__ == '__main__':
    main()
