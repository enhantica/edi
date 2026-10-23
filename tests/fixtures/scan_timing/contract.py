"""Validate complete work before granting timing credit; the bound is owner-specified."""

import csv
import hashlib
import io
import json
import math
import shlex
import shutil
import statistics
from pathlib import Path

BOUND = 1.05
# Frozen merge-base and that commit's SDK pin; derivation is retained in BASELINE.md.
BASELINE_EDI = 'a341b98154b53ea2499213a6c60b87e1371e9ce8'
BASELINE_CRYSTA = 'c2b02623e0b8354cec2dcfaeb2939645486c0dca'
RESUME_FILES = ('results.csv', 'results-provenance.csv', 'scan-notes.csv')


def prepared_analysis(data):
    """Omit saved fit starts; preserve all model and declared fitting input bytes."""
    lines = data.splitlines(keepends=True)
    output = []
    index = 0
    while index < len(lines):
        if (
            lines[index].strip() == b'loop_'
            and index + 1 < len(lines)
            and lines[index + 1].strip().startswith(b'_fit_parameter.')
        ):
            index += 1
            while index < len(lines) and lines[index].strip().startswith(b'_fit_parameter.'):
                index += 1
            while index < len(lines):
                token = lines[index].strip()
                if not token or token.startswith((b'_', b'loop_', b'data_', b'save_')):
                    break
                index += 1
            while index < len(lines) and not lines[index].strip():
                index += 1
            continue
        output.append(lines[index])
        index += 1
    return b''.join(output)


def prepare_input(project, destination):
    """Make the same fresh, fit-start-free input for every actual runner."""
    shutil.copytree(project, destination)
    for filename in RESUME_FILES:
        (destination / 'analysis' / filename).unlink(missing_ok=True)
    analysis = destination / 'analysis/analysis.edi'
    analysis.write_bytes(prepared_analysis(analysis.read_bytes()))
    return subject(destination)


def source_hashes(root):
    """A portable source witness survives a squash or a clone without old commit objects."""
    selected = ['core', 'app', 'lib', 'data', 'tools/ci', 'tests/fixtures/scan_timing']
    paths = [
        path
        for relative in selected
        for path in (root / relative).rglob('*')
        if path.is_file() and '__pycache__' not in path.parts and path.name != 'measurement.json'
    ]
    paths += [
        root / name for name in ['CMakeLists.txt', 'pixi.toml', 'pixi.lock', 'pyproject.toml']
    ]
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(paths)
    }


def subject(project):
    """Derive the declared inventory and literal conditions from the committed input."""
    text = (project / 'analysis/analysis.edi').read_text()
    declared = {}
    for line in text.splitlines():
        if line.startswith(('_fitting_mode.', '_minimizer.', '_sequential_fit.')):
            key, value = shlex.split(line)
            if key in declared:
                raise ValueError('duplicate declared setting: ' + key)
            declared[key] = value
    if declared.get('_fitting_mode.type') != 'sequential':
        raise ValueError('the performance subject must declare sequential fitting')
    folder = project / declared['_sequential_fit.data_dir']
    files = sorted(path.name for path in folder.glob(declared['_sequential_fit.file_pattern']))
    if len(files) != 162 or len(set(files)) != 162:
        raise ValueError('the committed subject must declare precisely 162 distinct files')
    return {
        'files': files,
        'settings': {
            key: value for key, value in declared.items() if key.startswith('_minimizer.')
        },
        'input_sha256': {
            path.relative_to(project).as_posix(): hashlib.sha256(
                prepared_analysis(path.read_bytes())
                if path == project / 'analysis/analysis.edi'
                else path.read_bytes()
            ).hexdigest()
            for path in sorted(project.rglob('*'))
            if path.is_file() and path.name not in RESUME_FILES
        },
    }


def csv_files(text, expected):
    reader = csv.DictReader(io.StringIO(text))
    fields = reader.fieldnames or []
    if len(fields) != len(set(fields)) or not {'file_path', 'fit_result.success'} <= set(fields):
        raise ValueError('results.csv must carry unique file and success columns')
    files = []
    for row in reader:
        if None in row or row['fit_result.success'] != 'True':
            raise ValueError('every results row must be complete and successful')
        files.append(Path(row['file_path']).name)
    if len(files) != len(expected) or sorted(files) != sorted(expected):
        raise ValueError('results.csv must name every expected dataset exactly once')
    return files


def validate_work(row, spec):
    """Receipt fields are observations of the real runner, never estimated work."""
    if row['returncode'] != 0:
        raise ValueError('a failed command has no timing credit')
    work = row['work']
    if work['input_sha256'] != spec['input_sha256'] or work['preexisting_results']:
        raise ValueError('every run must start from fresh identical input bytes')
    if work['mode'] != 'sequential' or work['settings'] != spec['settings']:
        raise ValueError('the run must use its declared mode and minimizer settings')
    csv_files(work['results_csv'], spec['files'])
    if work['skipped'] or work['refused'] or work['unfinished']:
        raise ValueError('skipped, refused or unfinished work has no timing credit')
    if row['path'] == 'cli':
        validate_machine(work)
    elif row['path'] == 'app':
        if (
            work['follow'] != 'adaptive'
            or not work['terminal_published']
            or work['outcome'] != 'success'
            or work['calculation_pending']
            or work['calculation_stale']
        ):
            raise ValueError(
                'the adaptive app must publish a successful fully settled terminal summary'
            )
        reset = work['reset']
        if (
            any(
                reset[key]
                for key in [
                    'remaining_files',
                    'result_rows',
                    'dataset_fit_outcomes',
                    'dataset_correlations',
                ]
            )
            or not reset['prefit_values_restored']
            or not reset['undo_available']
            or reset['calculation_pending']
        ):
            raise ValueError(
                'Reset fits must reach all of its actual empty-state and model conditions'
            )
    else:
        raise ValueError('unknown measured entry point')


def validate_machine(work):
    fields = {}
    for line in work['machine'].splitlines():
        if '=' in line:
            key, value = line.split('=', 1)
            if key in fields:
                raise ValueError('duplicate terminal machine field: ' + key)
            fields[key] = value
    if fields.get('record') != 'fit' or fields.get('status') != 'done':
        raise ValueError('the command must publish a terminal status=done machine record')


def validate_delay_slot(row, interval):
    values = [row.get(key) for key in ['delay_start_ms', 'delay_end_ms', 'interval_ms']]
    if row.get('interval') != interval or any(
        type(value) not in {int, float} or not math.isfinite(value) or value < 0
        for value in values
    ):
        raise ValueError('delay records must belong to a finite nonnegative interval clock')
    start, end, endpoint = values
    if end - start < 2000 or endpoint < end:
        raise ValueError('the measured endpoint must contain its real two-second signal slot')


def parse_app_timings(text, scenario, *, expect_delay=False):
    """Associate each recorded slot with the next endpoint on that same native clock."""
    intervals, slots = {}, {}
    pending = None
    for line in text.splitlines():
        fields = line.split('\t')
        if len(fields) != 3 or fields[0] != scenario:
            raise ValueError('each native timing record must name its actual scenario')
        _, label, raw = fields
        try:
            value = float(raw)
        except ValueError as error:
            raise ValueError('native clock records must be numeric') from error
        if not math.isfinite(value) or value < 0:
            raise ValueError('native clock records must be finite and nonnegative')
        if label.startswith('delay from ') and label.endswith(' to'):
            if not expect_delay or pending is not None:
                raise ValueError('unexpected or duplicate native delay record')
            try:
                start = float(label[len('delay from ') : -len(' to')])
            except ValueError as error:
                raise ValueError('native delay clock records must be numeric') from error
            pending = {'delay_start_ms': start, 'delay_end_ms': value}
            continue
        expected = 'fit' if not intervals else 'reset'
        if label != expected or label + '_ms' in intervals or value <= 0:
            raise ValueError('native endpoints must record one fit then one reset interval')
        if expect_delay:
            if pending is None:
                raise ValueError('each delayed endpoint requires its own native slot record')
            slot = {**pending, 'interval': label, 'interval_ms': value}
            validate_delay_slot(slot, label)
            slots[label] = slot
            pending = None
        intervals[label + '_ms'] = value
    if pending is not None or set(intervals) != {'fit_ms', 'reset_ms'}:
        raise ValueError('native timing requires two complete intervals and associated records')
    return intervals, slots


def validate_controls(controls):
    required = {'refused-start', 'cancel-after-40', 'delay-fit', 'delay-reset', 'slow-fit'}
    if {row['name'] for row in controls} != required or len(controls) != len(required):
        raise ValueError('every real timing-path negative control must run exactly once')
    for row in controls:
        if not row['real_timing_path'] or not row['command_sha256']:
            raise ValueError(
                'a constructed receipt is no substitute for a real timing-path control'
            )
        name = row['name']
        if name in {'refused-start', 'cancel-after-40'}:
            count = 0 if name == 'refused-start' else 40
            if row['returncode'] == 0 or row['timing_credit'] or row['completed_files'] != count:
                raise ValueError('refused and partial scenarios must fail without timing credit')
        elif name in {'delay-fit', 'delay-reset'}:
            if row['returncode'] != 0:
                raise ValueError('a failed delay control cannot prove its measured slot')
            validate_delay_slot(row, name.removeprefix('delay-'))
        elif (
            row['fixed_source'] != 'bd72193898d2dc6fefb1d692703d1f7a4137c731'
            or row['comparator_returncode'] == 0
            or row['fixed_fit_ms'] <= BOUND * row['baseline_fit_ms']
        ):
            raise ValueError('the pre-change slow build must fail the real fit-time comparator')


def validate_retained_sdk(retained, edi_source, cli_sha256, manifest_sha256):
    if (
        not isinstance(retained, dict)
        or retained.get('edi_source') != edi_source
        or retained.get('compiled_edi_source') != edi_source
        or retained.get('compiled_cli_sha256') != cli_sha256
        or retained.get('sdk_manifest_sha256') != manifest_sha256
    ):
        raise ValueError('The retained SDK observation must bind the unchanged compiled command')


def validate_builds(builds):
    baseline = builds['baseline']
    if (
        baseline['edi_source'] != BASELINE_EDI
        or baseline['crysta_source'] != BASELINE_CRYSTA
        or baseline.get('compiled_crysta_source') != BASELINE_CRYSTA
    ):
        raise ValueError('the baseline must use the frozen fork point and its pinned engine build')
    for build in builds.values():
        if build['configuration']['CMAKE_BUILD_TYPE'] != 'Release':
            raise ValueError('every compared build must use Release configuration')
        if build['configuration'] != baseline['configuration']:
            raise ValueError('both builds must use the same compiler and build configuration')
        native = build['native_configuration']
        if native['CMAKE_BUILD_TYPE'] != 'Release' or native != baseline['native_configuration']:
            raise ValueError('both native apps must use the same actual Release configuration')
        if build['compiled_edi_source'] != build['edi_source'] or not build['command_sha256']:
            raise ValueError('timings must identify the actual compiled command source and bytes')


def compare(receipt, spec):
    """Keep every run, with five alternating pairs on each measured entry point."""
    if receipt['schema'] != 1:
        raise ValueError('unknown timing receipt schema')
    validate_controls(receipt['controls'])
    validate_builds(receipt['builds'])
    rows = receipt['runs']
    expected = [
        (rep, build, path)
        for rep in range(1, 6)
        for build in ['baseline', 'fixed']
        for path in ['cli', 'app']
    ]
    if [(row['repetition'], row['build'], row['path']) for row in rows] != expected:
        raise ValueError(
            'exactly five alternating baseline/fixed runs per path must all be retained'
        )
    if any(control['sequence'] >= rows[0]['sequence'] for control in receipt['controls']):
        raise ValueError('all negative controls must finish before any credited measurement')
    if [row['sequence'] for row in rows] != sorted({row['sequence'] for row in rows}):
        raise ValueError('run ordering must have unique increasing sequence numbers')
    if not receipt['host'] or any(row['host'] != receipt['host'] for row in rows):
        raise ValueError('all compared runs must execute on the same identified host')
    for row in rows:
        validate_work(row, spec)
        required = {'process_ms'} if row['path'] == 'cli' else {'fit_ms', 'reset_ms'}
        if set(row['intervals']) != required:
            raise ValueError('each path must record exactly its declared end-to-end intervals')
        for value in row['intervals'].values():
            if not math.isfinite(value) or value <= 0:
                raise ValueError('measured intervals must be finite positive values')
    medians = {}
    for path, key in [
        ('cli', 'process_ms'),
        ('app', 'fit_ms'),
        ('app', 'reset_ms'),
        ('app', 'sum_ms'),
    ]:
        values = {}
        for build in ['baseline', 'fixed']:
            runs = [
                row['intervals'] for row in rows if row['path'] == path and row['build'] == build
            ]
            values[build] = statistics.median(
                interval['fit_ms'] + interval['reset_ms'] if key == 'sum_ms' else interval[key]
                for interval in runs
            )
        medians[path + '.' + key] = values
    failed = [
        name for name, values in medians.items() if values['fixed'] > BOUND * values['baseline']
    ]
    return {'bound': BOUND, 'medians_ms': medians, 'failed': failed, 'within_bound': not failed}


def main():
    import argparse  # noqa: PLC0415 - CLI only

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('receipt', type=Path)
    parser.add_argument('project', type=Path)
    args = parser.parse_args()
    try:
        result = compare(json.loads(args.receipt.read_text()), subject(args.project))
    except (ValueError, KeyError, TypeError, OSError) as error:
        print('Timing gate refused: ' + str(error))
        return 1
    print(json.dumps(result, indent=2))
    return 0 if result['within_bound'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
