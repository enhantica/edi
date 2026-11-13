"""ADR-0111: a converged scan row can have an undefined moment uncertainty."""

import csv
import math
import os
import subprocess
import sys
from pathlib import Path

import edi
import pytest

from tests.fixtures.magnetic_pnma import commensurate, reference
from tests.fixtures.scan_csv import CONDITION_COLUMNS, assert_reported_legacy

FIRST = '01_152_054p9730.dat'
SECOND = '02_153_055p0000.dat'
MOMENT = 'cosio.atom_site_moment.Co1.crystalaxis_x'
FIELDS = [
    'file_path',
    'fit_result.reduced_chi_square',
    'fit_result.success',
    'fit_result.iterations',
    # The extract column is its declared target, as in the retained magnetic scan.
    'diffrn.ambient_temperature',
    MOMENT,
    MOMENT + '.uncertainty',
]


def rows(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def scan(root, bad=None):
    # a=5, b=1.2, c=1.3 and the narrow 55-degree window contain only h00.
    # For M=(Mx,0,0), M_perp=M-e(e.M)=0, so dI/dMx=0 at every start.
    # The ordinary covariance cannot determine Mx; no fitted accuracy is an oracle.
    structure = commensurate.structure(b=1.2, moment='3.125() 0 0')
    structure = (
        structure
        .replace('_cell.length_a 4', '_cell.length_a 5')
        .replace('_cell.length_c 6', '_cell.length_c 1.3')
        .replace('A Co a', 'Co1 Co a')
        .replace('A 3.125()', 'Co1 3.125()')
    )
    experiment = (reference.ROOT / 'compound-experiment.edi').read_text()
    experiment = experiment.split('loop_\n_data.two_theta')[0]
    experiment = (
        experiment
        .replace('_instrument.setup_wavelength 1.87', '_instrument.setup_wavelength 1.54')
        .replace(
            '_instrument.calib_twotheta_offset 0.29433', '_instrument.calib_twotheta_offset 0'
        )
        .replace('_peak.broad_gauss_u 0.273213', '_peak.broad_gauss_u 0')
        .replace('_peak.broad_gauss_v -0.587787', '_peak.broad_gauss_v 0')
        .replace('_peak.broad_gauss_w 0.410988', '_peak.broad_gauss_w .04')
    )
    points = ''.join(f'{54.5 + i * 0.05:.8f} {2 + i * 0.01:.8f} 1\n' for i in range(21))
    reference.project(
        root,
        structure,
        experiment
        + 'loop_\n_data.two_theta\n_data.intensity_meas\n_data.intensity_meas_su\n'
        + points,
    )
    data = root / 'experiments/scan'
    data.mkdir()
    for name, temperature in [(FIRST, '54.973'), (SECOND, '55')]:
        (data / name).write_text('TEMP ' + temperature + '\n' + points)
    analysis = root / 'analysis'
    analysis.mkdir()
    (analysis / 'analysis.edi').write_text(
        '_edi.schema_version 3\n_minimizer.type crysta\n_minimizer.max_iterations 4\n'
        '_fitting_mode.type sequential\n_sequential_fit.data_dir experiments/scan\n'
        '_sequential_fit.file_pattern *.dat\n_sequential_fit.reverse false\n'
        'loop_\n_sequential_fit_extract.id\n_sequential_fit_extract.target\n'
        '_sequential_fit_extract.pattern\n_sequential_fit_extract.required\n'
        'temperature diffrn.ambient_temperature "^TEMP\\s+([0-9.]+)" true\n'
    )
    row = [f'experiments/scan/{FIRST}', '1.25', 'True', '4', '54.973', '3.125', 'nan']
    if bad == 'value':
        row[-2] = 'nan'
    elif bad == 'chi':
        row[1] = 'nan'
    elif bad == 'infinite-su':
        row[-1] = 'inf'
    with (analysis / 'results.csv').open('w', newline='') as stream:
        writer = csv.writer(stream, lineterminator='\n')
        writer.writerow(FIELDS)
        writer.writerow(row)
    return root


def continue_scan(root):
    return subprocess.run(
        [
            sys.executable,
            '-m',
            'edi',
            'fit',
            str(root),
            '--report',
            'human',
            '--verbosity',
            'full',
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
        env={**os.environ, 'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1'},
    )


@pytest.mark.parametrize('save_first', [False, True], ids=['resume', 'save-reload-resume'])
def test_converged_nan_moment_su_loads_continues_and_stays_undefined(tmp_path, save_first):
    root = scan(tmp_path / 'scan')
    initial = rows(root / 'analysis/results.csv')
    project = edi.Project.load(root)
    # Existing bridge to index_scan_results, the same native reader the dataset view uses.
    assert project._scan_notes()['refused'] == [], (
        'The native dataset index admits the converged row with an undefined uncertainty'
    )
    if save_first:
        root = tmp_path / 'saved'
        project.save_as(root)
        project = edi.Project.load(root)
        assert project._scan_notes()['refused'] == [], (
            'Reloaded scan history is admitted by the same native dataset index'
        )
        assert rows(root / 'analysis/results.csv') == initial, (
            'Save/reload retains the converged row and its literal nan uncertainty'
        )
    result = continue_scan(root)
    assert result.returncode == 0, (
        'ADR-0111 a converged row with undefined s.u. is admitted by the ordinary scan reader: '
        + result.stdout
        + result.stderr
    )
    actual = rows(root / 'analysis/results.csv')
    assert len(actual) == 2, (
        'Continue keeps the converged first row and appends exactly the remaining frame'
    )
    assert_reported_legacy(actual[0], initial[0])
    assert list(actual[0]) == [*FIELDS, *CONDITION_COLUMNS]
    assert Path(actual[1]['file_path']).name == SECOND, (
        'The scan continues to the next declared data file'
    )
    assert math.isnan(float(actual[1][MOMENT + '.uncertainty'])), (
        'The h00-only longitudinal component has ordinary undefined covariance, never zero s.u.'
    )
    restored = edi.Project.load(root)
    assert restored._scan_notes()['refused'] == [], (
        'Both retained and newly fitted undefined rows remain readable by the dataset index'
    )
    assert restored.structure.atom_site_moment['Co1'].crystalaxis_x.uncertainty is None, (
        'ADR-0111 an undefined fitted s.u. is exposed as None on the parameter after reload'
    )
    assert 'crysta.fit.su_undefined' not in result.stderr, (
        'Default Warning hides Info diagnostics while the saved s.u. remains undefined'
    )
    destination = tmp_path / 'second-save'
    restored.save_as(destination)
    edi.Project.load(destination)
    assert rows(destination / 'analysis/results.csv') == actual, (
        'A later save/reload keeps both scan rows and every undefined uncertainty cell'
    )


@pytest.mark.parametrize('bad', ['value', 'chi', 'infinite-su'])
def test_undefined_su_admission_does_not_admit_nonfinite_values_or_metrics(tmp_path, bad):
    root = scan(tmp_path / 'scan', bad)
    path = root / 'analysis/results.csv'
    before = path.read_bytes()
    with pytest.raises((ValueError, RuntimeError), match=r'results\.csv'):
        edi.Project.load(root)._scan_notes()
    result = continue_scan(root)
    assert result.returncode != 0, (
        'Only undefined uncertainties may be nan; '
        'parameter values and converged metrics stay finite'
    )
    assert 'results.csv' in result.stdout + result.stderr, (
        'The ordinary reader, rather than command syntax, refuses the retained CSV cell'
    )
    assert path.read_bytes() == before, (
        'Refusing a malformed retained row does not rewrite its scan history'
    )


USER_LEVELS = [None, 'error', 'warning', 'info', 'debug']
USER_ENTRIES = ['python', 'module', 'standalone']
LEVEL_PROGRAM = """import sys
import easydiffraction as edi
if sys.argv[2] != 'default':
    edi.set_log_level(sys.argv[2])
project = edi.Project.load(sys.argv[1])
if sys.argv[3] == 'fit':
    project.analysis.fit(verbosity='off')
    print('MESSAGE_LEVEL_FIT_FINISHED')
"""


@pytest.fixture(scope='module')
def user_level_runs(tmp_path_factory):
    # The h00 / longitudinal-moment closed form above supplies an Info diagnostic,
    # independently of the engine's numerical fitted answer. Every run is disposable.
    root = Path(__file__).resolve().parents[3]
    candidates = [
        os.environ.get('EDI_CLI_EXECUTABLE'),
        root / 'build/ci-consumer/cli/easydiffraction',
        root / 'build/ci/cli/easydiffraction',
    ]
    binary = next((str(path) for path in candidates if path and Path(path).is_file()), None)
    folder = tmp_path_factory.mktemp('user-message-levels')
    results = {}
    for entry in USER_ENTRIES:
        for level in USER_LEVELS:
            for operation in ['fit', 'error']:
                key = entry, level, operation
                if entry == 'standalone' and binary is None:
                    results[key] = None
                    continue
                work = folder / (entry + '-' + str(level) + '-' + operation)
                work.mkdir()
                project = (
                    scan(work / 'project') if operation == 'fit' else work / 'missing-level-input'
                )
                if entry == 'python':
                    command = [
                        sys.executable,
                        '-c',
                        LEVEL_PROGRAM,
                        str(project),
                        level or 'default',
                        operation,
                    ]
                else:
                    prefix = [binary] if entry == 'standalone' else [sys.executable, '-m', 'edi']
                    command = prefix + [
                        'fit',
                        str(project),
                        '--report',
                        'human',
                        '--verbosity',
                        'full',
                    ]
                    if level is not None:
                        command += ['--log-level', level]
                result = subprocess.run(
                    command,
                    cwd=work,
                    capture_output=True,
                    text=True,
                    timeout=20,
                    check=False,
                    env={**os.environ, 'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1'},
                )
                (work / 'stdout.txt').write_text(result.stdout)
                (work / 'stderr.txt').write_text(result.stderr)
                results[key] = result, project
    return results


@pytest.mark.parametrize('entry', USER_ENTRIES)
@pytest.mark.parametrize('level', USER_LEVELS)
def test_user_message_level_filters_real_undefined_covariance_diagnostics(
    entry, level, user_level_runs
):
    receipt = user_level_runs[entry, level, 'fit']
    assert receipt is not None, 'Message-level prerequisite: build the standalone executable'
    result, project = receipt
    assert result.returncode == 0, (
        'The real message-level fit entry must complete: ' + result.stdout + result.stderr
    )
    actual = rows(project / 'analysis/results.csv')
    assert len(actual) == 2 and Path(actual[-1]['file_path']).name == SECOND, (
        'Message filtering never skips the independently constructed remaining scan frame'
    )
    assert math.isnan(float(actual[-1][MOMENT + '.uncertainty'])), (
        'The zero longitudinal derivative still has undefined covariance at every message level'
    )
    assert ('crysta.fit.su_undefined' in result.stderr) == (level in {'info', 'debug'}), (
        'Default Warning and explicit Error/Warning hide Info diagnostics; Info/Debug expose them'
    )


@pytest.mark.parametrize('entry', USER_ENTRIES)
@pytest.mark.parametrize('level', USER_LEVELS)
def test_user_message_level_never_hides_an_actual_reader_error(entry, level, user_level_runs):
    receipt = user_level_runs[entry, level, 'error']
    assert receipt is not None, 'Message-level prerequisite: build the standalone executable'
    result, project = receipt
    assert result.returncode != 0 and project.name in result.stdout + result.stderr, (
        'Each level exposes the actual reader error and its input, rather than a syntax error'
    )
