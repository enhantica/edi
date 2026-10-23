"""Recover retained full-project byte witnesses, requiring their original hashes.

The saved tree transports unrounded bytes plus IUCr tokens. Restore each numeric
lexeme from the pinned input, then require the entire old file's existing hash
before archiving it. No new engine-output hash is accepted as an expectation.
"""

import argparse
import hashlib
import json
import re
import zipfile
from decimal import Decimal
from pathlib import Path

from tests.fixtures.cwl_family.historical import original_tokens
from tests.fixtures.report_units.iucr_reference import rounded_record

ROOT = Path(__file__).resolve().parents[3]
CASE = 'repo:docs/user/cli/pd-neut-tof_ncaf-wish-5bank_start-fullprof/project'
CASES = [
    CASE,
    CASE.replace('start-fullprof', 'start-5'),
    'repo:docs/user/cli/pd-neut-cwl_cosio-d20_scan-324f/project',
]
NUMERIC = re.compile(rb'([-+]?(?:\d+(?:\.\d*)?|\.\d+))\((\d+(?:\.\d*)?)\)')


def original_token(match):
    value = Decimal(str(float(match[1])))
    uncertainty = Decimal(match[2].decode())
    if b'.' not in match[2]:
        uncertainty *= Decimal(1).scaleb(Decimal(match[1].decode()).as_tuple().exponent)
    if not uncertainty:
        return match[0]
    uncertainty = Decimal(str(float(uncertainty)))
    place = min(
        value.normalize().as_tuple().exponent, uncertainty.normalize().as_tuple().exponent, 0
    )
    quantum = Decimal(1).scaleb(place)
    return (
        format(value.quantize(quantum), 'f') + '(' + str(int(uncertainty / quantum)) + ')'
    ).encode()


def recover(saved_tree, case, selected=None, *, original_bytes=False):
    pins = json.loads((ROOT / 'tests/fixtures/constraint_expressions/byte-pins.json').read_text())
    expected = pins['cases'][case]['after_saved_sha256']
    if selected is not None and (
        selected not in expected or not selected.startswith(('structures/', 'experiments/'))
    ):
        raise ValueError('Recovery needs a structure or experiment with an existing saved hash')
    source = ROOT / case.removeprefix('repo:')
    result = {}
    for name, digest in expected.items():
        if not name.startswith(('structures/', 'experiments/')) or (
            selected is not None and name != selected
        ):
            continue
        if original_bytes:
            original = (saved_tree / name).read_bytes()
            if hashlib.sha256(original).hexdigest() != digest:
                raise ValueError('Original bytes differ from the immutable old hash: ' + name)
            result[name] = original
            continue
        inverse = {}
        for match in NUMERIC.finditer((source / name).read_bytes()):
            original = original_token(match)
            rounded = rounded_record(b'_peak.test ' + original).split()[-1]
            if rounded in inverse and inverse[rounded] != original:
                raise ValueError('Ambiguous original lexemes cannot recover a byte witness')
            inverse[rounded] = original
        saved = (saved_tree / name).read_bytes()
        if name.startswith('experiments/'):
            block = b'_calculator.type crysta\n\n'
            if saved.count(block) != 1 or len(re.findall(rb'(?m)^_calculator\.', saved)) != 1:
                raise ValueError('Recovery requires exactly one canonical calculator block')
            saved = saved.replace(block, b'', 1)
        saved = original_tokens(saved)
        original = NUMERIC.sub(
            lambda match, inverse=inverse: inverse.get(match[0], match[0]), saved
        )
        if hashlib.sha256(original).hexdigest() != digest:
            raise ValueError('Recovered bytes differ from the immutable old hash: ' + name)
        if rounded_record(original) != saved:
            raise ValueError('Saved bytes differ from the independent IUCr projection: ' + name)
        result[name] = original
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    trees = parser.add_mutually_exclusive_group(required=True)
    trees.add_argument('--saved-tree', type=Path)
    trees.add_argument('--original-tree', type=Path)
    parser.add_argument('--case', default=CASE, choices=CASES)
    parser.add_argument('--file', help='Recover one file with an existing immutable saved hash')
    args = parser.parse_args()
    originals = recover(
        args.original_tree or args.saved_tree,
        args.case,
        args.file,
        original_bytes=args.original_tree is not None,
    )
    destination = Path(__file__).with_name('iucr-fullprof-before.zip')
    prefix = args.case.rsplit('/', 2)[1] + '/'
    retained = {}
    if destination.exists():
        with zipfile.ZipFile(destination) as archive:
            retained = {
                name: archive.read(name)
                for name in archive.namelist()
                if '/' in name
                and not name.startswith(prefix)
                and any(name.startswith(case.rsplit('/', 2)[1] + '/') for case in CASES)
            }
    retained.update({prefix + name: contents for name, contents in originals.items()})
    with zipfile.ZipFile(destination, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, contents in sorted(retained.items()):
            info = zipfile.ZipInfo(name)
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, contents)
    if args.original_tree is not None:
        print('Archived original files matching immutable saved hashes')
    else:
        print('Recovered immutable saved hashes and checked independent IUCr spellings')


if __name__ == '__main__':
    main()
