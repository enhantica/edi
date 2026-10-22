"""Author a labelled FullProf continuation diagnostic, never a fresh-start reference."""

import argparse
import json
import re
import shutil
from pathlib import Path

from run_fullprof import ROOT, digest, execute, fixed_twin

CASE = 'pd-xray-cwl_lam7o3-p021'
SUFFIXES = {'.pcr', '.new', '.dat', '.prf', '.sum', '.out', '.log'}


def capture(executable, logs):
    source = ROOT / 'knowledge/fitting/fullprof' / CASE
    home = source / 'continuation'
    twin = ROOT / 'knowledge/verification/fullprof' / CASE / 'continuation'
    home.mkdir()
    twin.mkdir()
    logs.mkdir(parents=True, exist_ok=True)
    text = re.sub(r'(!NCY[^\n]*\n)\s*\S+', r'\g<1>200', (source / 'fit.new').read_text())
    (home / 'fit.pcr').write_text(text)
    shutil.copyfile(source / 'fit.dat', home / 'fit.dat')
    execute(executable, home, 'fit', logs)
    (home / 'fit.log').write_text(
        (logs / 'continuation-fit.log').read_text().replace(str(ROOT), '<checkout>')
    )
    fixed_twin(home / 'fit.new', twin / 'fixed.pcr')
    shutil.copyfile(home / 'fit.dat', twin / 'fixed.dat')
    execute(executable, twin, 'fixed', logs)
    (twin / 'fixed.log').write_text(
        (logs / 'continuation-fixed.log').read_text().replace(str(ROOT), '<checkout>')
    )
    summary = (home / 'fit.sum').read_text()
    all_points = summary.split('RELIABILITY FACTORS WITH ALL NON-EXCLUDED POINTS FOR PATTERN:')[1]
    rwp = float(re.search(r'Rwp\s*[:=]\s*([\d.Ee+-]+)[^\n]*L.S.', all_points)[1]) / 100
    counts = [
        int(re.search(r'(\d+)\s+!Number of refined parameters', path.read_text())[1])
        for path in [source / 'fit.pcr', home / 'fit.pcr', home / 'fit.new']
    ]
    if counts != [39, 39, 39]:
        raise ValueError('The continuation must keep the original thirty-nine free parameters')
    log = (home / 'fit.log').read_text()
    record = {
        'program': 'FullProf 8.40',
        'scope': 'continuation diagnostic; not a fit directly from the committed start',
        'staging': 'FullProf self-continuation with the original free set unchanged',
        'source': str((source / 'fit.new').relative_to(ROOT)),
        'source_sha256': digest(source / 'fit.new'),
        'control_projection': 'NCY only: 200 cycles; the emitted three-column 1000 is ***',
        'converged': 'Convergence reached at this CYCLE' in log,
        'finite': re.search(r'\b(?:NaN|Infinity)\b', (home / 'fit.out').read_text()) is None,
        'n_free': 39,
        'r_wp': rwp,
        'artifacts_sha256': {p.name: digest(p) for p in home.iterdir() if p.suffix in SUFFIXES},
        'fixed_twin_sha256': {p.name: digest(p) for p in twin.iterdir() if p.suffix in SUFFIXES},
    }
    (home / 'reference.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps({key: record[key] for key in ['converged', 'finite', 'n_free', 'r_wp']}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--executable', type=Path, required=True)
    parser.add_argument('--logs', type=Path, required=True)
    args = parser.parse_args()
    capture(args.executable, args.logs)
