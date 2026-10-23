"""Freeze single-crystal FullProf inputs and outputs; run only when authoring references."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

CASES = {
    'sc-neut-cwl_pr2nio4_basic': 'prnio',
    'sc-neut-cwl_tbti_basic': 'tbti',
    'sc-neut-cwl_tbti_anisotropic-adp': 'tbti',
    'sc-neut-cwl_tbti_isotropic-extinction': 'tbti',
    'sc-neut-tof_taurine_basic': 'taurine',
}
HERE = Path(__file__).resolve().parent
UPSTREAM_DIR = 'docs/docs/verification/fullprof'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reflections(output):
    rows = []
    active = False
    for line in output.splitlines():
        if 'F2obs' in line and 'F2cal' in line and 'Extinction(y)' in line:
            active = True
            continue
        fields = line.replace('Excl', '').split()
        if active and len(fields) >= 12:
            try:
                hkl = [int(v) for v in fields[:3]]
                values = [float(v) for v in fields[5:12]]
            except ValueError:
                continue
            rows.append({
                'hkl': hkl,
                'f2_obs': values[0],
                'f2_calc': values[1],
                'difference_over_sigma': values[3],
                'extinction': values[4],
                'sin_theta_over_lambda': values[5],
                'lambda_over_two': values[6],
                'excluded_from_fit': 'Excl' in line,
            })
    if not rows:
        message = 'FullProf must emit its complete single-crystal F2 table'
        raise ValueError(message)
    return rows


def main():  # noqa: PLR0914 - one authoring run and its provenance
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--upstream', type=Path, required=True)
    parser.add_argument('--revision', default='cb2cda7be6117199be8f8cac0a666a7bccd32d90')
    parser.add_argument('--fp2k', type=Path, required=True)
    parser.add_argument('--run-dir', type=Path, required=True)
    parser.add_argument('--reuse-output', action='store_true')
    args = parser.parse_args()
    manifest = {
        'upstream_revision': args.revision,
        'fp2k': args.fp2k.name,
        'fp2k_sha256': digest(args.fp2k),
        'cases': {},
    }
    for case, stem in CASES.items():
        dest = HERE / 'fullprof' / case
        work = args.run_dir / case
        dest.mkdir(parents=True, exist_ok=True)
        work.mkdir(parents=True, exist_ok=True)
        input_hashes = {}
        for ext in ('pcr', 'int'):
            name = f'{stem}.{ext}'
            raw = subprocess.check_output([
                shutil.which('git') or '/usr/bin/git',
                '-C',
                str(args.upstream),
                'show',
                f'{args.revision}:{UPSTREAM_DIR}/{case}/{name}',
            ])
            (dest / name).write_bytes(raw)
            if not args.reuse_output:
                (work / name).write_bytes(raw)
            input_hashes[name] = digest(dest / name)
        print(f'FullProf start {case}', flush=True)
        result = None
        if not args.reuse_output:
            with (work / 'run.log').open('w') as log:
                result = subprocess.run(
                    [str(args.fp2k.resolve())],
                    input=f'{stem}\n\n',
                    text=True,
                    cwd=work,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    timeout=30,
                    check=False,
                )
        output = (work / f'{stem}.out').read_text()
        rows = reflections(output)
        for ext in ('out', 'sum', 'prf'):
            shutil.copyfile(work / f'{stem}.{ext}', dest / f'{stem}.{ext}')
        data_lines = (dest / f'{stem}.int').read_text().splitlines()
        parsed = []
        for line in data_lines[3:]:
            fields = line.split()
            if not fields:
                continue
            if len(fields) < 5:
                message = f'Incomplete FullProf input row in {case}'
                raise ValueError(message)
            hkl = [int(v) for v in fields[:3]]
            if hkl == [0, 0, 0]:
                continue
            row = hkl + [float(v) for v in fields[3:5]]
            if 'tof' in case:
                row.append(float(fields[6]))
            parsed.append(row)
        dat = '# h k l F2 sigma' + (' wavelength' if 'tof' in case else '') + '\n'
        dat += ''.join(' '.join(str(v) for v in row) + '\n' for row in parsed)
        (dest / f'{stem}.dat').write_text(dat)
        chi = re.findall(r'Chi2\(Intens\):\s*([\d.E+-]+)', output)
        manifest['cases'][case] = {
            'stem': stem,
            'inputs': input_hashes,
            'outputs': {
                f'{stem}.{ext}': digest(dest / f'{stem}.{ext}') for ext in ('out', 'sum', 'prf')
            },
            'returncode': result.returncode if result is not None else None,
            'banner': next(line.strip() for line in output.splitlines() if 'Version' in line),
            'chi2_reported': float(chi[-1]),
            'input_rows': parsed,
            'calculated_rows': rows,
            'fit_parameters': [],
            'fit_status': 'Input fixes every parameter; no fitted values or uncertainties exist.',
        }
        print(f'FullProf complete {case}: input={len(parsed)} calculated={len(rows)}', flush=True)
    (HERE / 'fullprof.json').write_text(json.dumps(manifest, indent=2) + '\n')


if __name__ == '__main__':
    main()
