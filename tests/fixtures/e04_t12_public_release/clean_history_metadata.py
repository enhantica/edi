"""Adapt descriptive archive metadata without recomputing historical references.

Run once with the pinned Python and --report PATH. Original and adapted hashes
retain the provenance of each changed member. Model records, Python executable
ASTs, C++ executable tokens, member names and regression assertions are checked
before any output is written. The original reference manifest must match first.
"""

import argparse
import ast
import hashlib
import io
import json
import re
import zipfile
from pathlib import Path

from adapt_test_metadata import payload

ROOT = Path(__file__).resolve().parents[3]
HISTORY = Path(__file__).resolve().parent / 'history'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def executable(tree):
    for node in ast.walk(tree):
        body = getattr(node, 'body', None)
        if isinstance(body, list) and body and isinstance(body[0], ast.Expr):
            value = body[0].value
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                del body[0]
    return ast.dump(tree, include_attributes=False)


def adapt(raw, name):
    try:
        before = raw.decode('utf-8')
    except UnicodeError:
        return raw
    after = payload(before, name)
    if before == after:
        return raw
    if name.endswith(('.edi', '.cif')):

        def records(text):
            return [
                line
                for line in text.splitlines()
                if not line.lstrip().startswith(('#', '_metadata.'))
            ]

        if records(before) != records(after):
            raise RuntimeError('metadata adaptation changed scientific records: ' + name)
    elif name.endswith('.py'):
        if executable(ast.parse(before)) != executable(ast.parse(after)):
            raise RuntimeError('metadata adaptation changed executable Python: ' + name)
    elif name.endswith(('.hpp', '.cpp', '.h')):
        # Strings in historical diagnostics may lose citations; identifiers,
        # numbers, operators and assertion structure must stay byte-identical.
        tokens = re.compile(r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"', re.DOTALL)
        if tokens.sub('', before) != tokens.sub('', after):
            raise RuntimeError('metadata adaptation changed executable native tokens: ' + name)
    elif not name.endswith(('.md', '.json', '.txt')):
        raise RuntimeError('unapproved scientific reference edit: ' + name)
    return after.encode('utf-8')


def rewrite(path, pins, changes):
    before = path.read_bytes()
    output = io.BytesIO()
    updated = {}
    with zipfile.ZipFile(io.BytesIO(before)) as source, zipfile.ZipFile(output, 'w') as target:
        target.comment = source.comment
        for info in source.infolist():
            raw = source.read(info)
            if pins is not None and pins.get(info.filename) != digest(raw):
                raise RuntimeError('historical reference pin mismatch: ' + info.filename)
            after = adapt(raw, info.filename)
            updated[info.filename] = digest(after)
            if after != raw:
                changes.append({
                    'path': path.relative_to(ROOT).as_posix() + '!' + info.filename,
                    'before': digest(raw),
                    'after': digest(after),
                })
            target.writestr(info, after)
    after = output.getvalue()
    # Recompression alone is not a descriptive edit.
    if any(row['path'].startswith(path.relative_to(ROOT).as_posix() + '!') for row in changes):
        changes.append({
            'path': path.relative_to(ROOT).as_posix(),
            'before': digest(before),
            'after': digest(after),
        })
        return after, updated
    return before, updated


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    if args.report.exists():
        raise RuntimeError('metadata adaptation receipt must be write-once')
    manifest_path = HISTORY / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    original_closures = {key: manifest[key] for key in ('closure', 'absorption_closure')}
    changes, outputs = [], {}
    for key in ('api', 'native', 'input', 'pages'):
        path = HISTORY / (key + '.zip')
        outputs[path], manifest[key] = rewrite(path, manifest[key], changes)
    compatibility = ROOT / 'tests/fixtures/c13_t12_ids'
    report = json.loads((compatibility / 'baseline.json').read_text())
    outputs[compatibility / 'baseline.zip'], members = rewrite(
        compatibility / 'baseline.zip', None, changes
    )
    # Only saved-file retention hashes follow metadata; population, outcomes,
    # artifact identity and all original candidate records remain untouched.
    with zipfile.ZipFile(compatibility / 'baseline.zip') as source:
        for row in report['accepted']:
            for name, old in row.get('files', {}).items():
                member = row['archive'] + '/saved/' + name
                if digest(source.read(member)) != old:
                    raise RuntimeError('saved reference pin mismatch: ' + member)
                row['files'][name] = members[member]
    if any(manifest[key] != value for key, value in original_closures.items()):
        raise RuntimeError('production closure provenance cannot move')
    outputs[manifest_path] = (json.dumps(manifest, indent=2, sort_keys=True) + '\n').encode()
    outputs[compatibility / 'baseline.json'] = (json.dumps(report, indent=2) + '\n').encode()
    for path, after in outputs.items():
        before = path.read_bytes()
        if before != after:
            if path.suffix != '.zip':
                changes.append({
                    'path': path.relative_to(ROOT).as_posix(),
                    'before': digest(before),
                    'after': digest(after),
                })
            path.write_bytes(after)
    args.report.write_text(
        json.dumps(
            {'kind': 'descriptive archive metadata adaptation', 'changes': changes}, indent=2
        )
        + '\n'
    )
    print(
        f'{len(changes)} changed member/archive/manifest digests; science and assertions retained'
    )


if __name__ == '__main__':
    main()
