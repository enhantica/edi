"""Freeze  oracles using independent FullProf 8.40, authoring only.

Source: edi's vendored fitting tree. PCR edits enable Ppl=2 and clear all
codewords. Scientific parameter values are retained at the source PCR values.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

CASES = (
    ('cecoal', 'pd-neut-tof_cecoal-polaris_chebyshev', 'cecoal', 'chebyshev'),
    ('pearl', 'pd-neut-tof_ceo2-pearl_polynomial', 'Ceo2_PEARL', 'polynomial'),
    ('lab6', 'pd-neut-cwl_lab6-11b-echidna_tch-fcj', 'ECH0030684_LaB6_1p622A', 'polynomial'),
)
OUTPUT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def index(lines, marker):
    return next(i for i, line in enumerate(lines) if marker in line)


def clear_row(lines, row):
    lines[row] = ' '.join('0.00' for _ in lines[row].split())


def fixed_pcr(text, key, count):
    lines = text.splitlines()
    row = index(lines, '!Ipr Ppl') + 1
    words = lines[row].split()
    words[1] = '2'
    lines[row] = ' '.join(words)
    row = index(lines, '!Number of')
    lines[row] = '      0    !' + lines[row].split('!', 1)[1]
    bg = index(lines, '!   Background coefficients/codes')
    for offset in range(count // 6):
        clear_row(lines, bg + 2 + 2 * offset)
    row = index(lines, '!    Zero' if key != 'lab6' else '!  Zero') + 1
    words = lines[row].split()
    for column in (1, 3, 5, 7):
        words[column] = '0.00'
    lines[row] = ' '.join(words)
    nat = int(lines[index(lines, '!Nat ') + 1].split()[0])
    atom = index(lines, '!Atom ')
    for offset in range(nat):
        clear_row(lines, atom + 2 + 2 * offset)
    for row, line in enumerate(tuple(lines)):
        if re.match(r'!\s+(Scale|Sigma-2|Gamma-2|U\s|a\s|Pref1)', line):
            clear_row(lines, row + 2)
        if line.startswith('!Absorption correction parameters'):
            words = lines[row + 1].split()
            words[1] = words[3] = '0.00'
            lines[row + 1] = ' '.join(words)
    return '\n'.join(lines) + '\n'


def scientific_inputs(text, key, count):
    lines = text.splitlines()
    bg = index(lines, '!   Background coefficients/codes')
    coefficients = [
        float(word) for offset in range(count // 6) for word in lines[bg + 1 + 2 * offset].split()
    ]
    origin = index(lines, '!  Bkpos' if key != 'lab6' else '! Lambda1')
    zero = index(lines, '!    Zero' if key != 'lab6' else '!  Zero')
    return {
        'coefficients': coefficients,
        'origin': float(lines[origin + 1].split()[0 if key != 'lab6' else 3]),
        'zero': float(lines[zero + 1].split()[0]),
    }


def summary_coefficients(source, stem, count):
    lines = (source / (stem + '.sum')).read_text().splitlines()
    start = next(
        i
        for i, line in enumerate(lines)
        if 'Background Parameters' in line or 'Background Polynomial Parameters' in line
    )
    pairs = [list(map(float, line.split())) for line in lines[start + 1 : start + 1 + count]]
    return {
        'sum_coefficients': [row[0] for row in pairs],
        'sum_uncertainties': [row[1] for row in pairs],
    }


def generate_case(args, key, folder, stem, kind):
    source = args.source / folder
    work = args.work / key
    work.mkdir(parents=True, exist_ok=True)
    text = (source / (stem + '.pcr')).read_text()
    count = 24 if kind == 'chebyshev' else 6
    (work / 'oracle.pcr').write_text(fixed_pcr(text, key, count))
    shutil.copyfile(source / (stem + '.dat'), work / 'oracle.dat')
    with (work / 'fp2k.log').open('w') as log:
        result = subprocess.run(
            [str(args.fp2k)],
            input='oracle\n\n\n\n',
            text=True,
            stdout=log,
            stderr=subprocess.STDOUT,
            cwd=work,
            timeout=30,
            check=False,
        )
    if 'Normal end, final calculations' not in (work / 'fp2k.log').read_text():
        message = f'FullProf {key} failed: see {work / "fp2k.log"}'
        raise RuntimeError(message)
    for suffix in ('.bac', '.pcr'):
        shutil.copyfile(work / ('oracle' + suffix), OUTPUT / (key + suffix))
    for suffix in ('.sum', '.dat'):
        shutil.copyfile(source / (stem + suffix), OUTPUT / (key + suffix))
    row = {
        'project': folder,
        'type': kind,
        **scientific_inputs(text, key, count),
        **summary_coefficients(source, stem, count),
    }
    row['source_sha256'] = {
        stem + suffix: sha(source / (stem + suffix)) for suffix in ('.pcr', '.dat', '.sum')
    }
    row['sha256'] = {
        key + suffix: sha(OUTPUT / (key + suffix)) for suffix in ('.bac', '.pcr', '.sum', '.dat')
    }
    row['command'] = f"printf 'oracle\\n\\n\\n\\n' | {args.fp2k.name}"
    row['edits'] = (
        'Ppl=2; all codewords and parameter count=0; DAT alias oracle.dat; '
        'scientific parameters unchanged'
    )
    row['exit_code'] = result.returncode
    bac = (OUTPUT / (key + '.bac')).read_text().splitlines()
    row['bac_header'] = bac[0].split()
    points = [list(map(float, line.split())) for line in bac if not line.startswith('!')]
    row['x_min'], row['x_max'] = points[0][0] + row['zero'], points[-1][0] + row['zero']
    row['bac_tolerance'] = {'cecoal': 0.03, 'pearl': 0.004, 'lab6': 0.001}[key]
    print(f'{key}: independent .bac saved', flush=True)
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--fp2k', type=Path, required=True)
    args = parser.parse_args()
    cases = {
        key: generate_case(args, key, folder, stem, kind) for key, folder, stem, kind in CASES
    }
    manifest = {'schema': 1, 'engine': 'FullProf.2k 8.40 (Feb2026-ILL)', 'cases': cases}
    (OUTPUT / 'reference.json').write_text(json.dumps(manifest, indent=2) + '\n')


if __name__ == '__main__':
    main()
