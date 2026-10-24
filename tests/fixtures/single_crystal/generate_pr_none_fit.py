"""Fit the owner's fixed-occupancy, extinction-free Pr example with FullProf."""

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

from generate_example_fits import extract, extract_isotropic

HERE = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():  # noqa: PLR0912, PLR0914, PLR0915 - the external control-file table
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fp2k', type=Path, required=True)
    parser.add_argument('--run-dir', type=Path, required=True)
    args = parser.parse_args()
    original = HERE / 'example_fits/pr2nio4/input.pcr'
    lines = original.read_text().splitlines()
    masks = {
        'Pr': ([False, False, True, False, False], [True, True, True, False, False, False]),
        'Ni': ([False] * 5, [True, True, True, False, False, False]),
        'O1': ([False] * 5, [True, True, True, True, False, False]),
        'O2': ([False, False, True, False, False], [True, True, True, False, False, False]),
        'Oi': ([False] * 5, [True, True, True, False, False, False]),
        'Od': ([True, True, True, True, False], None),
    }
    starts = {
        'Pr': (0.5, 0.5, 0.3620, 0, 2),
        'Ni': (0, 0, 0, 0, 1),
        'O1': (0.25, 0.25, 0, 0, 2),
        'O2': (0, 0, 0.1760, 0, 1.44593),
        'Oi': (0.25, 0.25, 0.25, 0, 0.14931),
        'Od': (0.075, 0.075, 0.175, 0, 0.597232),
    }
    number = 0

    def codes(mask):
        nonlocal number
        result = []
        for active in mask:
            number += int(active)
            result.append(str(number * 10 + 1) if active else '0')
        return ' '.join(result)

    for i, line in enumerate(tuple(lines)):
        fields = line.split()
        if fields and fields[0] in masks and len(fields) >= 11:
            atom = fields[0]
            fields[2:7] = [str(v) for v in starts[atom]]
            lines[i] = ' '.join(fields)
            main_mask, tensor = masks[atom]
            lines[i + 1] = codes(main_mask)
            if tensor is not None:
                lines[i + 2] = '0 0 0 0 0 0'
                lines[i + 3] = codes(tensor)
        if line.startswith('!Ipr'):
            flags = lines[i + 1].split()
            flags[3:5] = ['1', '2']
            lines[i + 1] = ' '.join(flags)
        if line.startswith('!NCY'):
            flags = lines[i + 1].split()
            flags[:2] = ['100', '0.000001']
            lines[i + 1] = ' '.join(flags)
        if line.startswith('!   Sc1'):
            flags = lines[i + 1].split()
            flags[0] = '0.0625'
            lines[i + 1] = ' '.join(flags)
            lines[i + 2] = codes([True, False, False, False, False, False])
        if line.startswith('! Ext1'):
            lines[i + 1] = '0 0 0 0 0 0 0 1'
            lines[i + 2] = '0 0 0 0 0 0 0'
    if number != 23:
        raise ValueError(
            'The matching Pr example must have twenty-three independent fitted parameters'
        )
    for i, line in enumerate(lines):
        if 'Number of' in line and 'parameters' in line:
            lines[i] = '23 ' + line[line.index('!') :]
    work = args.run_dir.resolve()
    work.mkdir(parents=True, exist_ok=True)
    (work / 'prnio.pcr').write_text('\n'.join(lines) + '\n')
    shutil.copy2(HERE / 'example_fits/pr2nio4/prnio.int', work / 'prnio.int')
    completed = subprocess.run(
        [str(args.fp2k.resolve())],
        input='prnio\n\n\n\n\n\n',
        text=True,
        cwd=work,
        capture_output=True,
        timeout=90,
        check=False,
    )
    (work / 'fp2k.log').write_text(completed.stdout + completed.stderr)
    if completed.returncode and 'Normal end' not in completed.stdout:
        raise RuntimeError('FullProf did not complete the matching Pr fit')
    destination = HERE / 'example_fits/pr2nio4_none'
    destination.mkdir(exist_ok=True)
    artifacts = {}
    for name in ('prnio.pcr', 'prnio.int', 'prnio.new', 'prnio.out', 'prnio.sum', 'prnio.prf'):
        source = work / name
        if not source.is_file():
            raise ValueError('FullProf did not write ' + name)
        shutil.copy2(source, destination / name)
        artifacts[name] = digest(source)
    record = json.loads((HERE / 'example-fits.json').read_text())
    record['cases']['pr2nio4_none'] = {
        'scale_factor': 64,
        'parameters': extract((work / 'prnio.sum').read_text(), 64)
        + [
            p
            for p in extract_isotropic((work / 'prnio.sum').read_text(), 64)
            if p['kind'] == 'Biso'
        ],
        'artifacts': artifacts,
        'binary_sha256': digest(args.fp2k),
        'source': 'FullProf 8.40; fixed occupancies, independent Od coordinates, extinction None',
        'rerun_command': "printf 'prnio\\n\\n' | fp2k",
    }
    (HERE / 'example-fits.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record['cases']['pr2nio4_none']['parameters']))


if __name__ == '__main__':
    main()
