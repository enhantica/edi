"""Independent  inventory: compiler members and source I/O tokens.

This never reads a schema or the production census output. It deliberately emits
references, not a guessed schema for data/category-census.json. The schema/census
adapter must compare these references once that public format is implemented.
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path


def without_comments(text):
    return re.sub(r'/\*.*?\*/|//[^\n]*', '', text, flags=re.DOTALL)


def declarations(text):
    # Resolve qualified declarations in this header; short names alias types in
    # included headers (for example Generation::Cell versus the model Cell).
    text = re.sub(r'"(?:\\.|[^"\\])*"', '""', without_comments(text))
    pattern = (
        r'namespace\s+(?P<namespace>\w+(?:::\w+)*)\s*\{'
        r'|(?:struct|class)\s+(?P<record>\w+)(?:\s+final)?\s*(?::[^;{}]*)?\{'
        r'|[{}]'
    )
    owners, scopes = set(), []
    for token in re.finditer(pattern, text):
        if token[0] == '}':
            scopes.pop()
            continue
        name = token['namespace'] or token['record'] or ''
        scopes.append(name)
        # A function or ordinary block has an unnamed scope. Its local types
        # are not namespace/record model declarations, even when they shadow one.
        if token['record'] and all(scopes):
            owners.add('::'.join(part for part in scopes if part))
    return owners


def members(dump, repo, owners):
    rows, scopes = set(), []
    for line in dump.splitlines():
        if line.startswith('Dumping '):
            scopes = []
            continue
        match = re.match(r'([| `-]*)(.*)', line)
        depth, entry = len(match[1]) // 2, match[2]
        while scopes and scopes[-1][0] >= depth:
            scopes.pop()
        namespace = re.match(r'NamespaceDecl .+\b([A-Za-z_]\w*)\s*$', entry)
        record = re.match(r'CXXRecordDecl .+\b(?:class|struct) (\w+) definition$', entry)
        if namespace:
            scopes.append((depth, namespace[1], False))
        elif entry.startswith((
            'FunctionDecl ',
            'CXXMethodDecl ',
            'CXXConstructorDecl ',
            'CXXDestructorDecl ',
            'CXXConversionDecl ',
            'CompoundStmt ',
        )):
            scopes.append((depth, '', False))
        elif record:
            scopes.append((depth, record[1], True))
        elif entry.startswith('FieldDecl ') and scopes:
            owner = scopes[-1]
            if not owner[2] or owner[0] != depth - 1 or any(not scope[1] for scope in scopes):
                continue
            field = compiler_field(entry, scopes, repo)
            if field and field[0] in owners:
                rows.add(field)
    return [dict(zip(('owner', 'member', 'type'), row, strict=True)) for row in sorted(rows)]


def compiler_field(entry, scopes, repo):
    types = re.findall(r"'([^']+)'", entry)
    if not types:
        raise ValueError('untyped compiler field: ' + entry)
    name = entry.split("'", 1)[0].split()[-1]
    qualified = '::'.join(part[1] for part in scopes)
    return (qualified, name, types[0]) if qualified.startswith(repo + '::') else None


def identity_reference(root, repo, identity_root=None):
    # Before: an undeclared sibling. After: fetched SDK source, or a caller's
    # independently prescribed synthetic reference tree; never census output.
    identity_root = identity_root or (root if repo == 'crysta' else root / 'build/crysta-src')
    identity_source = identity_root / 'src/core/identity.cpp'
    identity = without_comments(identity_source.read_text()).split('identity_columns() {', 1)[1]
    identity = identity.split('return columns;', 1)[0]
    identities = re.findall(r'\{\s*"(_[^"]+)"\s*,\s*"([^"]+)"\s*\}', identity)
    if not identities:
        message = 'identity_columns reference produced no declared identity tags'
        raise ValueError(message)
    return identities, hashlib.sha256(identity_source.read_bytes()).hexdigest()


def inventory(
    root, repo, compiler, *, extra_headers=(), io_paths=None, identity_root=None, sdk_include=None
):
    header = root / ('include' if repo == 'crysta' else 'core/include') / repo / 'model.hpp'
    headers = [header, *(root / name for name in extra_headers)]
    with tempfile.TemporaryDirectory(prefix='c34-reference-') as directory:
        vehicle = Path(directory) / 'members.cpp'
        vehicle.write_text('#include "' + repo + '/model.hpp"\n')
        command = [
            compiler,
            '-std=c++20',
            '-fsyntax-only',
            '-Xclang',
            '-ast-dump',
            '-Xclang',
            '-ast-dump-filter=' + repo,
        ]
        includes = [
            header.parents[1],
            root / '.pixi/envs/cpp-ci/include',
            root / '.pixi/envs/default/include',
            root / 'build/crysta-prefix/include',
        ]
        if sdk_include is not None:
            includes.insert(0, sdk_include)
        if os.environ.get('CRYSTA_SDK_DIR'):
            includes.insert(1, Path(os.environ['CRYSTA_SDK_DIR']) / 'include')
        for path in includes:
            command += ['-I', str(path)]
        result = subprocess.run(
            [*command, str(vehicle)], capture_output=True, text=True, check=False, timeout=25
        )
    if result.returncode:
        raise RuntimeError('independent compiler reference refused: ' + result.stderr)
    field_rows = members(
        result.stdout, repo, set().union(*(declarations(path.read_text()) for path in headers))
    )
    if not field_rows:
        raise RuntimeError('compiler produced no fields from ' + str(header))
    io_paths = io_paths or (
        ['src/core/save_project.cpp', 'src/core/model.cpp']
        if repo == 'crysta'
        else ['core/src/io.cpp']
    )
    identities, identity_digest = identity_reference(root, repo, identity_root)
    inputs = [*(path.relative_to(root).as_posix() for path in headers), *io_paths]
    return {
        'repo': repo,
        'members': field_rows,
        'identity_columns': [{'tag': tag, 'category': category} for tag, category in identities],
        'identity_source_sha256': identity_digest,
        **io_references(root, io_paths),
        'input_sha256': {
            name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in inputs
        },
        'compiler': compiler,
        'limits': 'I/O inventory covers literal dotted tags and category stems ending in a dot, '
        'and literal underscore tags in core sources (apart from the three data-range suffixes); '
        'not category names assembled without a literal dotted stem; '
        'model members include private fields, not inherited duplicates. '
        'No schema output or correctness claim is used as a reference.',
    }


def io_references(root, io_paths):
    tags, cif_tags = {}, {}
    for relative in io_paths:
        path = root / relative
        text = without_comments(path.read_text())
        for tag in re.findall(r'"(_[A-Za-z][A-Za-z_0-9]*\.[A-Za-z_0-9]*)"', text):
            tags.setdefault(tag, []).append(relative)
        if relative.startswith(('core/src/', 'src/core/')):
            for tag in re.findall(r'"(_[A-Za-z][A-Za-z0-9_-]*)"', text):
                if tag not in {'_min', '_max', '_step'}:
                    cif_tags.setdefault(tag, []).append(relative)
    if not tags:
        raise ValueError('independent I/O reference produced no tags')
    return {
        'io_tags': {tag: sorted(set(paths)) for tag, paths in sorted(tags.items())},
        'cif_tags': {tag: sorted(set(paths)) for tag, paths in sorted(cif_tags.items())},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--repo', choices=('crysta', 'edi'), required=True)
    parser.add_argument('--compiler', default=shutil.which('clang++'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not args.compiler:
        parser.error('Clang is required for the independent member reference')
    record = inventory(args.source_root.resolve(), args.repo, args.compiler)
    args.output.write_text(json.dumps(record, indent=2, sort_keys=True) + '\n')


if __name__ == '__main__':
    main()
