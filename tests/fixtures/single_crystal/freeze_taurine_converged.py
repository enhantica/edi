"""Import an already completed independent fit; this writer never invokes FullProf."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from decimal import Decimal
from pathlib import Path

NUMBER = r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][-+]?\d+)?'
COMPONENTS = ('11', '22', '33', '12', '13', '23')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def codewords(text):
    lines = text.splitlines()
    result = {}

    def add(code, symbol, start, path):
        code = Decimal(code)
        if not code:
            return
        index = int(code / 10)
        coefficient = code - 10 * index
        if index in result or not coefficient:
            msg = 'Every independent FullProf codeword must have one nonzero coefficient'
            raise ValueError(msg)
        result[index] = {
            'symbol': symbol,
            'start': float(start),
            'path': path,
            'codeword_coefficient': float(coefficient),
        }

    for i, line in enumerate(lines):
        fields = line.split()
        if len(fields) >= 11 and fields[1] in {'S', 'O', 'N', 'H', 'C'}:
            atom = fields[0]
            for axis, start, code in zip(
                'xyz', fields[2:5], lines[i + 1].split()[:3], strict=True
            ):
                add(
                    code,
                    axis.upper() + '_' + atom,
                    start,
                    f'taurine.atom_site.{atom}.fract_{axis}',
                )
            for component, start, code in zip(
                COMPONENTS, lines[i + 2].split(), lines[i + 3].split(), strict=True
            ):
                add(
                    code,
                    'bet' + component + '_' + atom,
                    start,
                    f'taurine.atom_site_aniso.{atom}.adp_{component}',
                )
        if line.startswith('!   Sc1'):
            for bank, (start, code) in enumerate(
                zip(lines[i + 1].split(), lines[i + 2].split(), strict=True), 1
            ):
                add(code, f'Scale{bank}', start, f'senju_{bank}.linked_structure.taurine.scale')
        if line.startswith('! Ext1'):
            for component, start, code in zip(
                ('11', '22', '33'), lines[i + 1].split()[:3], lines[i + 2].split()[:3], strict=True
            ):
                add(
                    code,
                    'Ext' + str(('11', '22', '33').index(component) + 1),
                    start,
                    f'senju_1.extinction.coefficient_{component}',
                )
    if set(result) != set(range(1, 136)):
        msg = 'The owner input must declare exactly the 135 independent parameters'
        raise ValueError(msg)
    return result


def extract(folder, original):
    codes = codewords(original)
    output = (folder / 'taurine.out').read_text()
    summary = (folder / 'taurine.sum').read_text()
    final = output.split('SYMBOLIC NAMES AND FINAL VALUES AND SIGMA')[-1]
    pattern = rf'Parameter number\s+(\d+)\s*:\s*(\S+)\s+({NUMBER})\s*\(\s*\+/-\s*({NUMBER})\s*\)'
    parameters = []
    for number, symbol, value, sigma in re.findall(pattern, final):
        item = codes[int(number)]
        if symbol != item['symbol'] or float(sigma) <= 0:
            msg = 'Final FullProf parameter identity and uncertainty must match its codeword'
            raise ValueError(msg)
        parameters.append(
            dict(
                number=int(number),
                **item,
                value=float(value),
                reported_su=float(sigma),
                su=float(sigma) / abs(item['codeword_coefficient']),
            )
        )
    if len(parameters) != 135:
        msg = 'The converged FullProf output must expose all 135 final parameters'
        raise ValueError(msg)
    cycles = re.search(r'CYCLE No\.:\s*(\d+)\s*\n\s*=>\s*Convergence reached', output)
    if not cycles:
        msg = 'The independent output must explicitly report convergence'
        raise ValueError(msg)
    rows = []
    active = False
    for line in output.splitlines():
        if 'F2obs' in line and 'F2cal' in line and 'Extinction(y)' in line:
            active = True
            continue
        tokens = line.replace('Excl', '').split()
        if active and len(tokens) >= 12:
            try:
                hkl = list(map(int, tokens[:3]))
                difference = float(tokens[8])
            except ValueError:
                continue
            if 'Excl' not in line:
                rows.append({'hkl': hkl, 'difference_over_sigma': difference})
    n = int(re.search(r'No\. of reflections for pattern#:\s*1:\s*(\d+)', summary)[1])
    if len(rows) != n:
        msg = 'The selected reflection rows must match the FullProf summary count'
        raise ValueError(msg)
    return {
        'engine': next(line.strip() for line in summary.splitlines() if 'Version' in line),
        'cycle': int(cycles[1]),
        'n_free': len(parameters),
        'n_selected': n,
        'parameters': parameters,
        'reduced_chi_square_from_printed_rows': sum(r['difference_over_sigma'] ** 2 for r in rows)
        / (n - len(parameters)),
        'chi_square_reported': float(re.search(r'Chi2\(Intens\):\s*(' + NUMBER + ')', summary)[1]),
        'rf2w_percent': float(re.search(r'RF2w-factor\s*:\s*(' + NUMBER + ')', summary)[1]),
        'rf2_percent': float(re.search(r'RF2 -factor\s*:\s*(' + NUMBER + ')', summary)[1]),
    }


def freeze(original, run, example, destination):
    destination.mkdir(parents=True, exist_ok=False)
    original_bytes = (original / 'taurine.pcr').read_bytes()
    lines = original_bytes.splitlines(keepends=True)
    lines[10] = re.sub(rb'^\s*20\s+0\.10\b', b'200  0.01', lines[10], count=1)
    if lines[10] == original_bytes.splitlines(keepends=True)[10]:
        msg = 'The original input must carry the documented NCY 20 / Eps 0.10'
        raise ValueError(msg)
    (destination / 'original.pcr').write_bytes(original_bytes)
    (destination / 'input.pcr').write_bytes(b''.join(lines))
    if digest(original / 'taurine.int') != digest(run / 'taurine.int'):
        msg = 'Tightening convergence must not change a single observation byte'
        raise ValueError(msg)
    for name in (
        'taurine.int',
        'taurine.pcr',
        'taurine.out',
        'taurine.sum',
        'taurine.prf',
        'run.log',
    ):
        shutil.copyfile(run / name, destination / name)
    shutil.copytree(example, destination / 'project')
    reference = extract(destination, original_bytes.decode())
    reference['artifacts'] = {
        p.relative_to(destination).as_posix(): digest(p)
        for p in sorted(destination.rglob('*'))
        if p.is_file()
    }
    reference['conventions'] = {
        'coordinates': 'fractional',
        'adp': 'beta as printed by the final parameter list, not Betas*1E04',
        'su': 'FullProf manual eq. 3.7: divide printed sigma by the codeword coefficient',
        'chi_square': (
            'sum of selected printed Dif/sig squared divided by N minus p; '
            'printed headline retained separately'
        ),
        'tolerances': (
            'values within one conventional FullProf sigma; '
            's.u. ratio within 20 percent; N-p objective within 1 percent; '
            'rounded RF2w within 0.1 percentage point'
        ),
    }
    (destination / 'reference.json').write_text(json.dumps(reference, indent=2) + '\n')
    (destination / 'PROVENANCE.md').write_text("""# Converged taurine fitting reference

FullProf.2k 8.40 (Feb2026-ILL JRC), run 2026-10-24 at 14:20:11 CEST
(12:20:11 UTC), imported without executing FullProf again.

The owner supplied SENJU_taurine/taurine.pcr and taurine.int on 2026-10-23.
`original.pcr` preserves that input byte for byte. `input.pcr` changes only its
NCY/Eps line from 20 / 0.10 to 200 / 0.01. Every observation byte is unchanged.
`taurine.pcr` is the control file rewritten by FullProf AFTER fitting; it is
preserved as output and must not be mistaken for the starting input.
The complete .out, .sum and .prf are independent engine outputs. No earlier
verification or fitting reference is replaced.

The output explicitly converges at cycle 52 with 135 independent parameters
and 947 selected reflections. The summary prints Chi2 30.1 and RF2w 12.2 percent.
The trailing Fortran EOF in run.log occurs at the continuation prompt AFTER
all outputs were written. It is retained, never represented as an exit-zero run.

The reference writer parses final high-precision parameters from .out and
codewords from original.pcr. FullProf manual equations 3.7 and 3.8 define the
codeword coefficient in sigma and the N-p denominator. Scales and extinction
have coefficient 0.20; positions and beta components have coefficient 1.00.
Reported sigma and conventional sigma are both retained. Beta targets use the
final parameter list directly, avoiding the summary's displayed x10000 units.
The headline Chi2 and the independently summed selected Dif/sig objective are
retained separately; their difference is not hidden by changing the divisor.

The project is the committed six-dataset taurine fitting example, copied only
as input stimulus. No fitted product value supplies a target or an uncertainty.
`reference.json` pins all source, output and project hashes. This writer never
runs fp2k. No other reference quantity or bound is changed.
""")
    return reference


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('original', 'run', 'example', 'destination'):
        parser.add_argument('--' + key, type=Path, required=True)
    args = parser.parse_args()
    item = freeze(args.original, args.run, args.example, args.destination)
    print('Imported parameters:', item['n_free'], 'selected reflections:', item['n_selected'])


if __name__ == '__main__':
    main()
