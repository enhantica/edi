"""Labelled carried-result writer pins, not independent diffraction references.

Generate from saved-byte JUnit receipts. Original historical
and numeric-policy dictionaries remain immutable. The physical d conversion is
checked separately against diffraction-lib and the quadratic calibration.
"""

import argparse
import hashlib
import json
import xml.etree.ElementTree as ET  # noqa: S405 - locally produced scoped JUnit
from pathlib import Path

DOCUMENTS = {
    'cosio-d20-s1': 'pd-neut-cwl_cosio-d20_start-1',
    'cosio-d20-s4': 'pd-neut-cwl_cosio-d20_start-4',
    'cosio-d20-scan-3f': 'pd-neut-cwl_cosio-d20_scan-3f',
    'ncaf-wish-2bank-s3': 'pd-neut-tof_ncaf-wish-2bank_start-3',
    'si-sepd-s2': 'pd-neut-tof_si-sepd_start-2',
    'si-sepd-s5': 'pd-neut-tof_si-sepd_start-5',
}
CASES = {'corpus:' + name + '/project' for name in DOCUMENTS} | {
    'repo:docs/user/cli/' + name + '/project' for name in DOCUMENTS.values()
}

PATH = Path(__file__).with_name('carried-result-pins.json')


def carried_hashes(previous, case):
    if case not in CASES:
        return previous
    row = json.loads(PATH.read_text())['cases'].get(case) if PATH.exists() else None
    if row is None:
        return previous  # An uncaptured transition must still satisfy its original exact pin.
    if row['before'] != previous or set(row['after']) != set(previous):
        message = 'A carried-result pin must bind its complete prior saved inventory'
        raise ValueError(message)
    return row['after']


def computed_files(name):
    if 'ncaf-wish-2bank' in name:
        expected_changes = {
            'structures/ncaf.edi',
            'experiments/wish_4_7.edi',
            'experiments/wish_5_6.edi',
        }
    elif 'cosio-d20' in name:
        expected_changes = {'structures/cosio.edi', 'experiments/d20.edi'}
    else:
        expected_changes = {'structures/si.edi', 'experiments/sepd.edi'}
    return expected_changes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('receipt', type=Path)
    parser.add_argument('--extend', action='store_true')
    args = parser.parse_args()
    retained = json.loads(PATH.read_text())['cases'] if args.extend else {}
    rows = {}
    for case in ET.parse(args.receipt).iter('testcase'):  # noqa: S314 - scoped local JUnit
        properties = {
            p.attrib['name']: p.attrib['value'] for p in case.findall('./properties/property')
        }
        if 'carried_result_hashes' in properties and 'carried_computed_columns' not in properties:
            message = 'Computed-column checks must succeed before a writer transition is captured'
            raise ValueError(message)
        for prop in case.findall('./properties/property'):
            if prop.attrib['name'] != 'carried_result_hashes':
                continue
            value = json.loads(prop.attrib['value'])
            name = value.pop('case')
            if name not in CASES or set(value['before']) != set(value['after']):
                message = 'Carried-result capture requires each declared inventory exactly once'
                raise ValueError(message)
            changed = {
                key for key in value['before'] if value['before'][key] != value['after'][key]
            }
            expected_changes = computed_files(name)
            if changed != expected_changes:
                message = 'Only the declared computed structure and bank files may change'
                raise ValueError(message)
            if name in rows and rows[name] != value:
                message = 'Repeated provenance routes must yield the identical carried transition'
                raise ValueError(message)
            if name in retained and retained[name] != value:
                message = 'An existing carried-result transition must remain immutable'
                raise ValueError(message)
            if not all(
                len(digest) == 64 and all(c in '0123456789abcdef' for c in digest)
                for which in ('before', 'after')
                for digest in value[which].values()
            ):
                message = 'Every carried-result record must retain complete SHA-256 digests'
                raise ValueError(message)
            rows[name] = value
    captured = bool(rows)
    rows = {**retained, **rows}
    if not captured or rows.keys() != CASES:
        message = 'Every declared carried-result regression must be exercised before capture'
        raise ValueError(message)
    PATH.write_text(
        json.dumps(
            {
                'kind': 'carried-result representation regression pins, not numeric truth',
                'receipt_sha256': hashlib.sha256(args.receipt.read_bytes()).hexdigest(),
                'cases': rows,
            },
            indent=2,
            sort_keys=True,
        )
        + '\n'
    )
    print(PATH)


if __name__ == '__main__':
    main()
