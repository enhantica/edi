# ruff: noqa: PLR0913, PLR0917
"Every scan output keeps independent outside bytes and complete resume history."

import csv
import importlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tests.fixtures import phase_scan

ROOT = Path(__file__).resolve().parents[3]
ENGINE = 'edi'
FILES = ['results.csv', 'results-provenance.csv', 'scan-notes.csv']
CALLERS = ['api', 'core'] if ENGINE == 'crysta' else ['api', 'direct']


def contents(directory):
    return {
        str(path.relative_to(directory)): path.read_bytes()
        for path in directory.rglob('*')
        if path.is_file()
    }


@pytest.fixture(scope='module')
def scan_history(tmp_path_factory):
    engine = importlib.import_module(ENGINE)
    root = tmp_path_factory.mktemp('scan-history')
    histories = {}
    for mode in ('sequential', 'independent'):
        path = phase_scan.materialize(root / mode, mode, negative=True)
        hidden = {}
        for data in sorted((path / 'experiments/scan').glob('*.xy'))[1:]:
            hidden[data.name] = data.read_bytes()
            data.unlink()
        engine.Project.load(path).analysis.fit()
        for name, body in hidden.items():
            (path / 'experiments/scan' / name).write_bytes(body)
        (path / 'analysis/scan-notes.csv').write_text(
            'file_path,negative_points,skipped_dataset,refusal\nexperiments/scan/01.xy,0,False,\n'
        )
        histories[mode] = path
    return histories


@pytest.fixture(scope='module')
def scan_faults(tmp_path_factory):
    root = tmp_path_factory.mktemp('scan-io-faults')
    library = root / 'faults.so'
    compiler = shutil.which('cc')
    assert compiler, 'The scan I/O witness requires the pinned native C compiler'
    result = subprocess.run(
        [
            compiler,
            '-shared',
            '-fPIC',
            str(ROOT / 'tests/fixtures/project_output/scan_faults.c'),
            '-o',
            str(library),
            *([] if sys.platform == 'darwin' else ['-ldl']),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )
    assert result.returncode == 0, 'The real scan I/O failure witness compiles: ' + result.stderr
    return library


@pytest.fixture(scope='module')
def core_scan(tmp_path_factory):
    if ENGINE != 'crysta':
        return None
    producer_command = importlib.import_module(
        'tests.fixtures.report_storage.temporary_aliases'
    ).producer_command

    root = tmp_path_factory.mktemp('core-scan-caller')
    flags, library = producer_command()
    flags[0] = shutil.which('clang++')
    flags = [flag for flag in flags if flag != '-fopenmp' and not flag.startswith('-W')]
    executable = root / 'scan'
    environment_lib = Path(sys.executable).resolve().parent.parent / 'lib'
    result = subprocess.run(
        [
            *flags,
            '-O0',
            '-fdelayed-template-parsing',
            *(['-fuse-ld=gold'] if sys.platform == 'linux' and shutil.which('ld.gold') else []),
            str(ROOT / 'tests/fixtures/project_output/core_probe.cpp'),
            str(library),
            '-lgomp' if sys.platform == 'linux' else '-lomp',
            '-L' + str(environment_lib),
            '-Wl,-rpath,' + str(environment_lib),
            '-lsleef',
            '-o',
            str(executable),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=25,
    )
    assert result.returncode == 0, (
        'The direct core scan observer links the producer API: ' + result.stderr
    )
    return executable


def invoke(
    path,
    caller,
    core_scan,
    scan_faults,
    *,
    fault=None,
    selected=None,
    temporary=None,
    prefix=False,
    dry=None,
):
    receipt = path.parent / 'fault-receipt'
    environment = dict(os.environ)
    if fault:
        environment['DYLD_INSERT_LIBRARIES' if sys.platform == 'darwin' else 'LD_PRELOAD'] = str(
            scan_faults
        )
        environment['SCAN_FAULT_RECEIPT'] = str(receipt)
        if fault == 'read':
            environment['SCAN_FAULT_READ_PATH'] = str(selected.resolve())
            if prefix:
                environment['SCAN_FAULT_PREFIX'] = '1'
        elif fault == 'remove':
            environment['SCAN_FAULT_REMOVE_PATH'] = str(temporary)
        else:
            environment['SCAN_FAULT_RENAME_PATH'] = str(selected)
    if caller == 'core':
        arguments = [str(core_scan), str(path), *([str(dry)] if dry else [])]
    else:
        arguments = [
            sys.executable,
            str(ROOT / 'tests/fixtures/project_output/worker.py'),
            ENGINE,
            str(path),
            caller,
            *([str(dry)] if dry else []),
        ]
    result = subprocess.run(
        arguments, env=environment, text=True, capture_output=True, check=False, timeout=10
    )
    assert 'scan-enter' in result.stdout, (
        'Every scan witness enters the delivered scan caller: ' + result.stderr
    )
    assert not any(
        name in result.stderr
        for name in ('TypeError:', 'AttributeError:', 'ImportError:', 'ModuleNotFoundError:')
    ), (
        'Every scan witness must reach the real core or adapter entry '
        'point with a supported observer signature: '
    ) + result.stderr
    return result, receipt


def project(tmp_path, scan_history, mode, history):
    if history == 'resume':
        path = tmp_path / 'project'
        shutil.copytree(scan_history[mode], path)
        return path
    return phase_scan.materialize(tmp_path / 'project', mode, negative=True)


def alias_file(path, external, filename, alias):
    selected = path / 'analysis' / filename
    sentinel = external / filename
    sentinel.write_bytes(selected.read_bytes())
    selected.unlink()
    if alias == 'symbolic':
        selected.symlink_to(sentinel)
    else:
        os.link(sentinel, selected)
    return selected, sentinel


@pytest.mark.parametrize('mode', ['sequential', 'independent'])
@pytest.mark.parametrize('caller', CALLERS)
@pytest.mark.parametrize('history', ['fresh', 'resume'])
def test_scan_output_parent_never_mutates_an_outside_directory(
    tmp_path, scan_history, core_scan, scan_faults, mode, caller, history
):
    path = project(tmp_path, scan_history, mode, history)
    external = tmp_path / 'outside'
    shutil.move(path / 'analysis', external)
    (external / 'independent-sentinel').write_bytes(b'outside tree\x00retained\n')
    (path / 'analysis').symlink_to(external, target_is_directory=True)
    outside = contents(external)
    result, _ = invoke(path, caller, core_scan, scan_faults)
    assert contents(external) == outside, (
        'Fresh and resumed core/adapter scans never append, remove, '
        'backfill or create a file through a linked analysis parent'
    )
    if result.returncode == 0:
        assert not (path / 'analysis').is_symlink(), (
            'A successful scan owns the analysis output parent'
        )
        assert len(list(csv.DictReader((path / 'analysis/results.csv').open()))) == 3, (
            'The ordinary successful scan writes each dataset exactly once'
        )


@pytest.mark.parametrize('mode', ['sequential', 'independent'])
@pytest.mark.parametrize('caller', CALLERS)
@pytest.mark.parametrize('filename', FILES)
@pytest.mark.parametrize('alias', ['symbolic', 'hard'])
@pytest.mark.parametrize('failure', ['none', 'remove', 'rename'])
@pytest.mark.parametrize('temporary_target_kind', ['outside', 'published'])
def test_each_csv_detaches_final_and_temporary_aliases(
    tmp_path,
    scan_history,
    core_scan,
    scan_faults,
    mode,
    caller,
    filename,
    alias,
    failure,
    temporary_target_kind,
):
    path = project(tmp_path, scan_history, mode, 'resume')
    external = tmp_path / 'outside'
    external.mkdir()
    selected, _sentinel = alias_file(path, external, filename, alias)
    temporary = Path(str(selected) + '.own')
    temporary_target = external / 'temporary-sentinel'
    temporary_target.write_bytes(b'retained temporary alias\x00independent\n')
    if temporary_target_kind == 'published':
        temporary_target = selected
    if alias == 'symbolic':
        temporary.symlink_to(temporary_target)
    else:
        os.link(temporary_target, temporary)
    outside = contents(external)
    previous = selected.read_bytes()
    result, receipt = invoke(
        path,
        caller,
        core_scan,
        scan_faults,
        fault=None if failure == 'none' else failure,
        selected=selected,
        temporary=temporary,
    )
    assert contents(external) == outside, (
        'Every CSV append and detachment preserves outside final and '
        'temporary alias bytes even after removal or replacement refuses'
    )
    if result.returncode:
        assert selected.read_bytes() == previous, (
            'A refused scan detachment preserves the complete previously published CSV'
        )
    elif failure != 'none' and receipt.exists():
        pytest.fail('An injected scan output removal or replacement failure must reach the caller')
    else:
        assert not selected.is_symlink(), 'Successful scan output owns its final entry'
        assert selected.stat().st_nlink == 1, 'Successful scan output owns the final CSV inode'
        assert selected.read_bytes().startswith(previous), (
            'Successful detachment retains the entire resume header and row prefix'
        )
        assert len(selected.read_bytes()) > len(previous), (
            'Each named results, provenance and notes append is actually reached'
        )


@pytest.mark.parametrize('mode', ['sequential', 'independent'])
@pytest.mark.parametrize('caller', CALLERS)
@pytest.mark.parametrize('filename', FILES)
@pytest.mark.parametrize('alias', ['symbolic', 'hard'])
@pytest.mark.parametrize('prefix', [False, True], ids=['empty', 'partial'])
def test_failed_detachment_read_never_publishes_a_truncated_csv(
    tmp_path, scan_history, core_scan, scan_faults, mode, caller, filename, alias, prefix
):
    path = project(tmp_path, scan_history, mode, 'resume')
    external = tmp_path / 'outside'
    external.mkdir()
    selected, _sentinel = alias_file(path, external, filename, alias)
    previous = selected.read_bytes()
    outside = contents(external)
    result, receipt = invoke(
        path, caller, core_scan, scan_faults, fault='read', selected=selected, prefix=prefix
    )
    assert receipt.exists(), 'The failed-copy observer emits a reached-source receipt'
    assert 'failed' in receipt.read_text(), (
        'The failed-copy witness reaches the source read after '
        'retained-row admission and fitting have succeeded'
    )
    assert result.returncode != 0, (
        'An empty or partial source-copy failure is reported instead of '
        'publishing a complete scan update'
    )
    assert selected.read_bytes() == previous, (
        'A source-read failure preserves the complete CSV header and '
        'every previously committed resume row'
    )
    assert contents(external) == outside, (
        'A failed detachment read never changes the aliased outside source'
    )


@pytest.mark.parametrize('mode', ['sequential', 'independent'])
@pytest.mark.parametrize('caller', CALLERS)
@pytest.mark.parametrize('parent', ['owned', 'linked'])
@pytest.mark.parametrize('rewrite', [False, True], ids=['append', 'backfill'])
def test_provenance_backfill_and_ordinary_scan_controls(
    tmp_path, scan_history, core_scan, scan_faults, mode, caller, parent, rewrite
):
    path = project(tmp_path, scan_history, mode, 'resume')
    if rewrite:
        provenance = path / 'analysis/results-provenance.csv'
        lines = provenance.read_text().splitlines()
        provenance.write_text('\n'.join(','.join(line.split(',')[:-1]) for line in lines) + '\n')
    external = tmp_path / 'outside'
    if parent == 'linked':
        shutil.move(path / 'analysis', external)
        (path / 'analysis').symlink_to(external, target_is_directory=True)
    else:
        external.mkdir()
    outside = contents(external)
    result, _ = invoke(path, caller, core_scan, scan_faults)
    assert contents(external) == outside, (
        'Provenance reconciliation and backfill never remove or rewrite '
        'entries through an outside parent'
    )
    if parent == 'owned':
        assert result.returncode == 0, (
            'An owned ordinary scan completes both appending and legacy provenance backfill: '
        ) + result.stderr
        assert len(list(csv.DictReader((path / 'analysis/results-provenance.csv').open()))) == 3, (
            'Backfill and ordinary append retain exactly one provenance row per scan dataset'
        )


@pytest.mark.parametrize('mode', ['sequential', 'independent'])
@pytest.mark.parametrize('parent', ['owned', 'linked'])
@pytest.mark.parametrize('target', FILES)
def test_dry_scan_copies_resume_state_only_into_an_owned_destination(
    tmp_path, scan_history, core_scan, scan_faults, mode, parent, target
):
    path = project(tmp_path, scan_history, mode, 'resume')
    scratch = tmp_path / 'dry'
    scratch.mkdir()
    external = tmp_path / 'outside'
    external.mkdir()
    # A missing results file admits the dry-copy branch; other targets retain aliases.
    if target != 'results.csv':
        (external / target).write_bytes(b'independent dry destination bytes\n')
    if parent == 'linked':
        (scratch / 'analysis').symlink_to(external, target_is_directory=True)
    else:
        (scratch / 'analysis').mkdir()
        if target != 'results.csv':
            (scratch / 'analysis' / target).symlink_to(external / target)
    before = contents(external)
    source_before = contents(path)
    result, _ = invoke(
        path, 'core' if ENGINE == 'crysta' else 'direct', core_scan, scan_faults, dry=scratch
    )
    assert contents(external) == before, (
        'Core dry-run state copying preserves every outside destination entry and byte'
    )
    assert contents(path) == source_before, (
        'A dry scan never mutates the loaded source project or its resume state'
    )
    if result.returncode == 0:
        assert not (scratch / 'analysis').is_symlink(), (
            'A successful dry scan owns its destination analysis directory'
        )


@pytest.mark.parametrize('mode', ['sequential', 'independent'])
@pytest.mark.parametrize('history', ['fresh', 'resume'])
@pytest.mark.parametrize(
    'alias', ['parent', 'results.csv', 'results-provenance.csv', 'scan-notes.csv', 'none']
)
def test_real_cli_scan_uses_the_same_output_boundary(tmp_path, scan_history, mode, history, alias):
    path = project(tmp_path, scan_history, mode, history)
    external = tmp_path / 'outside'
    if alias == 'parent':
        shutil.move(path / 'analysis', external)
        (path / 'analysis').symlink_to(external, target_is_directory=True)
    else:
        external.mkdir()
        if alias != 'none':
            if not (path / 'analysis' / alias).exists():
                shutil.copy2(scan_history[mode] / 'analysis' / alias, path / 'analysis' / alias)
            alias_file(path, external, alias, 'symbolic')
    previous = contents(external)
    arguments = (
        [sys.executable, '-m', 'edi', 'fit', str(path), '--verbosity', 'off']
        if ENGINE == 'edi'
        else [
            str(next((ROOT / 'build').glob('cp312-abi3*/crysta'))),
            'fit',
            str(path),
            '--verbosity',
            'off',
        ]
    )
    result = subprocess.run(arguments, text=True, capture_output=True, check=False, timeout=10)
    assert not any(
        error in result.stderr for error in ('TypeError:', 'ImportError:', 'ModuleNotFoundError:')
    ), 'The CLI witness invokes the actual supported scan command'
    assert contents(external) == previous, (
        'The real CLI scan never writes through retained parent or final CSV aliases'
    )
    if alias == 'none':
        assert result.returncode == 0, (
            'An ordinary unaliased CLI scan completes successfully: ' + result.stderr
        )
        assert len(list(csv.DictReader((path / 'analysis/results.csv').open()))) == 3, (
            'The successful CLI scan actually writes the complete dataset inventory'
        )


@pytest.mark.parametrize('mode', ['sequential', 'independent'])
@pytest.mark.parametrize('caller', ['api'])
@pytest.mark.parametrize('filename', FILES)
@pytest.mark.parametrize('alias', ['symbolic', 'hard'])
def test_kernel_removal_refusal_keeps_retained_temporary_aliases(
    tmp_path, scan_history, core_scan, scan_faults, mode, caller, filename, alias
):
    path = project(tmp_path, scan_history, mode, 'resume')
    external = tmp_path / 'outside'
    external.mkdir()
    selected, _sentinel = alias_file(path, external, filename, alias)
    temporary = Path(str(selected) + '.own')
    outside_file = external / 'temporary-sentinel'
    outside_file.write_bytes(b'independent writable temporary bytes\n')
    if alias == 'symbolic':
        temporary.symlink_to(outside_file)
    else:
        os.link(outside_file, temporary)
    outside = contents(external)
    previous = selected.read_bytes()
    directory = selected.parent
    directory.chmod(0o555)
    try:
        result, _ = invoke(path, caller, core_scan, scan_faults)
        assert contents(external) == outside, (
            'A real non-writable output directory cannot turn a retained '
            'temporary alias into a truncating write to outside bytes'
        )
        if result.returncode:
            assert selected.read_bytes() == previous, (
                'A kernel-level removal refusal retains the complete earlier scan CSV'
            )
    finally:
        directory.chmod(0o755)
