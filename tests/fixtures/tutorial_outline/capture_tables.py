"""Capture published display column sets; owner 60fd686d5 extends the free set to all()."""

import argparse
import ast
import hashlib
import json
import subprocess
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repository', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    revision = 'cb2cda7be6117199be8f8cac0a666a7bccd32d90'
    definitions = {}
    hashes = {}
    for kind, path in [
        ('fit', 'src/easydiffraction/analysis/fit_helpers/reporting.py'),
        ('free', 'src/easydiffraction/analysis/analysis.py'),
    ]:
        payload = subprocess.check_output([
            'git',
            '-C',
            str(args.repository),
            'show',
            revision + ':' + path,
        ])
        hashes[path] = hashlib.sha256(payload).hexdigest()
        candidates = []
        for node in ast.walk(ast.parse(payload)):
            if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.List):
                continue
            try:
                value = ast.literal_eval(node.value)
            except (ValueError, TypeError):
                continue
            if not all(isinstance(item, str) for item in value):
                continue
            required = {'datablock', 'category', 'entry', 'parameter', 'value', 'units'}
            if required <= set(value) and (
                ('start' in value and 'change' in value)
                if kind == 'fit'
                else ('min' in value and 'max' in value)
            ):
                candidates.append(value)
        assert candidates, 'The pinned primary table definition must be present'
        definitions[kind] = [
            '#',
            *['s.u.' if name == 'uncertainty' else name for name in candidates[0]],
        ]
    definitions.update(
        commit=revision,
        source_sha256=hashes,
        explanation_terms={
            'start': ['before', 'fit'],
            'value': ['fit', 'least'],
            's.u.': ['standard', 'uncertainty', 'covariance'],
            'change': ['relative', '%', '↑', '↓'],
        },
    )
    args.output.write_text(json.dumps(definitions, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    main()
