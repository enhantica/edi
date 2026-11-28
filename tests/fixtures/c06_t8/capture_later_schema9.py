"""Retain the older format projection through a separately captured schema-nine case."""

import argparse
import hashlib
import json
import re
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


def remove_appended_cases(name, data, case_ids):
    if name.endswith('.json'):
        # The CLI writer appends case objects at the end of the cases array.
        # Reverse only those bytes so the old whole-document hash still proves custody.
        ids = [json.dumps(case_id).encode() for case_id in case_ids]
        marker = b',\n    {\n      "id": ' + ids[0] + b',\n'
        start = data.index(marker)
        end = data.index(b'\n  ]', start)
        found = re.findall(rb'^    \{\n      "id": ("[^"\n]+"),\n', data[start:end], re.MULTILINE)
        if found != ids:
            raise ValueError('Appended cases must occur in order at the end of the cases array')
        return data[:start] + data[end:]
    prefixes = tuple(('{' + json.dumps(case_id) + ',').encode() for case_id in case_ids)
    previous = data.splitlines(keepends=True)
    lines = [line for line in previous if not line.startswith(prefixes)]
    if len(previous) - len(lines) != len(case_ids):
        raise ValueError('Each appended case must own exactly one removed row')
    return b''.join(lines)


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


def append_cases(case_ids):
    path = HERE / 'later-schema9.json'
    receipt = json.loads(path.read_text())
    appended = receipt.get('appended_cases', {'ids': [], 'sha256': {}})
    prior_case_ids = appended['ids']
    if len(case_ids) != len(set(case_ids)) or set(case_ids) & set(prior_case_ids):
        raise ValueError('Later capture requires distinct new cases')
    all_case_ids = [*prior_case_ids, *case_ids]
    current_hashes = {}
    for name, entry in receipt['files'].items():
        data = (ROOT / name).read_bytes()
        retained = remove_appended_cases(name, data, case_ids)
        warning = receipt['warning_spelling']
        prior = warning if name == warning['file'] else entry
        expected = appended['sha256'].get(name, prior['after_sha256'])
        if hashlib.sha256(retained).hexdigest() != expected:
            raise ValueError('Later capture must retain every previous fixture byte')
        current_hashes[name] = hashlib.sha256(data).hexdigest()
    for case_id in case_ids:
        record = f'tests/fixtures/e05_t1/{case_id}.record'
        if record in receipt['native_records']:
            raise ValueError('Later capture cannot replace a previous native record')
        data = (ROOT / record).read_bytes()
        receipt['native_records'][record] = hashlib.sha256(data).hexdigest()
    receipt['appended_cases'] = {'ids': all_case_ids, 'sha256': current_hashes}
    path.write_text(json.dumps(receipt, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--append', nargs='+', metavar='CASE')
    args = parser.parse_args()
    if args.append:
        append_cases(args.append)
        return
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
