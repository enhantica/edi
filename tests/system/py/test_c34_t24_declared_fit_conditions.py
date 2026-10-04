"""declared fit conditions across paths; no generated correctness constants.

Oracles: single/scan equivalence, declared iteration bounds, absent/explicit-default
invariance, and the frozen diffraction-lib CSV header. Numerical equality is a path
invariant, not a self-generated correctness pin. Each scan comparison has a negative
control that drops the descent before the inner fit.
"""

from __future__ import annotations

import csv
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
CORPUS = Path(
    __import__('os').environ.get('EDI_CRYSTA_CORPUS_ROOT', ROOT / 'build/crysta-src/tests/fitting')
)
CLI = [sys.executable, '-m', 'edi']
SCAN = CORPUS / 'cosio-d20-scan-3f'


def declare(project, **values):
    path = project / 'analysis/analysis.edi'
    text = path.read_text()
    for key, value in values.items():
        text = re.sub(rf'(?m)^_minimizer\.{key}\s+[^\n]*\n?', '', text)
        if value is not None:
            text += f'\n_minimizer.{key} {value}\n'
    path.write_text(text)


def copy_case(tmp_path, case='cosio-d20-scan-3f', name='project', **values):
    project = tmp_path / name
    shutil.copytree(CORPUS / case / 'project', project)
    for filename in ('results.csv', 'results-provenance.csv'):
        (project / 'analysis' / filename).unlink(missing_ok=True)
    declare(project, **values)
    return project


def run_fit(project):
    result = subprocess.run(
        [*CLI, 'fit', str(project), '--report', 'machine', '--verbosity', 'full'],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, (
        ' declared conditions must execute through the public fit path: ' + result.stderr
    )
    record = dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)
    assert record.get('record') == 'fit', ' must observe a real terminal fit record'
    return record


def read_csv(path):
    assert path.is_file(), ' scan must materialize its results and per-row provenance sidecar'
    with path.open(newline='') as handle:
        reader = csv.DictReader(handle)
        return reader.fieldnames, list(reader)


def condition(row, field):
    keys = [key for key in row if key.rsplit('.', 1)[-1] == field]
    assert len(keys) == 1, ' provenance needs unique columns for file identity and each condition'
    return row[keys[0]]


def assert_provenance(rows, result_rows, expected):
    assert len(rows) == len(result_rows) == len(expected), (
        ' provenance must cover every result row exactly once'
    )
    for row, result, (descent, tolerance, limit) in zip(rows, result_rows, expected, strict=True):
        assert condition(row, 'file_path') == result['file_path'], (
            ' provenance must identify the corresponding results.csv row'
        )
        assert condition(row, 'descent') == descent, (
            ' provenance must record the descent that actually produced each row'
        )
        assert float(condition(row, 'chi_square_tolerance')) == pytest.approx(
            tolerance, rel=0, abs=0
        ), ' provenance must record each row actual chi-square tolerance'
        assert int(condition(row, 'max_iterations')) == limit, (
            ' provenance must record each row actual iteration bound'
        )


def single_from_scan(tmp_path, scan, data_file, name, **values):
    project = tmp_path / name
    shutil.copytree(scan, project)
    analysis = project / 'analysis/analysis.edi'
    analysis.write_text(
        analysis.read_text().replace('_fitting_mode.type sequential', '_fitting_mode.type single')
    )
    declare(project, **values)
    # Independent XYDATA transcription: only numeric x,y,sigma triples enter the
    # measured-data loop; no fitted quantity or code-under-test output supplies it.
    triples = []
    for line in data_file.read_text().splitlines():
        fields = line.split()
        if len(fields) == 3:
            try:
                x, _y, sigma = map(float, fields)
            except ValueError:
                continue
            # The committed template excludes [0,8] and [150,180]. Its two zero-
            # sigma observations lie outside the fitted window, so omit that window
            # rather than inventing uncertainties in the single-file transcription.
            if 8.0 < x < 150.0 and sigma > 0.0:
                triples.append(' '.join(fields))
    assert triples, ' independent single-file control needs observed XYDATA points'
    experiment = project / 'experiments/d20.edi'
    text = experiment.read_text()
    start = text.index('loop_\n_data.')
    end = text.find('loop_', start + 6)
    measured = (
        'loop_\n_data.two_theta\n_data.intensity_meas\n_data.intensity_meas_su\n'
        + '\n'.join(triples)
        + '\n\n'
    )
    experiment.write_text(text[:start] + measured + (text[end:] if end >= 0 else ''))
    return project


def assert_same_fit(row, record):
    assert int(row['fit_result.iterations']) == int(record['iterations']), (
        ' scan inner fit must use the same declared stopping conditions as a single fit'
    )
    assert float(row['fit_result.reduced_chi_square']) == pytest.approx(
        float(record['reduced_chi_square']), rel=2e-6, abs=1e-6
    ), ' scan inner fit must execute the declared descent beyond its provenance label'


@pytest.mark.parametrize('mode', ['single', 'joint'])
@pytest.mark.parametrize('descent', ['fast_descent', 'fast_descent_guarded_linear_snap'])
def test_single_and_joint_execute_declared_selection_and_budget(tmp_path, mode, descent):
    case = 'cosio-d20-s1' if mode == 'single' else 'ncaf-wish-2bank-s3'
    project = copy_case(
        tmp_path, case, descent=descent, chi_square_tolerance=1e-4, max_iterations=1
    )
    record = run_fit(project)
    assert record['descent'] == descent, (
        ' single and joint terminal records must name the declared descent'
    )
    assert 0 < int(record['iterations']) <= 1, (
        ' a single-descent fit must obey the declared iteration budget'
    )


@pytest.mark.parametrize('mode', ['single', 'joint'])
def test_tolerance_changes_real_stopping_behavior(tmp_path, mode):
    case = 'cosio-d20-s1' if mode == 'single' else 'ncaf-wish-2bank-s3'
    records = []
    for index, tolerance in enumerate((0.9, 1e-12)):
        project = copy_case(
            tmp_path,
            case,
            name=f'tolerance-{index}',
            descent='fast_descent',
            chi_square_tolerance=tolerance,
            max_iterations=20,
        )
        records.append(run_fit(project))
    assert int(records[0]['iterations']) < int(records[1]['iterations']), (
        ' declared tolerance must control single and joint stopping rules'
    )


def test_absent_conditions_equal_explicit_engine_defaults(tmp_path):
    records = []
    for name, values in [
        ('absent', {'descent': None, 'chi_square_tolerance': None, 'max_iterations': None}),
        ('explicit', {'descent': 'ladder', 'chi_square_tolerance': 1e-6, 'max_iterations': 50}),
    ]:
        project = copy_case(tmp_path, 'cosio-d20-s1', name=name, **values)
        records.append(run_fit(project))
    for key in ('descent', 'iterations', 'reduced_chi_square', 'rwp'):
        assert records[0][key] == records[1][key], (
            ' absent conditions must execute the engine defaults'
        )


def test_scan_inner_fits_and_provenance_match_declared_conditions(tmp_path):
    chosen = ('fast_descent', 1e-4, 1)
    project = copy_case(
        tmp_path, descent=chosen[0], chi_square_tolerance=chosen[1], max_iterations=chosen[2]
    )
    # Prepare independent controls BEFORE fitting mutates the scan's model.
    controls = [
        single_from_scan(tmp_path, project, data, f'single-{i}')
        for i, data in enumerate(sorted((project / 'experiments/d20_scan').glob('*.dat')))
    ]
    dropped = single_from_scan(
        tmp_path,
        project,
        min((project / 'experiments/d20_scan').glob('*.dat')),
        'dropped',
        descent='ladder',
    )
    run_fit(project)
    header, rows = read_csv(project / 'analysis/results.csv')
    reference_header, _ = read_csv(SCAN / 'diffraction-lib/project/analysis/results.csv')
    assert header == reference_header, (
        ' results.csv must retain the exact diffraction-lib column set and order'
    )
    for row, control in zip(rows, controls, strict=True):
        assert_same_fit(row, run_fit(control))
    # Exercise the omitted-descent escape using a real alternate engine run.
    with pytest.raises(AssertionError, match=' scan inner fit'):
        assert_same_fit(rows[0], run_fit(dropped))
    _, provenance = read_csv(project / 'analysis/results-provenance.csv')
    assert_provenance(provenance, rows, [chosen] * len(rows))
    corrupted = [dict(row) for row in provenance]
    key = next(key for key in corrupted[-1] if key.rsplit('.', 1)[-1] == 'descent')
    corrupted[-1][key] = 'ladder'
    with pytest.raises(AssertionError, match='descent that actually produced'):
        assert_provenance(corrupted, rows, [chosen] * len(rows))


def test_scan_tolerance_reaches_the_inner_fit(tmp_path):
    outcomes = []
    for index, tolerance in enumerate((0.9, 1e-12)):
        project = copy_case(
            tmp_path,
            name=f'scan-{index}',
            descent='fast_descent',
            chi_square_tolerance=tolerance,
            max_iterations=20,
        )
        files = sorted((project / 'experiments/d20_scan').glob('*.dat'))
        for extra in files[1:]:
            extra.unlink()
        control = single_from_scan(tmp_path, project, files[0], f'control-{index}')
        run_fit(project)
        _, rows = read_csv(project / 'analysis/results.csv')
        assert_same_fit(rows[0], run_fit(control))
        outcomes.append(int(rows[0]['fit_result.iterations']))
    assert outcomes[0] < outcomes[1], ' scan tolerance must affect actual inner stopping behavior'


def test_resume_preserves_old_provenance_and_records_new_conditions(tmp_path):
    old = ('fast_descent', 1e-4, 1)
    new = ('fast_descent_guarded_linear_snap', 0.00037, 2)
    project = copy_case(
        tmp_path, descent=old[0], chi_square_tolerance=old[1], max_iterations=old[2]
    )
    run_fit(project)
    paths = [project / 'analysis' / name for name in ('results.csv', 'results-provenance.csv')]
    before = []
    for path in paths:
        assert path.is_file(), ' resume requires paired result and provenance files'
        prefix = b''.join(path.read_bytes().splitlines(keepends=True)[:2])
        path.write_bytes(prefix)
        before.append(prefix)
    declare(project, descent=new[0], chi_square_tolerance=new[1], max_iterations=new[2])
    run_fit(project)
    for path, prefix in zip(paths, before, strict=True):
        assert path.read_bytes().startswith(prefix), (
            ' resume must never relabel or rewrite historical result/provenance rows'
        )
    _, rows = read_csv(paths[0])
    _, provenance = read_csv(paths[1])
    assert_provenance(provenance, rows, [old, new, new])
    completed = [path.read_bytes() for path in paths]
    run_fit(project)
    assert [path.read_bytes() for path in paths] == completed, (
        ' a completed resume must append neither result nor provenance rows'
    )


@pytest.mark.parametrize(
    'escape',
    ['descent', 'chi_square_tolerance', 'max_iterations', 'file_path', 'missing', 'duplicate'],
)
def test_provenance_gate_rejects_each_misattribution(escape):
    result = [{'file_path': 'first.dat'}, {'file_path': 'second.dat'}]
    expected = [('fast_descent', 0.00037, 7), ('ladder', 1e-4, 3)]
    rows = [
        {
            'file_path': item['file_path'],
            'descent': descent,
            'chi_square_tolerance': str(tol),
            'max_iterations': str(limit),
        }
        for item, (descent, tol, limit) in zip(result, expected, strict=True)
    ]
    assert_provenance(rows, result, expected)
    if escape == 'missing':
        rows.pop()
    elif escape == 'duplicate':
        rows.append(dict(rows[0]))
    else:
        rows[-1][escape] = rows[0][escape]
    with pytest.raises(AssertionError, match=' provenance'):
        assert_provenance(rows, result, expected)


def test_guarded_scan_records_its_observed_outcomes_without_assuming_convergence(tmp_path):
    #  is out of scope: measure the guarded flow's actual bailout, never
    # manufacture a convergence requirement or conceal failed scan rows.
    chosen = ('fast_descent_guarded_linear_snap', 1e-4, 1000)
    project = copy_case(
        tmp_path, descent=chosen[0], chi_square_tolerance=chosen[1], max_iterations=chosen[2]
    )
    run_fit(project)
    _, rows = read_csv(project / 'analysis/results.csv')
    _, provenance = read_csv(project / 'analysis/results-provenance.csv')
    assert len(rows) == 3, ' guarded scan must record every input, including any  bailout'
    assert_provenance(provenance, rows, [chosen] * len(rows))
    observations = [
        (
            Path(row['file_path']).name,
            row['fit_result.success'],
            row['fit_result.iterations'],
            row['fit_result.reduced_chi_square'],
        )
        for row in rows
    ]
    print(' guarded-scan observations (file, success, iterations, chi-square):', observations)
