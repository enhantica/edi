"""Record FullProf's actual outputs and convergence evidence after authoring."""

import argparse
import hashlib
import json
import math
import re
import tempfile
from pathlib import Path

import numpy as np
from fullprof_inputs import ROOT, Writer

EXTENSIONS = {'.pcr', '.new', '.dat', '.prf', '.sum', '.out', '.log'}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parameters(home, case):
    output = (home / 'fit.out').read_text(errors='replace')
    pattern = r'Parameter number\s+(\d+)\s*:\s+(\S+)\s+([-+\d.Ee]+)\s*\(\s*\+/-\s*([-+\d.Ee]+)'
    result = {
        index: {'symbol': symbol, 'value': float(value), 'uncertainty': float(sigma)}
        for index, symbol, value, sigma in re.findall(pattern, output)
    }
    writer = Writer(case, False)
    with tempfile.TemporaryDirectory() as scratch:
        writer.write(Path(scratch) / 'mapping.pcr')
    codes = dict(writer.codes.assigned)
    return result, codes


def stopping_settings(control):
    budget = re.search(r'^!NCY[^\n]*\n\s*(\d+)\s+([\d.Ee+-]+)', control.read_text(), re.MULTILINE)
    if budget is None:
        raise ValueError(f'Missing FullProf cycle budget in {control}')
    return int(budget[1]), float(budget[2])


def refresh_project_inputs(record, home, case):
    project = ROOT / record['start_project']
    current = {
        str(path.relative_to(project)): digest(path) for path in sorted(project.rglob('*.edi'))
    }
    if current == record['project_sha256']:
        return
    with tempfile.TemporaryDirectory() as directory:
        scratch = Path(directory)
        for fixed, stem in [(True, 'start'), (False, 'fit')]:
            if stem == 'fit' and record['scope'] == 'calculation':
                continue
            Writer(case, fixed, cycles=record['cycles'], epsilon=record['epsilon']).write(
                scratch / f'{stem}.pcr'
            )
            for generated in scratch.glob(stem + '*'):
                if generated.read_bytes() != (home / generated.name).read_bytes():
                    raise ValueError(
                        f'Changed FullProf input requires a new run: {generated.name}'
                    )
    record['project_sha256'] = current


def prepare_record(path, home, simulation, case):
    record = json.loads(path.read_text())
    record['cycles'], record['epsilon'] = stopping_settings(
        home / ('start.pcr' if simulation else 'fit.pcr')
    )
    dispersion = Path(__file__).with_name('synchrotron-dispersion.json')
    if json.loads(dispersion.read_text())['case'] == case:
        record['dispersion_reference'] = str(dispersion.relative_to(ROOT))
        record['dispersion_reference_sha256'] = digest(dispersion)
    refresh_project_inputs(record, home, case)
    return record


def dispersion_notes(record, home):
    if 'dispersion_reference' not in record:
        return []
    notes = [
        'The explicit type-2 dispersion records use Sasaki (1989), KEK Report 88-14.',
        'The independent table brackets and their source digest are frozen in',
        f'`{record["dispersion_reference"]}`; the receipt binds that file.',
        'Interpolation is linear in photon energy at the committed 0.207109 A wavelength.',
        'FullProf retains its normal form factors; only Dfp and Dfpp are supplied.',
        '[FullProf manual, line 12, ITY=2](https://www.ill.eu/sites/fullprof/downloads/Docs/FullProf_Manual.pdf)',
        'documents the lower-case symbols and the synchrotron correction route.',
        '[Sasaki tables](https://www2.kek.jp/imss/pf/tools/sasaki/scatfac/scatfac.html).',
        '',
    ]
    if (home / 'strict-shift-attempt').is_dir():
        notes += [
            'The archived `strict-shift-attempt` used epsilon 0.001 and 1000 cycles',
            'from the same start but did not converge. The primary reference uses',
            'the established epsilon 0.1; no fitted result seeds another fit.',
            '',
        ]
    if (home / 'continuation/reference.json').is_file():
        notes += [
            'A separately labelled self-continuation is retained under `continuation`.',
            "It starts from this run's emitted .new with the same free set and a valid",
            '200-cycle control field. Its own receipt and fixed twin identify the staged',
            'diagnostic; it does not replace this reference from the committed start.',
            '',
        ]
    return notes


def finish(case, directories):  # noqa: PLR0914 - complete external output receipt
    simulation = case.endswith('_simulation')
    kind = 'verification' if simulation else 'fitting'
    home = ROOT / 'knowledge' / kind / 'fullprof' / case
    path = home / 'reference.json'
    record = prepare_record(path, home, simulation, case)
    stems = ['start'] if simulation else ['start', 'fit', 'fixed']
    twin = ROOT / 'knowledge/verification/fullprof' / case
    for stem in stems:
        candidates = [d / f'{case}-{stem}.log' for d in directories]
        existing = [p for p in candidates if p.is_file()]
        if existing:
            source = max(existing, key=lambda p: p.stat().st_mtime_ns)
            destination = twin if stem == 'fixed' else home
            destination.mkdir(parents=True, exist_ok=True)
            (destination / f'{stem}.log').write_text(
                source.read_text(errors='replace').replace(str(ROOT), '<checkout>')
            )
    if not simulation:
        output = (home / 'fit.out').read_text(errors='replace')
        summary = (home / 'fit.sum').read_text(errors='replace')
        finite = re.search(r'\b(?:NaN|Infinity)\b', output, re.IGNORECASE) is None
        record['finite_fit'] = finite
        log = (home / 'fit.log').read_text(errors='replace')
        record['converged'] = 'Convergence reached at this CYCLE' in log and finite
        record['fit_output_complete'] = bool(
            finite and (home / 'fit.new').is_file() and list(home.glob('fit*.prf'))
        )
        record['fullprof_parameters'], record['parameter_codes'] = parameters(home, case)
        sections = re.findall(
            r'RELIABILITY FACTORS WITH ALL NON-EXCLUDED POINTS FOR PATTERN:\s*\d+'
            r'(.*?)(?=RELIABILITY FACTORS|GLOBAL PARAMETERS|\Z)',
            summary,
            re.DOTALL,
        )
        bank_values = []
        for section in sections:
            match = re.search(r'Rwp\s*[:=]\s*([0-9.Ee+-]+)[^\n]*L.S.', section)
            if match:
                bank_values.append(float(match[1]) / 100)
        record['r_wp_by_bank'] = dict(zip(record['banks'], bank_values, strict=False))
        record.pop('r_wp', None)
        if finite and len(bank_values) == len(record['banks']):
            weights = []
            for index in range(1, len(bank_values) + 1):
                suffix = '' if len(bank_values) == 1 else f'_{index}'
                data = np.loadtxt(home / f'fit{suffix}.dat')
                weights.append(float(np.sum((data[:, 1] / data[:, 2]) ** 2)))
            record['r_wp'] = math.sqrt(
                sum(
                    value * value * weight
                    for value, weight in zip(bank_values, weights, strict=True)
                )
                / sum(weights)
            )
        record['parameters'] = {
            item['symbol'].removeprefix('X_').removesuffix('_ph1') + '.fract_x': item['value']
            for item in record['fullprof_parameters'].values()
            if case == 'pd-xray-cwl_lam7o3-p021' and item['symbol'] == 'X_O1_ph1'
        }
        record['twin_artifacts_sha256'] = {
            p.name: digest(p) for p in sorted(twin.iterdir()) if p.suffix in EXTENSIONS
        }
    record['artifacts_sha256'] = {
        p.name: digest(p) for p in sorted(home.iterdir()) if p.suffix in EXTENSIONS
    }
    path.write_text(json.dumps(record, indent=2, allow_nan=False) + '\n')
    notes = [
        '# FullProf authoring record',
        '',
        'FullProf fp2k 8.40 (Feb2026, ILL) was run at authoring time: '
        + record.get('authored_utc', '22 October 2026')
        + '.',
        'Tests read these committed outputs and never invoke fp2k.',
        '',
        f'Start: `{record["start_project"]}`. `reference.json` binds every input and output byte.',
        'No fitted values seed the start, and no parameters are fixed or released in stages.',
        'Input triples retain positive sigma; excluded and sigma-zero points are omitted.',
        'The range remains the background domain. FullProf Ins=10 reads six header lines.',
        '',
        (
            'Reproduce with `python tests/fixtures/example_catalogue/run_fullprof.py '
            f'--case {case} --cycles {record["cycles"]} '
            f'--epsilon {record["epsilon"]} '
            '--executable /path/to/fp2k --logs /persistent/logs`.'
        ),
        'The executable receives the PCR basename and blank responses on standard input.',
        'A terminal EOF after completed output is not a numerical failure. Logs are retained.',
        '',
    ]
    if not simulation:
        notes += [
            '`fit.pcr` uses Pcr=2. `fit.new` is the independent fitted model.',
            'Its fixed twin zeros every value/code field in that emitted file.',
            f'Finite output: {record["finite_fit"]}. Converged: {record["converged"]}.',
            (
                f'Fitting cycle budget: {record["cycles"]}; '
                f'shift tolerance epsilon: {record["epsilon"]}.'
            ),
            'The output parameter table and its code-index mapping are retained.',
            'Rwp uses all-point least-squares factors, pooled with observed weighted sums.',
            'The scan rows claim only their single template fit.',
            '',
        ]
        if not record['converged']:
            notes += [
                '**The fitting agreement gate remains open.** FullProf did not produce a finite',
                'converged fit from this start. These outputs document the attempt.',
                '',
            ]
        notes += dispersion_notes(record, home)
        if any(
            e['values']['_peak.type'] == 'cwl-pseudo-voigt-berar-baldinozzi'
            for e in Writer(case, True).experiments
        ):
            notes += [
                'Bérar-Baldinozzi uses FullProf Npr=5 for the mixing-eta model, with its signed',
                "coefficient map. This is distinct from diffraction-lib's TCH-based BeBa model.",
                '',
            ]
        (twin / 'PROVENANCE.md').write_text(
            '\n'.join([
                '# Fitted FullProf calculation',
                '',
                f'The source is `knowledge/fitting/fullprof/{case}/fit.new` from fp2k 8.40.',
                'The authoring projection zeros active codes and retains fitted values.',
                'The fitting record pins these artifacts and records convergence.',
                '',
            ])
        )
    (home / 'PROVENANCE.md').write_text('\n'.join(notes))
    return {key: record.get(key) for key in ('finite_fit', 'converged', 'n_free', 'r_wp')}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--logs', type=Path, action='append', required=True)
    parser.add_argument('--case', action='append')
    args = parser.parse_args()
    cases = args.case or [
        r['id']
        for r in json.loads((Path(__file__).parent / 'catalogue-selection.json').read_text())[
            'cases'
        ]
    ]
    for case in cases:
        print(case, finish(case, args.logs))
