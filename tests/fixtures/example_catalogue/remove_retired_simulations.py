"""Drop retired case identities without refreshing surviving regression pins."""

import gzip
import io
import json
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RETIRED = ('pd-neut-tof_si_simulation', 'pd-xray-cwl_nacl_simulation')
IDENTITY_FIELDS = {'id', 'case', 'project', 'path', 'tag'}
PATTERN = re.compile(r'(?<![\w-])(?:' + '|'.join(map(re.escape, RETIRED)) + r')(?![\w-])')
DROP = object()


def retired(value):
    return isinstance(value, str) and PATTERN.search(value) is not None


def prune(value):
    if isinstance(value, dict):
        if any(retired(value.get(key)) for key in IDENTITY_FIELDS):
            return DROP
        result = {}
        for key, item in value.items():
            if retired(key):
                continue
            kept = prune(item)
            if kept is not DROP:
                result[key] = kept
        return result
    if isinstance(value, list):
        return [kept for item in value if (kept := prune(item)) is not DROP]
    return DROP if retired(value) else value


def prune_zip(path):
    with zipfile.ZipFile(path) as archive:
        entries = [(info, archive.read(info)) for info in archive.infolist()]
    kept = [
        (info, data)
        for info, data in entries
        if not retired(info.filename) and not retired(data.decode('utf-8', errors='replace'))
    ]
    if len(kept) != len(entries):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as archive:
            for info, data in kept:
                archive.writestr(info, data)
        path.write_bytes(buffer.getvalue())
        print(path.relative_to(ROOT))


def prune_gzip(path):
    original = gzip.decompress(path.read_bytes()).decode('utf-8')
    if not PATTERN.search(original):
        return
    document = json.loads(original)
    updated = prune(document)
    if updated is DROP:
        raise ValueError('A compressed fixture root must survive the case removal')
    path.write_bytes(gzip.compress(json.dumps(updated, separators=(',', ':')).encode(), mtime=0))
    print(path.relative_to(ROOT))


def main():
    fixtures = ROOT / 'tests/fixtures'
    for path in sorted(fixtures.rglob('*')):
        if path.suffix == '.zip':
            prune_zip(path)
            continue
        if path.suffix == '.gz':
            prune_gzip(path)
            continue
        if path.suffix not in {'.json', '.js'}:
            continue
        original = path.read_text()
        if not PATTERN.search(original):
            continue
        start = original.find('{')
        end = original.rfind('}') + 1
        document = json.loads(original[start:end])
        updated = prune(document)
        if updated is DROP:
            raise ValueError('A fixture root must survive the scoped case removal')
        if updated == document:
            continue
        rendered = json.dumps(updated, indent=2)
        path.write_text(original[:start] + rendered + original[end:])
        print(path.relative_to(ROOT))
    selection_path = fixtures / 'example_catalogue/catalogue-selection.json'
    selection = json.loads(selection_path.read_text())
    if 'fullprof_cases' not in selection:
        selection['fullprof_cases'] = [
            row['id'].replace('pd-neut-cwl_cosio-d20_scan-213f', 'pd-neut-cwl_cosio-d20_scan')
            for row in selection['cases']
            if row['id'] != 'pd-neut-cwl_cosio-d20_2k'
        ]
    for row in selection['cases']:
        if row['id'] == 'pd-neut-cwl_cosio-d20_scan':
            row['id'] = 'pd-neut-cwl_cosio-d20_scan-213f'
    if not any(row['id'] == 'pd-neut-cwl_cosio-d20_2k' for row in selection['cases']):
        index = next(
            i for i, row in enumerate(selection['cases']) if row['id'] == 'pd-neut-cwl_cosio-d20'
        )
        selection['cases'].insert(
            index + 1,
            {
                'id': 'pd-neut-cwl_cosio-d20_2k',
                'group': 'Constant-wavelength neutron',
            },
        )
    suffix = '; magnetic case identities and simulation removals adapted on 2026-11-08'
    if not selection['source'].endswith(suffix):
        selection['source'] += suffix
    selection_path.write_text(json.dumps(selection, indent=2) + '\n')
    path = fixtures / 'e04_t1/oracle.js'
    original = path.read_text()
    start, end = original.find('{'), original.rfind('}') + 1
    category = json.loads(original[start:end])
    ids = [row['id'] for row in selection['cases']]
    category['catalogue_ids'] = ids
    category['app_ids'] = ids + category['app_only_ids']
    path.write_text(original[:start] + json.dumps(category, indent=2) + original[end:])
    path = fixtures / 'metadata_migration.tsv'
    before = path.read_text()
    path.write_text(
        ''.join(line for line in before.splitlines(keepends=True) if not retired(line))
    )


if __name__ == '__main__':
    main()
