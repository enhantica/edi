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
        match = re.match(r'\s*(\w+)\s+((?:[-\d.]+\(\s*\d+\)\s*){6})', line)
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fp2k', type=Path, required=True)
    parser.add_argument('--prnio-source', type=Path, required=True)
    parser.add_argument('--run-dir', type=Path, required=True)
    args = parser.parse_args()
    result = {'binary_sha256': digest(args.fp2k), 'cases': {}}
    for compound, stem, scale_factor in [('tb2ti2o7', 'tbti', 1), ('pr2nio4', 'prnio', 64)]:
        work = args.run_dir / compound
        work.mkdir(parents=True, exist_ok=True)
        dest = HERE / 'example_fits' / compound
        dest.mkdir(parents=True, exist_ok=True)
        if compound == 'tb2ti2o7':
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
            'parameters': extract(summary, scale_factor),
            'artifacts': {p.name: digest(p) for p in sorted(dest.iterdir())},
        }
    (HERE / 'example-fits.json').write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    main()
