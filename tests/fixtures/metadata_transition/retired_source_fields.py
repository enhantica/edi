"""Retain byte oracles through the exact committed removal of a retired source key."""

import functools
import hashlib
import json
import re
import subprocess
import zipfile
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.resolve().parents[2]
REVISION = 'ec587609746b50823c048463f353b1767cbfa5f9'


@functools.cache
def rows():
    return json.loads((HERE / 'retired-source-fields.json').read_text())['files']


def previous_bytes(name, data):
    row = rows().get(str(name))
    if row is None:
        return data
    digest = hashlib.sha256(data).hexdigest()
    if digest == row['before_sha256']:
        return data
    assert digest == row['after_sha256'], (
        'A live descriptive input must match its entire independently archived source, '
        'including every scientific byte'
    )
    with zipfile.ZipFile(HERE / 'retired-source-fields.zip') as archive:
        before = archive.read(row['before_sha256'])
    assert hashlib.sha256(before).hexdigest() == row['before_sha256'], (
        'Retired-field projection retains the complete independently committed prior source'
    )
    return before


def saved_absorption(data, source):
    """Recover only the retired fixed-zero scalar for an immutable saved-byte witness."""
    source = Path(source)
    original = source.read_bytes()
    if source.is_relative_to(ROOT):
        original = previous_bytes(source.relative_to(ROOT).as_posix(), original)
    pattern = rb'(?m)^_absorption\.abscor2[^\r\n]*\r?\n'
    retired = re.findall(pattern, original)
    if not retired:
        return data
    assert retired in ([b'_absorption.abscor2 0\n'], [b'_absorption.abscor2 0.0\n']), (
        'The retired absorption projection admits exactly one fixed-zero source scalar'
    )
    assert not re.search(rb'(?m)^_absorption\.abscor2(?:[ \t]|$)', data), (
        'The current saved document must omit the retired absorption scalar'
    )
    cylinder = rb'(?m)^_absorption\.type[ \t]+cylinder\r?$'
    assert len(re.findall(cylinder, original)) == len(re.findall(cylinder, data)) == 1, (
        'The retired scalar belongs only to the unchanged cylinder absorption type'
    )
    first = rb'(?m)^_absorption\.abscor1[^\r\n]*\r?\n'
    assert len(re.findall(first, data)) == 1, (
        'The saved cylinder must retain exactly one active absorption coefficient'
    )
    return re.sub(first, lambda match: match[0] + b'_absorption.abscor2 0\n', data)


def generate():
    names = subprocess.check_output(
        [
            'git',
            'diff-tree',
            '--no-commit-id',
            '--name-only',
            '-r',
            REVISION,
            '--',
            'docs/user/cli/**/*.edi',
        ],
        cwd=ROOT,
        text=True,
    ).splitlines()
    records, content = {}, {}
    for name in names:
        before, after = (
            subprocess.check_output(['git', 'show', revision + ':' + name], cwd=ROOT)
            for revision in (REVISION + '^', REVISION)
        )
        retired = [
            line
            for line in before.splitlines(True)
            if line.startswith((b'_absorption.abscor2 ', b'_minimizer.stop_rule '))
        ]
        if not retired:
            continue
        assert len(retired) == 1 and retired[0] in {
            b'_absorption.abscor2 0\n',
            b'_absorption.abscor2 0.0\n',
            b'_minimizer.stop_rule shift_su\n',
            b'_minimizer.stop_rule chi_square_change\n',
        }, 'Only the declared fixed zero coefficient or superseded stop-rule scalar may leave'
        replacement = (
            b'_minimizer.stop_rules "chi_square_change"\n'
            if retired[0] == b'_minimizer.stop_rule chi_square_change\n'
            else b''
        )
        assert before.replace(retired[0], replacement, 1) == after, (
            'The source transition changes exactly the declared scalar and no other byte'
        )
        assert (ROOT / name).read_bytes() == after, (
            'The source transition must bind the complete current committed source'
        )
        old, new = (hashlib.sha256(data).hexdigest() for data in (before, after))
        records[name] = {'before_sha256': old, 'after_sha256': new}
        content[old] = before
    with zipfile.ZipFile(HERE / 'retired-source-fields.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for digest, data in sorted(content.items()):
            info = zipfile.ZipInfo(digest, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data)
    (HERE / 'retired-source-fields.json').write_text(
        json.dumps(
            {
                'source_commit': REVISION,
                'claim': (
                    'Remove only the retired fixed zero coefficient or stop-rule scalar; '
                    'all other bytes exact'
                ),
                'files': records,
            },
            indent=2,
        )
        + '\n'
    )
    print('Archived exact retired-field source transitions:', len(records))


if __name__ == '__main__':
    generate()
