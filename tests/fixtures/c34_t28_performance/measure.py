""": three alternating CLI runs on identical committed project bytes.

This measures existing executables. Command executable hashes are recorded;
Final-head build/CI provenance remains the caller's obligation. This script makes
no checkout-to-build claim.
"""

import argparse
import hashlib
import json
import math
import platform
import shutil
import statistics
import subprocess
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent


def hashes(root):
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob('*'))
        if path.is_file()
    }


def read_record(text):
    values = {}
    for line in text.splitlines():
        if '=' not in line:
            continue
        key, value = line.split('=', 1)
        if key in values:
            raise ValueError('duplicate machine field: ' + key)
        values[key] = value
    if (
        values.get('record') != 'fit'
        or values.get('status') != 'done'
        or values.get('converged') != 'true'
    ):
        raise ValueError('not a completed fit record: ' + repr(values))
    for key in ('elapsed_ms', 'iterations', 'n_free', 'n_points_fitted', 'reduced_chi_square'):
        value = float(values[key])
        if not math.isfinite(value) or value <= 0:
            raise ValueError('invalid positive engine metric: ' + key)
    return values


def compare(rows):
    if [(row['repetition'], row['repo']) for row in rows] != [
        (rep, repo) for rep in (1, 2, 3) for repo in ('crysta', 'edi')
    ]:
        message = ' requires exactly three alternating crysta/edi repetitions'
        raise ValueError(message)
    for left, right in zip(rows[::2], rows[1::2], strict=True):
        for name in ('iterations', 'n_free', 'n_points_fitted'):
            if left['record'][name] != right['record'][name]:
                raise ValueError('the two CLIs did different fit work: ' + name)
        if not math.isclose(
            float(left['record']['reduced_chi_square']),
            float(right['record']['reduced_chi_square']),
            rel_tol=1e-8,
        ):
            message = 'the two CLIs finished with different fit objectives'
            raise ValueError(message)
    medians = {
        repo: statistics.median(
            float(row['record']['elapsed_ms']) for row in rows if row['repo'] == repo
        )
        for repo in ('crysta', 'edi')
    }
    ratio = medians['edi'] / medians['crysta']
    return {'median_engine_ms': medians, 'edi_over_crysta': ratio, 'within_bound': ratio <= 1.3}


def measure(commands, output):
    provenance = json.loads((HERE / 'project-provenance.json').read_text())
    expected = provenance['project_sha256']
    if hashes(HERE / 'project') != expected:
        message = 'the committed  input differs from its visible generator record'
        raise ValueError(message)
    output.mkdir(parents=True, exist_ok=False)
    rows = []
    for rep in (1, 2, 3):
        for repo in ('crysta', 'edi'):
            with tempfile.TemporaryDirectory(prefix='-timing-') as scratch:
                project = Path(scratch) / 'project'
                shutil.copytree(HERE / 'project', project)
                command = [part.replace('@PROJECT@', str(project)) for part in commands[repo]]
                result = subprocess.run(
                    command, text=True, capture_output=True, check=False, timeout=300
                )
                (output / f'{repo}-{rep}.stdout').write_text(result.stdout)
                (output / f'{repo}-{rep}.stderr').write_text(result.stderr)
                if result.returncode:
                    raise RuntimeError(repo + ' fit refused: ' + result.stderr)
                if hashes(project) != expected:
                    raise RuntimeError(repo + ' dry fit mutated the common input')
                rows.append({
                    'repetition': rep,
                    'repo': repo,
                    'command': command,
                    'record': read_record(result.stdout),
                })
    report = {
        'machine': platform.uname()._asdict(),
        'command_executable_sha256': {
            repo: hashlib.sha256(Path(command[0]).read_bytes()).hexdigest()
            for repo, command in commands.items()
        },
        'commands': commands,
        'project_sha256': expected,
        'runs': rows,
        **compare(rows),
    }
    (output / 'measurement.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--crysta-bin', required=True, type=Path)
    parser.add_argument('--edi-python', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    commands = {
        'crysta': [
            str(args.crysta_bin.resolve()),
            'fit',
            '@PROJECT@',
            '--dry',
            '--verbosity',
            'compact',
            '--perf-info',
        ],
        'edi': [
            str(args.edi_python.resolve()),
            '-m',
            'edi',
            'fit',
            '@PROJECT@',
            '--dry',
            '--report',
            'machine',
            '--verbosity',
            'compact',
        ],
    }
    result = measure(commands, args.output)
    print(
        json.dumps({
            key: result[key] for key in ('median_engine_ms', 'edi_over_crysta', 'within_bound')
        })
    )
    return 0 if result['within_bound'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
