"""Retain the older format projection through a separately captured schema-nine case."""

import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).parent
CASE = 'sc-neut-cwl_tb2ti2o7-heidi_exclusions'
WARNING_FILE = 'tests/fixtures/e05_t1/cli.json'
WARNING_SOURCE = 'a6f0c1dd'
OLD_WARNING_NAME = 'structures[Al2O3].atom_sites[Al1].adp_iso'
SAVED_WARNING_NAME = 'Al2O3.atom_site.Al1.adp_iso'


def warning_spelling(before, after):
    old = f'Warning: {OLD_WARNING_NAME} = -0.13591'.encode()
    new = f'Warning: {SAVED_WARNING_NAME} = -0.13591'.encode()
    assert before.count(old) == 1 and before.replace(old, new, 1) == after, (
        'Only the named warning spelling may change between the committed documents'
    )
    return {
        'source_commit': WARNING_SOURCE,
        'file': WARNING_FILE,
        'before_sha256': hashlib.sha256(before).hexdigest(),
        'after_sha256': hashlib.sha256(after).hexdigest(),
    }


def main():
    files, payloads = {}, {}
    diagnostic = None
    for suffix in ('json', 'hpp'):
        name = f'tests/fixtures/e05_t1/cli.{suffix}'
        before, after = (
            subprocess.check_output(['git', 'show', ref + ':' + name], cwd=ROOT)
            for ref in ('2830f2cc^', '2830f2cc')
        )
        current = after
        if name == WARNING_FILE:
            current = subprocess.check_output(
                ['git', 'show', WARNING_SOURCE + ':' + name], cwd=ROOT
            )
            diagnostic = warning_spelling(after, current)
        assert (ROOT / name).read_bytes() == current, (
            'Later captures require their exact committed bytes'
        )
        if suffix == 'json':
            old, new = json.loads(before), json.loads(after)
            added = [row for row in new['cases'] if row['id'] == CASE]
            assert len(added) == 1, 'The schema-nine addition is one independently captured case'
            new['cases'] = [row for row in new['cases'] if row['id'] != CASE]
            assert new == old, 'The later capture preserves every original case and manifest field'
        files[name] = {
            'before_sha256': hashlib.sha256(before).hexdigest(),
            'after_sha256': hashlib.sha256(after).hexdigest(),
        }
        payloads[hashlib.sha256(before).hexdigest()] = before
    with zipfile.ZipFile(HERE / 'later-schema9.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for digest, data in sorted(payloads.items()):
            info = zipfile.ZipInfo(digest, (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data)
    record = f'tests/fixtures/e05_t1/{CASE}.record'
    (HERE / 'later-schema9.json').write_text(
        json.dumps(
            {
                'source_commit': '2830f2cc',
                'files': files,
                'warning_spelling': diagnostic,
                'native_records': {
                    record: hashlib.sha256((ROOT / record).read_bytes()).hexdigest()
                },
            },
            indent=2,
        )
        + '\n'
    )


if __name__ == '__main__':
    main()
