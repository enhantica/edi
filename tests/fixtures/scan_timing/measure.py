"""Run existing compiled commands, keep raw artifacts, then enforce the work/timing gate.

The configuration supplies the production demo-driver command and receipt filename.
Every native observation must come from that command. No test driver replaces it.
"""

import argparse
import hashlib
import json
import os
import platform
import subprocess
import time
from pathlib import Path

from contract import (
    BOUND,
    compare,
    parse_app_timings,
    source_hashes,
    subject,
    validate_builds,
    validate_controls,
    validate_retained_sdk,
    validate_work,
)
from contract import (
    prepare_input as fresh,
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


def expanded(parts, project, output, control='normal'):
    tokens = {'@PROJECT@': str(project), '@OUTPUT@': str(output), '@CONTROL@': control}
    return [tokens.get(part, part) for part in parts]


def invoke_app(build, project, directory, control, spec):
    observed_input = fresh(project, directory / 'project')
    if observed_input != spec:
        raise ValueError('the app scratch must retain every prepared input byte')
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
    intervals, slots = {}, {}
    timing_file = output / 'timings.tsv'
    if timing_file.exists():
        intervals, slots = parse_app_timings(
            timing_file.read_text(), scenario, expect_delay=control == 'delayed'
        )
    native = {
        'path': 'app',
        'returncode': rc,
        'work': work,
        'intervals': intervals,
        'delay_slots': slots,
        'command_sha256': digest(Path(build['app_binary'])),
    }
    (directory / 'native.json').write_text(json.dumps(native, indent=2) + '\n')
    return native


def invoke_cli(build, project, directory, spec):
    observed = fresh(project, directory / 'project')
    if observed != spec:
        raise ValueError('the command scratch must retain every prepared input byte')
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


def configuration(cache_file):
    cache = Path(cache_file).read_text(encoding='utf-8')
    settings = {}
    for key in [
        'CMAKE_BUILD_TYPE',
        'CMAKE_CXX_COMPILER',
        'CMAKE_POSITION_INDEPENDENT_CODE',
        'EDI_BUILD_APP',
        'EDI_BUILD_BINDINGS',
        'CMAKE_CXX_FLAGS',
        'CMAKE_CXX_FLAGS_RELEASE',
    ]:
        values = [
            line.split('=', 1)[1] for line in cache.splitlines() if line.startswith(key + ':')
        ]
        if not values and key == 'CMAKE_POSITION_INDEPENDENT_CODE':
            settings[key] = 'not-declared'
            continue
        if len(values) != 1:
            raise ValueError('the actual build must record its configuration: ' + key)
        settings[key] = values[0]
    compiler = Path(settings.pop('CMAKE_CXX_COMPILER'))
    for key in ['CMAKE_CXX_FLAGS', 'CMAKE_CXX_FLAGS_RELEASE']:
        settings[key] = settings[key].replace(str(compiler.parent.parent), '@TOOLCHAIN@')
    settings['compiler_sha256'] = digest(compiler.resolve())
    settings['compiler_version'] = subprocess.check_output(
        [str(compiler), '--version'], text=True
    ).strip()
    return settings


def sdk_identity(build, cli_sha256):
    cache = Path(build['cmake_cache']).read_text(encoding='utf-8')
    directories = [
        line.split('=', 1)[1] for line in cache.splitlines() if line.startswith('crysta_DIR:')
    ]
    if len(directories) != 1:
        raise ValueError('The actual command must identify its installed engine package')
    manifest = Path(directories[0]).parents[2] / 'share/crysta-sdk/manifest.json'
    if 'sdk_manifest' in build:
        manifest = Path(build['sdk_manifest'])
        retained = json.loads(Path(build['retained_identity']).read_text(encoding='utf-8'))
        validate_retained_sdk(
            retained, build['identity']['edi_source'], cli_sha256, digest(manifest)
        )
    sdk = json.loads(manifest.read_text())
    reference = build['identity']['crysta_source']
    tree = subprocess.check_output(
        ['git', '-C', build['crysta_repository'], 'rev-parse', reference + '^{tree}'], text=True
    ).strip()
    if sdk['source_tree'] != tree:
        raise ValueError('The actual installed engine tree must match its declared source')
    return {
        'compiled_crysta_source': sdk['source_sha'],
        'crysta_source_tree': tree,
        'sdk_manifest_sha256': digest(manifest),
        'sdk_configuration': sdk['cmake_options'],
    }


def build_identity(build, *, cli_only=False):
    source = Path(build['source'])
    head = subprocess.check_output(
        ['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True
    ).strip()
    compiled, extension = (
        subprocess
        .check_output(
            [
                *build['python_command'],
                '-c',
                'import edi, edi._edi; print(edi.__build_commit__); print(edi._edi.__file__)',
            ],
            env={**os.environ, **build['environment']},
            text=True,
        )
        .strip()
        .splitlines()
    )
    if head != build['identity']['edi_source'] or compiled != head:
        raise ValueError('the command must identify its actual declared compiled source')
    settings = configuration(build['cmake_cache'])
    if settings != build['identity']['configuration']:
        raise ValueError('the command configuration must come from its actual CMake cache')
    command = Path(extension) if cli_only else Path(build['app_binary'])
    if digest(command) != build['identity']['command_sha256']:
        raise ValueError('the command bytes must match the recorded native source witness')
    observed = {
        **build['identity'],
        'compiled_cli_sha256': digest(Path(extension)),
        'source_sha256': source_hashes(source),
        **sdk_identity(build, digest(Path(extension))),
    }
    if not cli_only:
        observed['native_configuration'] = configuration(build['native_cmake_cache'])
    return observed


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
            **delayed['delay_slots'][key],
        })
    # This control comes from the same fit-only comparator, called on raw real CLI runs.
    slow = []
    for rep in range(1, 6):
        for name in ['baseline', 'slow']:
            row = invoke_cli(builds[name], project, output / f'control-slow-{rep}-{name}', spec)
            slow.append({'build': name, **row})
            (output / 'control-slow-runs.json').write_text(json.dumps(slow, indent=2) + '\n')
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
    (output / 'control-observations.json').write_text(json.dumps(controls, indent=2) + '\n')
    validate_controls(controls)
    return controls


def measure(config, output):
    project = Path(config['project']).resolve()
    spec = subject(project)
    output.mkdir(parents=True, exist_ok=False)
    builds = config['builds']
    identity = {
        name: build_identity(builds[name], cli_only=name == 'slow')
        for name in ['baseline', 'fixed', 'slow']
    }
    slow_identity = identity.pop('slow')
    if slow_identity['edi_source'] != 'bd72193898d2dc6fefb1d692703d1f7a4137c731':
        raise ValueError('the slow negative control must identify the actual pre-change build')
    validate_builds(identity)
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
                print('Completed ' + directory.name, flush=True)
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
