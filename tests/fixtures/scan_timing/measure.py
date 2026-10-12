"""Run existing compiled commands, keep raw artifacts, then enforce the work/timing gate.

The configuration supplies the production demo-driver command and receipt filename.
Every native observation must come from that command. No test driver replaces it.
"""

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import time
from pathlib import Path

from contract import (
    BOUND,
    RESUME_FILES,
    compare,
    source_hashes,
    subject,
    validate_controls,
    validate_work,
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def execute(command, cwd, directory, environment):
    directory.mkdir(parents=True, exist_ok=False)
    (directory / 'command.json').write_text(json.dumps(command) + '\n')
    with (directory / 'stdout.txt').open('w') as out, (directory / 'stderr.txt').open('w') as err:
        started = time.monotonic_ns()
        result = subprocess.run(
            command,
            cwd=cwd,
            env={**os.environ, **environment},
            stdout=out,
            stderr=err,
            check=False,
        )
        elapsed_ms = (time.monotonic_ns() - started) / 1e6
    (directory / 'exit.txt').write_text(str(result.returncode) + '\n')
    return result.returncode, elapsed_ms


def fresh(project, destination):
    shutil.copytree(project, destination)
    for filename in RESUME_FILES:
        (destination / 'analysis' / filename).unlink(missing_ok=True)
    return subject(destination)


def expanded(parts, project, output, control='normal'):
    tokens = {'@PROJECT@': str(project), '@OUTPUT@': str(output), '@CONTROL@': control}
    return [tokens.get(part, part) for part in parts]


def invoke_app(build, project, directory, control, spec):
    observed_input = fresh(project, directory / 'project')
    if observed_input != spec:
        raise ValueError('the actual app scratch must retain every committed input byte')
    output = directory / 'native'
    output.mkdir(parents=True)
    scenario = {
        'normal': 'perf-162f',
        'refused-start': 'perf-control-refused',
        'cancel-after-40': 'perf-control-partial',
        'delayed': 'perf-162f',
    }[control]
    command = expanded(build['app_command'], directory / 'project', output, scenario)
    environment = {
        **build['environment'],
        'EDI_DEMO_PERF_PROJECT': str(directory / 'project'),
        'EDI_TIMING_OBSERVER_OUTPUT': str(output / 'observed.json'),
        'EDI_DEMO_DELAY_MS': '2000' if control == 'delayed' else '0',
    }
    command = [
        'bash',
        str(Path(__file__).with_name('launch-app.sh')),
        str(Path(build['source']) / 'tools/ci/app-platform.sh'),
        *command,
    ]
    rc, _ = execute(command, directory / 'project', directory / 'process', environment)
    work = json.loads((output / 'observed.json').read_text())
    work.update(input_sha256=observed_input['input_sha256'], preexisting_results=[])
    work.setdefault('skipped', [])
    work.setdefault('refused', [])
    work.setdefault('unfinished', [])
    intervals = {}
    timing_file = output / 'timings.tsv'
    if timing_file.exists():
        for line in timing_file.read_text().splitlines():
            _, key, value = line.split('\t')
            if key + '_ms' in intervals:
                raise ValueError('a native timing interval must be recorded only once')
            intervals[key + '_ms'] = float(value)
    native = {
        'path': 'app',
        'returncode': rc,
        'work': work,
        'intervals': intervals,
        'command_sha256': digest(Path(build['app_binary'])),
    }
    (directory / 'native.json').write_text(json.dumps(native, indent=2) + '\n')
    return native


def invoke_cli(build, project, directory, spec):
    observed = fresh(project, directory / 'project')
    if observed != spec:
        raise ValueError('the actual command scratch must retain every committed input byte')
    command = [
        *build['python_command'],
        '-m',
        'edi',
        'fit',
        str(directory / 'project'),
        '--report',
        'machine',
    ]
    rc, elapsed = execute(
        ['/usr/bin/time', '-v', *command],
        directory / 'project',
        directory / 'process',
        build['environment'],
    )
    if rc != 0:
        raise ValueError('a failed command has no timing credit; inspect its raw process files')
    work = {
        'input_sha256': observed['input_sha256'],
        'preexisting_results': [],
        'mode': 'sequential',
        'settings': observed['settings'],
        'skipped': [],
        'refused': [],
        'unfinished': [],
        'results_csv': (directory / 'project/analysis/results.csv').read_text(),
        'machine': (directory / 'process/stdout.txt').read_text(),
    }
    notes = directory / 'project/analysis/scan-notes.csv'
    if notes.exists() and len(notes.read_text().splitlines()) > 1:
        raise ValueError('a command with scan notes cannot claim complete clean work')
    row = {'path': 'cli', 'returncode': rc, 'work': work, 'intervals': {'process_ms': elapsed}}
    validate_work(row, spec)
    return row


def build_identity(build):
    source = Path(build['source'])
    head = subprocess.check_output(
        ['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True
    ).strip()
    compiled = subprocess.check_output(
        [*build['python_command'], '-c', 'import edi; print(edi.__build_commit__)'],
        env={**os.environ, **build['environment']},
        text=True,
    ).strip()
    if head != build['identity']['edi_source'] or compiled != head:
        raise ValueError('the command must identify its actual declared compiled source')
    cache = Path(build['cmake_cache']).read_text(encoding='utf-8')
    settings = {}
    for key in [
        'CMAKE_BUILD_TYPE',
        'CMAKE_CXX_COMPILER',
        'CMAKE_POSITION_INDEPENDENT_CODE',
        'EDI_BUILD_APP',
        'EDI_BUILD_BINDINGS',
    ]:
        values = [
            line.split('=', 1)[1] for line in cache.splitlines() if line.startswith(key + ':')
        ]
        if len(values) != 1:
            raise ValueError('the actual build must record its configuration: ' + key)
        settings[key] = values[0]
    if settings != build['identity']['configuration']:
        raise ValueError('the command configuration must come from its actual CMake cache')
    if digest(Path(build['app_binary'])) != build['identity']['command_sha256']:
        raise ValueError('the app command bytes must match the recorded native source witness')
    return {**build['identity'], 'source_sha256': source_hashes(source)}


def run_controls(builds, project, output, spec):
    controls = []
    for name in ['refused-start', 'cancel-after-40']:
        native = invoke_app(builds['fixed'], project, output / ('control-' + name), name, spec)
        controls.append({
            'name': name,
            'sequence': len(controls) + 1,
            'real_timing_path': True,
            'command_sha256': native['command_sha256'],
            'returncode': native['returncode'],
            'timing_credit': bool(native['intervals']),
            'completed_files': native['work'].get('completed_files', 0),
        })
    normal = invoke_app(builds['fixed'], project, output / 'control-normal', 'normal', spec)
    delayed = invoke_app(builds['fixed'], project, output / 'control-delayed', 'delayed', spec)
    for row in [normal, delayed]:
        validate_work(row, spec)
    for key in ['fit', 'reset']:
        controls.append({
            'name': 'delay-' + key,
            'sequence': len(controls) + 1,
            'real_timing_path': True,
            'command_sha256': delayed['command_sha256'],
            'returncode': delayed['returncode'],
            'normal_ms': normal['intervals'][key + '_ms'],
            'delayed_ms': delayed['intervals'][key + '_ms'],
        })
    # This control comes from the same fit-only comparator, called on raw real CLI runs.
    slow = []
    for rep in range(1, 6):
        for name in ['baseline', 'slow']:
            row = invoke_cli(builds[name], project, output / f'control-slow-{rep}-{name}', spec)
            slow.append({'build': name, **row})
    import statistics  # noqa: PLC0415 - measurement path only

    medians = {
        name: statistics.median(
            row['intervals']['process_ms'] for row in slow if row['build'] == name
        )
        for name in ['baseline', 'slow']
    }
    comparator_rc = int(medians['slow'] > BOUND * medians['baseline'])
    controls.append({
        'name': 'slow-fit',
        'sequence': 5,
        'real_timing_path': True,
        'command_sha256': builds['slow']['identity']['command_sha256'],
        'fixed_source': builds['slow']['identity']['edi_source'],
        'comparator_returncode': comparator_rc,
        'baseline_fit_ms': medians['baseline'],
        'fixed_fit_ms': medians['slow'],
    })
    validate_controls(controls)
    return controls


def measure(config, output):
    project = Path(config['project']).resolve()
    spec = subject(project)
    output.mkdir(parents=True, exist_ok=False)
    builds = config['builds']
    identity = {name: build_identity(builds[name]) for name in ['baseline', 'fixed', 'slow']}
    slow_identity = identity.pop('slow')
    if slow_identity['edi_source'] != 'bd72193898d2dc6fefb1d692703d1f7a4137c731':
        raise ValueError('the slow negative control must identify the actual pre-change build')
    host = '|'.join(platform.uname())
    controls = run_controls(builds, project, output, spec)
    rows = []
    for rep in range(1, 6):
        for name in ['baseline', 'fixed']:
            for path in ['cli', 'app']:
                directory = output / f'{rep}-{name}-{path}'
                row = (
                    invoke_cli(builds[name], project, directory, spec)
                    if path == 'cli'
                    else invoke_app(builds[name], project, directory, 'normal', spec)
                )
                row.update(
                    build=name, path=path, repetition=rep, sequence=len(rows) + 6, host=host
                )
                validate_work(row, spec)
                rows.append(row)
                (output / 'partial-runs.json').write_text(json.dumps(rows, indent=2) + '\n')
    receipt = {'schema': 1, 'host': host, 'builds': identity, 'runs': rows, 'controls': controls}
    (output / 'measurement.json').write_text(json.dumps(receipt, indent=2) + '\n')
    result = compare(receipt, spec)
    print(json.dumps(result, indent=2))
    return 0 if result['within_bound'] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('configuration', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    try:
        return measure(json.loads(args.configuration.read_text()), args.output)
    except (ValueError, KeyError, TypeError, OSError, subprocess.CalledProcessError) as error:
        print('Timing gate refused: ' + str(error))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
