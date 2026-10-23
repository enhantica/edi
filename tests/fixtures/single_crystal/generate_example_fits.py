"""Author fitted FullProf references without changing the fixed parity inputs."""

import argparse
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
COMPONENTS = ('11', '22', '33', '12', '13', '23')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tb_input():
    lines = (HERE / 'fullprof/sc-neut-cwl_tbti_anisotropic-adp/tbti.pcr').read_text().splitlines()
    codes = {
        'Tb': ([0, 0, 0, 0, 0], [11, 11, 11, 21, 21, 21]),
        'Ti': ([0, 0, 0, 0, 0], [31, 31, 31, 41, 41, 41]),
        'O1': ([51, 0, 0, 0, 0], [61, 71, 71, 0, 0, 81]),
        'O2': ([0, 0, 0, 0, 0], [91, 91, 91, 0, 0, 0]),
    }
    for index, line in enumerate(tuple(lines)):
        fields = line.split()
        if fields and fields[0] in codes and len(fields) >= 10:
            atom, tensor = codes[fields[0]]
            lines[index + 1] = ' '.join(map(str, atom))
            lines[index + 3] = ' '.join(map(str, tensor))
        if 'Number of ' in line and 'parameters' in line:
            lines[index] = '10 ' + line[line.index('!') :]
        if line.startswith('!   Sc1'):
            lines[index + 2] = '101 0 0 0 0 0'
    return '\n'.join(lines) + '\n'


def extract(summary, scale_factor):
    parameters = []
    for line in summary.split('Anisotropic Betas')[0].splitlines():
        match = re.match(r'\s*(\w+)\s+((?:[-\d.]+\(\s*\d+\)\s*){5})', line)
        if not match:
            continue
        values = re.findall(r'([-\d.]+)\(\s*(\d+)\)', match[2])
        for axis, (value, digits) in zip('xyz', values[:3], strict=True):
            su = int(digits) * 10 ** -len(value.partition('.')[2])
            if su:
                parameters.append({
                    'atom': match[1],
                    'kind': 'coordinate',
                    'component': axis,
                    'value': float(value),
                    'su': su,
                })
    lines = summary.split('Anisotropic Betas*1E04')[1].split('==> SCALE')[0].splitlines()
    for index, line in enumerate(tuple(lines)):
        fields = line.split()
        if len(fields) != 7 or fields[0] == 'Name':
            continue
        try:
            values = list(map(float, fields[1:]))
            sigmas = list(map(float, lines[index + 1].split()))
        except ValueError:
            continue
        if len(sigmas) != 6:
            raise ValueError('A FullProf tensor must have six uncertainty values')
        for component, value, sigma in zip(COMPONENTS, values, sigmas, strict=True):
            if sigma > 0:
                parameters.append({
                    'atom': fields[0],
                    'kind': 'beta',
                    'component': component,
                    'value': value / 1e4,
                    'su': sigma / 1e4,
                })
    scale = summary.split('=> Scale factors')[1].splitlines()[1].split()
    parameters.append({
        'kind': 'scale',
        'value': float(scale[0]) * scale_factor,
        'su': float(scale[1]) * scale_factor,
    })
    if not parameters or any(p['su'] <= 0 for p in parameters):
        raise ValueError('Every fitted oracle quantity needs a positive FullProf uncertainty')
    return parameters


def pr_biso_input():
    lines = (HERE / 'fullprof/sc-neut-cwl_pr2nio4_basic/prnio.pcr').read_text().splitlines()
    coordinates = {
        'Pr': (0.5, 0.5, 0.362),
        'Ni': (0, 0, 0),
        'O1': (0.25, 0.25, 0),
        'O2': (0, 0, 0.176),
        'Oi': (0.25, 0.25, 0.25),
        'Od': (0.075, 0.075, 0.175),
    }
    active = {
        'Pr': [False, False, True],
        'Ni': [False] * 3,
        'O1': [False] * 3,
        'O2': [False, False, True],
        'Oi': [False] * 3,
        'Od': [True] * 3,
    }
    result, index, next_code = [], 0, 1
    while index < len(lines):
        line = lines[index]
        fields = line.split()
        if fields and fields[0] in coordinates and len(fields) >= 11:
            atom = fields[0]
            anisotropic = fields[9] == '2'
            fields[2:5] = [format(value, '.8g') for value in coordinates[atom]]
            fields[5], fields[9] = '0.5', '0'
            codes = []
            for free in [*active[atom], True, False]:
                codes.append(str(next_code * 10 + 1) if free else '0')
                next_code += int(free)
            result.extend([' '.join(fields), ' '.join(codes)])
            index += 4 if anisotropic else 2
            continue
        if 'Number of ' in line and 'parameters' in line:
            line = '12 ' + line[line.index('!') :]
        if line.startswith('!NCY'):
            result.append(line)
            index += 1
            fields = lines[index].split()
            fields[:2] = ['100', '0.000001']
            line = ' '.join(fields)
        if line.startswith('!   Sc1'):
            result.extend([line, lines[index + 1], '121 0 0 0 0 0'])
            index += 3
            continue
        result.append(line)
        index += 1
    if next_code != 12:
        raise ValueError('The isotropic example must retain its eleven structural free parameters')
    return '\n'.join(result) + '\n'


def reparse_examples():
    path = HERE / 'example-fits.json'
    record = json.loads(path.read_text())
    for compound in ('tb2ti2o7', 'pr2nio4'):
        item = record['cases'][compound]
        stem = 'tbti' if compound == 'tb2ti2o7' else 'prnio'
        folder = HERE / 'example_fits' / compound
        if any(digest(folder / name) != expected for name, expected in item['artifacts'].items()):
            raise ValueError('Reparsing cannot change any independent FullProf artifact')
        item['parameters'] = extract((folder / (stem + '.sum')).read_text(), item['scale_factor'])
    path.write_text(json.dumps(record, indent=2) + '\n')


def extract_isotropic(summary, scale_factor):
    parameters = []
    for line in summary.splitlines():
        match = re.match(r'\s*(\w+)\s+((?:[-\d.]+\(\s*\d+\)\s*){5})', line)
        if not match:
            continue
        pairs = re.findall(r'([-\d.]+)\(\s*(\d+)\)', match[2])
        for index, (value, digits) in enumerate(pairs[:4]):
            su = int(digits) * 10 ** -len(value.partition('.')[2])
            if su:
                parameters.append({
                    'atom': match[1],
                    'kind': 'coordinate' if index < 3 else 'Biso',
                    **({'component': 'xyz'[index]} if index < 3 else {}),
                    'value': float(value),
                    'su': su,
                })
    scale = summary.split('=> Scale factors')[1].splitlines()[1].split()
    parameters.append({
        'kind': 'scale',
        'value': float(scale[0]) * scale_factor,
        'su': float(scale[1]) * scale_factor,
    })
    if not any(item['kind'] == 'Biso' for item in parameters):
        raise ValueError('The independent isotropic fit must expose Biso uncertainties')
    return parameters


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fp2k', type=Path)
    parser.add_argument('--reparse-only', action='store_true')
    parser.add_argument('--biso-only', action='store_true')
    parser.add_argument('--prnio-source', type=Path)
    parser.add_argument('--run-dir', type=Path)
    args = parser.parse_args()
    if args.reparse_only:
        reparse_examples()
        return
    if not args.fp2k or not args.run_dir or (not args.biso_only and not args.prnio_source):
        parser.error('FullProf authoring needs the binary, persistent run directory and source')
    result = (
        json.loads((HERE / 'example-fits.json').read_text())
        if args.biso_only
        else {'binary_sha256': digest(args.fp2k), 'cases': {}}
    )
    if args.biso_only and result['binary_sha256'] != digest(args.fp2k):
        raise ValueError('An added example must use the independently recorded FullProf binary')
    selection = (
        [('pr2nio4_biso', 'prnio', 1)]
        if args.biso_only
        else [('tb2ti2o7', 'tbti', 1), ('pr2nio4', 'prnio', 64)]
    )
    for compound, stem, scale_factor in selection:
        work = args.run_dir / compound
        work.mkdir(parents=True, exist_ok=True)
        dest = HERE / 'example_fits' / compound
        dest.mkdir(parents=True, exist_ok=True)
        if compound == 'pr2nio4_biso':
            if compound in result['cases']:
                raise ValueError('A new isotropic example cannot replace a committed reference')
            text = pr_biso_input()
            data = HERE / 'fullprof/sc-neut-cwl_pr2nio4_basic/prnio.int'
        elif compound == 'tb2ti2o7':
            text = tb_input()
            data = HERE / 'fullprof/sc-neut-cwl_tbti_anisotropic-adp/tbti.int'
        else:
            text = (args.prnio_source / 'prnio.pcr').read_text()
            data = args.prnio_source / 'prnio.int'
        (work / f'{stem}.pcr').write_text(text)
        (dest / 'input.pcr').write_text(text)
        shutil.copyfile(data, work / f'{stem}.int')
        shutil.copyfile(data, dest / f'{stem}.int')
        print(f'FullProf fit {compound}', flush=True)
        with (work / 'run.log').open('w') as log:
            run = subprocess.run(
                [str(args.fp2k.resolve())],
                input=f'{stem}\n\nn\n',
                text=True,
                cwd=work,
                stdout=log,
                stderr=subprocess.STDOUT,
                timeout=25,
                check=False,
            )
        summary = (work / f'{stem}.sum').read_text()
        output = (work / f'{stem}.out').read_text()
        if run.returncode != 0 or 'Convergence reached' not in output:
            raise ValueError(
                f'FullProf must finish its fit normally for {compound}; exit {run.returncode}'
            )
        for extension in ('sum', 'out'):
            shutil.copyfile(work / f'{stem}.{extension}', dest / f'{stem}.{extension}')
        result['cases'][compound] = {
            'scale_factor': scale_factor,
            'parameters': extract_isotropic(summary, scale_factor)
            if args.biso_only
            else extract(summary, scale_factor),
            'artifacts': {p.name: digest(p) for p in sorted(dest.iterdir())},
        }
    (HERE / 'example-fits.json').write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    main()
