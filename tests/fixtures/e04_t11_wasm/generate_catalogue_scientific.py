"""Capture complete native parity regression pins for the browser catalogue projects."""

import argparse
import hashlib
import json
import math
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

import edi

from tests.fixtures.e04_t11_wasm.generate_catalogue import CASES, ROOT, digest
from tests.fixtures.web_parallel import generate as operands
from tests.fixtures.web_parallel import numeric
from tests.fixtures.web_parallel.conditioning import generate as conditioning

HERE = Path(__file__).resolve().parent / 'catalogue_scientific'


def restore_native_precision(fixture, raw):
    bindings = []
    n = len(raw['labels'])
    for document, rows in fixture['scientific'].items():
        for ri, row in enumerate(rows):
            for ti, token in enumerate(row):
                operand = numeric._operand(token)
                if operand is None or operand[1] is None or operand[1] == 0:
                    continue
                candidates = []
                for column, value in enumerate(raw['values']):
                    sigma = math.sqrt(raw['covariance'][column * n + column])
                    native = (
                        format(Decimal(str(value)), 'f')
                        + '('
                        + format(Decimal(str(sigma)), 'f')
                        + ')'
                    )
                    rounded = numeric._iucr_operand(native)
                    if math.isclose(
                        operand[0], rounded[0], rel_tol=1e-9, abs_tol=1e-11
                    ) and math.isclose(operand[1], rounded[1], rel_tol=5e-9, abs_tol=5e-10):
                        candidates.append((column, native))
                if len(candidates) > 1 and '_background.id' in row:
                    tags = [part for part in row if part.startswith('_')]
                    identity = row[len(tags) + tags.index('_background.id')]
                    if not identity.isdecimal() or int(identity) < 1:
                        raise ValueError(
                            'Catalogue background points require positive integer ids'
                        )
                    suffix = f'background[{int(identity) - 1}]'
                    names = {suffix, Path(document).stem + '.' + suffix}
                    candidates = [
                        (column, native)
                        for column, native in candidates
                        if raw['labels'][column] in names
                    ]
                if len(candidates) != 1:
                    raise ValueError(
                        'A rounded operand must identify one native covariance column'
                    )
                column, native = candidates[0]
                row[ti] = native
                bindings.append([document, ri, ti, column, token, native])
    if not bindings:
        raise ValueError('Complete native captures require saved fitted uncertainty operands')
    fixture['native_precision_bindings'] = bindings
    return fixture


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--conditioning-executable', type=Path, required=True)
    parser.add_argument('--sdk-manifest', type=Path, required=True)
    args = parser.parse_args()
    HERE.mkdir(exist_ok=True)
    operands.HERE = HERE
    operands.CASES = {
        case: f'docs/user/cli/{identity}/project' for case, identity in CASES.items()
    }
    before = {case: digest(ROOT / relative) for case, relative in operands.CASES.items()}
    operands.generate(
        Path(sys.executable),
        f'Native CLI parity regression pin at {edi.__build_commit__}',
        edi=True,
    )
    conditioning.HERE = HERE
    for case, relative in operands.CASES.items():
        project = ROOT / relative
        if digest(project) != before[case]:
            raise RuntimeError('Complete parity captures must retain every committed input byte')
        native = HERE / f'{case}-native.json'
        record = json.loads(native.read_text())
        record['reference'] = (
            'Native CLI parity regression pin; not an external correctness oracle'
        )
        record['project_sha256'] = before[case]
        native.write_text(json.dumps(record, indent=2) + '\n')
        raw = HERE / f'{case}-conditioning-raw.json'
        with raw.open('w') as stream:
            subprocess.run(
                [str(args.conditioning_executable.resolve()), str(project)],
                stdout=stream,
                check=True,
                timeout=120,
            )
        record = restore_native_precision(record, json.loads(raw.read_text()))
        native.write_text(json.dumps(record, indent=2) + '\n')
        conditioning.generate(case, raw, args.conditioning_executable, args.sdk_manifest)
        receipt = json.loads((HERE / f'{case}-conditioning.json').read_text())
        if receipt['raw_capture_sha256'] != hashlib.sha256(raw.read_bytes()).hexdigest():
            raise RuntimeError('The conditioning receipt must bind its retained native matrix')


if __name__ == '__main__':
    main()
