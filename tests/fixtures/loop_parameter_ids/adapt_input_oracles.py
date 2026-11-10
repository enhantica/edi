"""Record the owner's newest-name input changes without regenerating scientific oracles.

Original complete sources are retained in the committed digest-bound archive.
Only adding a declared row-ID column or changing archived fit-state key cells is
admitted. Every other byte, numerical cell, row order and expectation is retained.
"""

import argparse
import hashlib
import json
import re
import subprocess
import zipfile
from pathlib import Path

from tests.fixtures.cwl_family.historical import original_tokens
from tests.fixtures.loop_parameter_ids.historical_bytes import old_fit_state_bytes
from tests.fixtures.table_display.metadata_bytes import pre_catalogue_bytes

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


def digest(data):
    return hashlib.sha256(data).hexdigest()


def remove_added_ids(previous, current):
    categories = {
        category
        for category in (b'_background', b'_excluded_region')
        if category + b'.id\n' not in previous
    }
    lines = current.splitlines(keepends=True)
    output = []
    tags = []
    header = False
    remove = False
    for original_line in lines:
        line = original_line
        word = line.strip()
        if word == b'loop_':
            tags = []
            header = True
            remove = False
        elif header and word.startswith(b'_'):
            tags.append(word)
            if any(word == category + b'.id' for category in categories):
                assert len(tags) == 1, 'The added input ID column must precede its retained cells'
                remove = True
                continue
        elif header:
            if word.startswith((b'_', b'data_', b'loop_')):
                remove = False
                header = False
            elif word and not word.startswith(b'#'):
                if remove:
                    match = re.match(rb'(?:\S+)[ \t]+', line)
                    assert match, 'Each added ID must prefix a complete retained input row'
                    line = line[match.end() :]
        output.append(line)
    return b''.join(output)


def require_transition(name, before, after):
    source = ROOT / name
    projected = remove_added_ids(before, after)
    if name.endswith('/analysis/analysis.edi'):
        projected = old_fit_state_bytes(before, projected, source.parent.parent)
    assert projected == before, (
        'The newest-format input conversion retains every byte outside declared ID/key cells'
    )


def retained_source(row):
    name = row['before_sha256'] + '.edi'
    with zipfile.ZipFile(HERE / 'input-format-before.zip') as archive:
        data = archive.read(name)
    assert digest(data) == row['before_sha256'], (
        'The retained input oracle must match its original complete-source digest'
    )
    return data


def retain_original_sources():
    records = json.loads((HERE / 'input-format-transitions.json').read_text())['files']
    held = {}
    for row in records.values():
        result = subprocess.check_output(
            ['git', 'show', row['before_commit'] + ':' + row['file']], cwd=ROOT
        )
        assert digest(result) == row['before_sha256'], (
            'Archive authoring must retain the exact independently committed before source'
        )
        held[row['before_sha256'] + '.edi'] = result
    with zipfile.ZipFile(HERE / 'input-format-before.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(held.items()):
            member = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            member.compress_type = zipfile.ZIP_DEFLATED
            member.external_attr = 0o644 << 16
            archive.writestr(member, data)


def archived_source(name, expected):
    record_path = HERE / 'input-format-transitions.json'
    if record_path.exists() and (HERE / 'input-format-before.zip').exists():
        records = json.loads(record_path.read_text())['files']
        for row in records.values():
            if row['file'] == name and row['before_sha256'] == expected:
                return row['before_commit'], retained_source(row)
    commits = subprocess.check_output(
        ['git', 'log', '--format=%H', 'HEAD', '--', name], cwd=ROOT, text=True
    ).splitlines()
    for revision in commits:
        result = subprocess.run(
            ['git', 'show', revision + ':' + name], cwd=ROOT, capture_output=True, check=False
        )
        if result.returncode == 0 and digest(result.stdout) == expected:
            return revision, result.stdout
    raise ValueError('The immutable source digest is absent from committed history: ' + name)


def read_js(path):
    return json.loads(path.read_text().split('var frozen = ', 1)[1].removesuffix(';\n'))


def generate():
    oracle = read_js(ROOT / 'tests/fixtures/e04_t1/oracle.js')
    display = read_js(ROOT / 'tests/fixtures/e04_t1/display_oracle.js')
    loops = json.loads((ROOT / 'tests/fixtures/e04_t2/loops.json').read_text())
    record_path = HERE / 'input-format-transitions.json'
    records = json.loads(record_path.read_text())['files'] if record_path.exists() else {}

    def update(name, expected, *, projected=False):
        path = ROOT / name
        after = original_tokens(pre_catalogue_bytes(path)) if projected else path.read_bytes()
        if digest(after) == expected:
            return expected
        revision, before = archived_source(name, expected)
        require_transition(name, before, after)
        key = name + ('#pre-catalogue' if projected else '')
        records[key] = {
            'file': name,
            'before_commit': revision,
            'before_sha256': expected,
            'after_sha256': digest(after),
        }
        return digest(after)

    for case in oracle['corpus']:
        name = case['project'] + '/experiments/' + case['experiment'] + '.edi'
        case['sha256'] = update(name, case['sha256'])
    for case in oracle['projects']:
        for relative, expected in case['files'].items():
            case['files'][relative] = update(case['path'] + '/' + relative, expected)
    for name, expected in display['sources'].items():
        display['sources'][name] = update(name, expected)
    for case in loops['loops']:
        # The separately recorded replacement-model input keeps its original receipt.
        replacement = json.loads(
            (ROOT / 'tests/fixtures/e04_t2/replacement-input.json').read_text()
        )
        if case['file'] == replacement['file']:
            continue
        old_digest = case['sha256']
        case['sha256'] = update(case['file'], old_digest, projected=True)
        if (
            case['sha256'] != old_digest
            and case['category'] in {'background', 'excluded_region'}
            and 'id' not in case['columns']
        ):
            case['columns'].insert(0, 'id')
    for name, data in [('oracle.js', oracle), ('display_oracle.js', display)]:
        (ROOT / 'tests/fixtures/e04_t1' / name).write_text(
            '// Independent source oracle; newest-name changes use adapt_input_oracles.py.\n'
            'var frozen = '
            + json.dumps(data, indent=2, ensure_ascii=name == 'display_oracle.js')
            + ';\n'
        )
    (ROOT / 'tests/fixtures/e04_t2/loops.json').write_text(json.dumps(loops, indent=2) + '\n')
    (HERE / 'input-format-transitions.json').write_text(
        json.dumps(
            {
                'authority': 'hub 43e60c982 and 0f42ef2f9, newest names and declared loop IDs',
                'classification': 'Input identity record; scientific expectations are unchanged',
                'files': records,
            },
            indent=2,
        )
        + '\n'
    )


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--retain-original-sources', action='store_true')
    arguments = parser.parse_args()
    if arguments.retain_original_sources:
        retain_original_sources()
    else:
        generate()
