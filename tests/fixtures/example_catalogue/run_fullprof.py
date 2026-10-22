"""Author FullProf references; this command is never called by a test.

Usage: python run_fullprof.py --executable /path/to/fp2k --logs /persistent/logs
Each project starts from its committed values. No fitted result seeds another fit.
"""

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import time
from pathlib import Path

from fullprof_inputs import ROOT, Writer


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fixed_twin(source, destination):  # noqa: PLR0912 - FullProf record families
    """Zero FullProf's documented value/code records in its emitted .new file."""
    lines = source.read_text().splitlines()
    indices = [i for i, line in enumerate(lines) if line.strip() and not line.startswith('!')]
    following = dict(zip(indices, indices[1:], strict=False))

    def zero(index, columns=None):
        fields = lines[index].split()
        for column in range(len(fields)) if columns is None else columns:
            fields[column] = '0'
        lines[index] = ' '.join(fields)

    for index, line in enumerate(list(lines)):
        if 'Number of refined parameters' in line:
            lines[index] = '0 !Number of refined parameters'
        if not line.startswith('!'):
            fields = line.split()
            if len(fields) == 11 and re.fullmatch(r'[A-Za-z][A-Za-z0-9+-]*', fields[0]):
                zero(following[index])
                if fields[9] == '2':
                    zero(following[following[following[index]]])
            continue
        header = line.lstrip('! ').split()
        if not header:
            continue
        start = next((i for i in indices if i > index), None)
        if start is None:
            continue
        if header[:1] == ['NCY']:
            fields = lines[start].split()
            fields[0] = '1'
            lines[start] = ' '.join(fields)
        elif header[0].startswith('2Theta/TOF/E'):
            cursor = start
            while (
                cursor < len(lines) and lines[cursor].strip() and not lines[cursor].startswith('!')
            ):
                zero(cursor, [2])
                cursor += 1
        elif header[0] == 'Zero':
            zero(start, [1, 3, 5, 7])
        elif header[0] in {'Scale', 'U', 'Sigma-2', 'Gamma-2', 'a', 'Pref1'}:
            zero(following[start])
        elif header[0] in {'Background', 'BACK'}:
            cursor = start
            while cursor < len(lines) and not lines[cursor].startswith('!'):
                zero(cursor + 1)
                cursor += 2
        elif header[0].startswith('Absorption'):
            zero(start, [1, 3])
    # FullProf's emitted absorption record has its own inline ABS label.
    for index, line in enumerate(list(lines)):
        if 'ABS: ABSCOR1 ABSCOR2' in line:
            zero(index, [1, 3])
    destination.write_text('\n'.join(lines).replace('fit_', 'fixed_') + '\n')


def execute(executable, directory, stem, logs):
    name = f'{directory.name}-{stem}'
    print(time.strftime('%H:%M:%S'), name, 'started', flush=True)
    output = logs / f'{name}.log'
    with output.open('w') as stream:
        stream.write(f'{directory}: {stem}.pcr through {executable}\n')
        stream.flush()
        try:
            result = subprocess.run(
                [str(executable)],
                cwd=directory,
                input=f'{stem}\n\n',
                text=True,
                stdout=stream,
                stderr=subprocess.STDOUT,
                check=False,
                timeout=1800,
            )
            status = result.returncode
        except subprocess.TimeoutExpired:
            status = 124
    (logs / f'{name}.exit').write_text(str(status) + '\n')
    print(time.strftime('%H:%M:%S'), name, 'exit', status, flush=True)
    return status


def run_case(case, executable, logs, cycles=200):
    simulation = case.endswith('_simulation')
    home = ROOT / 'knowledge' / ('verification' if simulation else 'fitting') / 'fullprof' / case
    home.mkdir(parents=True, exist_ok=True)
    # A failed new run must never inherit a previous run's output as evidence.
    for stem in ['start', 'fit']:
        for old in home.glob(stem + '*'):
            if old.is_file() and old.suffix not in {'.pcr', '.dat'}:
                old.unlink()
    start = Writer(case, True)
    start.write(home / 'start.pcr')
    execute(executable, home, 'start', logs)
    record = {
        'program': 'FullProf',
        'version': '8.40 Feb2026',
        'same_start': True,
        'start_project': str(start.project.relative_to(ROOT)),
        'project_sha256': {
            str(p.relative_to(start.project)): digest(p)
            for p in sorted(start.project.rglob('*.edi'))
        },
        'banks': [e['id'] for e in start.experiments],
        'scope': 'calculation'
        if simulation
        else ('template' if case.endswith('_scan') else 'fit'),
        'staging': 'none',
        'cycles': 1 if simulation else cycles,
    }
    if not simulation:
        fit = Writer(case, False, cycles=cycles)
        record['n_free'] = fit.write(home / 'fit.pcr')
        record['exit'] = execute(executable, home, 'fit', logs)
        twin = ROOT / 'knowledge/verification/fullprof' / case
        twin.mkdir(parents=True, exist_ok=True)
        for old in twin.glob('fixed*'):
            if old.is_file():
                old.unlink()
        if (home / 'fit.new').exists():
            fixed_twin(home / 'fit.new', twin / 'fixed.pcr')
            for data in home.glob('fit*.dat'):
                shutil.copyfile(data, twin / data.name.replace('fit', 'fixed', 1))
            record['twin_exit'] = execute(executable, twin, 'fixed', logs)
        profiles = sorted(home.glob('fit*.prf'))
        text = (home / 'fit.sum').read_text(errors='replace')
        agreement = re.findall(r'Rwp\s*[:=]\s*([0-9.Ee+-]+)[^\n]*L.S.', text)
        if agreement:
            record['r_wp'] = float(agreement[-1]) / 100
        record['fit_output_complete'] = bool(profiles and (home / 'fit.new').exists())
    record['artifacts_sha256'] = {
        p.name: digest(p)
        for p in sorted(home.iterdir())
        if p.suffix in {'.pcr', '.new', '.dat', '.prf', '.sum'}
    }
    (home / 'reference.json').write_text(json.dumps(record, indent=2) + '\n')
    return record


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--executable', type=Path, required=True)
    parser.add_argument('--logs', type=Path, required=True)
    parser.add_argument('--case', action='append')
    parser.add_argument('--cycles', type=int, default=200)
    args = parser.parse_args()
    if args.cycles < 1:
        parser.error('--cycles must be positive')
    args.logs.mkdir(parents=True, exist_ok=True)
    cases = args.case or [
        r['id']
        for r in json.loads((Path(__file__).parent / 'catalogue-selection.json').read_text())[
            'cases'
        ]
    ]
    results = {}
    for case in cases:
        results[case] = run_case(case, args.executable, args.logs, args.cycles)
        (args.logs / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
