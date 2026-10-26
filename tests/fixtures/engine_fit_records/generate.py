"""Capture pinned-engine parity records after checking unchanged external references."""

import hashlib
import json
import subprocess
from pathlib import Path

from tests.conftest import corpus_case_dir, crysta_reference_prefix

HERE = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fields(text):
    return dict(line.split('=', 1) for line in text.splitlines())


def capture(case, verbosity):
    source = corpus_case_dir(case)
    cli = crysta_reference_prefix() / 'bin/crysta'
    command = [str(cli), 'fit', str(source / 'project'), '--dry', '--verbosity', verbosity]
    run = subprocess.run(command, text=True, capture_output=True, check=True, timeout=30)
    if run.stderr:
        raise ValueError(run.stderr)
    record = (
        '\n'.join(
            line
            for line in run.stdout.splitlines()
            if not line.startswith('elapsed_ms=') and '.elapsed_ms=' not in line
        )
        + '\n'
    )
    return (
        source,
        record,
        {
            'claim': 'Pinned crysta CLI parity regression pin, not an independent physics oracle',
            'engine_sha': (crysta_reference_prefix() / '.crysta-sha').read_text().strip(),
            'cli_sha256': digest(cli),
            'invocation': ['fit', f'tests/fitting/{case}/project', *command[3:]],
            'input_sha256': {
                p.relative_to(source / 'project').as_posix(): digest(p)
                for p in sorted((source / 'project').rglob('*'))
                if p.is_file()
            },
        },
    )


def main():
    source, record, provenance = capture('ncaf-wish-3bank-s5', 'full')
    actual = fields(record)
    reference = json.loads((source / 'expected.json').read_text())['variants']['ladder'][
        'quantities'
    ]
    checks = {}
    for name, spec in reference.items():
        if spec['kind'] != 'reference':
            continue
        value = float(actual[name])
        bound = max(spec['tol_abs'] or 0, (spec['tol_rel'] or 0) * abs(spec['value']))
        if abs(value - spec['value']) > bound:
            raise ValueError(f'Independent FullProf reference missed: {name}')
        checks[name] = {'actual': value, 'reference': spec['value'], 'bound': bound}
    baseline = source / 'goldens/joint-default.json'
    provenance.update({
        'decision': 'Out-of-range TOF reflections paint their finite tails',
        'historical_record_sha256': digest(baseline),
        'fullprof_expected_sha256': digest(source / 'expected.json'),
        'fullprof_files_sha256': {
            p.name: digest(p) for p in sorted((source / 'fullprof').iterdir()) if p.is_file()
        },
        'independent_checks': checks,
    })
    (HERE / 'joint-tail-default.json').write_text(
        json.dumps(
            {
                'provenance': provenance,
                'record': record,
            },
            indent=2,
        )
        + '\n'
    )
    _, record, provenance = capture('cosio-d20-s1', 'compact')
    if fields(record)['status'] != 'no_step' or fields(record)['converged'] != 'false':
        raise ValueError('The failed resumed descent retains its terminal reason')
    provenance['decision'] = 'The resumed descent ends with no accepted step'
    (HERE / 'cosio-ladder.json').write_text(
        json.dumps(
            {
                'provenance': provenance,
                'record': record,
            },
            indent=2,
        )
        + '\n'
    )


if __name__ == '__main__':
    main()
