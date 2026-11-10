"""Fit and persistence checks against a frozen external covariance projection."""

from __future__ import annotations

import csv
import json
import math
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import edi
import pytest

from tests.fixtures.report_units.iucr_reference import rounded_correlation, rounded_record

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / 'tests/fixtures/correlations'
REFERENCE = json.loads((FIXTURE / 'reference.json').read_text())
PREFIX = '_fit_parameter_correlation.'


def correlations(text):
    lines = text.splitlines()
    start = next((i for i, line in enumerate(lines) if line.startswith(PREFIX)), None)
    if start is None:
        return []
    headers = []
    while start < len(lines) and lines[start].startswith(PREFIX):
        headers.append(lines[start][len(PREFIX) :])
        start += 1
    rows = []
    for line in lines[start:]:
        if not line.strip():
            continue
        if line.startswith(('_', 'loop_', 'data_')):
            break
        fields = shlex.split(line)
        assert len(fields) == len(headers), (
            'Every saved correlation row must match its declared loop columns'
        )
        rows.append(dict(zip(headers, fields, strict=True)))
    return rows


def saved_analysis(project, destination):
    project.save_as(destination)
    return (destination / 'analysis/analysis.edi').read_text()


def check_pairs(text, count):
    expected = REFERENCE['cases'][str(count)]['rows']
    rows = correlations(text)
    assert len(rows) == len(expected), (
        'The latest fit must store each distinct free-parameter pair exactly once'
    )
    pairs = {
        tuple(sorted((row['parameter_unique_name_i'], row['parameter_unique_name_j']))): float(
            row['correlation']
        )
        for row in rows
    }
    assert len(pairs) == len(rows), (
        'The correlation loop must contain no duplicate or diagonal pairs'
    )
    for row in expected:
        key = tuple(sorted((row['parameter_unique_name_i'], row['parameter_unique_name_j'])))
        assert key in pairs, (
            'Stored correlation labels must identify the independently selected fit parameters'
        )
        assert math.isfinite(pairs[key]), 'Every persisted correlation coefficient must be finite'
        assert pairs[key] == pytest.approx(
            float(rounded_correlation(row['correlation'])), abs=1e-14
        ), (
            'Saved polynomial covariance equals the independent IUCr-rounded external reference; '
            f'pair={key}, actual={pairs[key]}, raw reference={row["correlation"]}'
        )


@pytest.mark.parametrize('count', [1, 2, 3])
def test_polynomial_fit_stores_external_correlations(tmp_path, count):
    project = edi.Project.load(FIXTURE / f'polynomial-{count}')
    assert len(project.free_parameters) == count, (
        'The shared polynomial example must expose the requested free set'
    )
    project.analysis.fit()
    check_pairs(saved_analysis(project, tmp_path / 'fitted'), count)


@pytest.mark.parametrize('count', [1, 2, 3])
def test_python_fit_result_exposes_external_correlations(count):
    project = edi.Project.load(FIXTURE / f'polynomial-{count}')
    result = project.analysis.fit()
    assert hasattr(result, 'correlations'), (
        'The returned Python fit result must expose its parameter correlations'
    )
    rows = result.correlations
    expected = REFERENCE['cases'][str(count)]['rows']
    assert len(rows) == len(expected), (
        'Python must expose every distinct free-parameter pair and no diagonal or stale pairs'
    )
    pairs = {
        tuple(sorted((row.parameter_unique_name_i, row.parameter_unique_name_j))): row.correlation
        for row in rows
    }
    assert len(pairs) == len(rows), 'Python fit correlations must contain no duplicate pairs'
    for row in expected:
        key = tuple(sorted((row['parameter_unique_name_i'], row['parameter_unique_name_j'])))
        assert key in pairs, 'Python correlation labels must identify the external free set'
        assert math.isfinite(pairs[key]), 'Python correlation coefficients must be finite'
        assert pairs[key] == pytest.approx(row['correlation'], abs=2e-4), (
            'Python fit-result correlations must match diffraction-lib normalized normal equations'
        )


@pytest.mark.parametrize('count', [1, 2, 3])
def test_cli_machine_report_names_external_correlation_count(tmp_path, count):
    source = tmp_path / 'input'
    shutil.copytree(FIXTURE / f'polynomial-{count}', source)
    result = subprocess.run(
        [
            sys.executable,
            '-m',
            'edi',
            'fit',
            str(source),
            '--report',
            'machine',
            '--verbosity',
            'compact',
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, 'The CLI must fit the independent polynomial input successfully'
    assert 'record=fit' in result.stdout, 'The CLI must emit a terminal machine fit record'
    # The decision requires a named count, but does not prescribe its key spelling.
    counts = re.findall(
        r'^(?:x-edi\.)?(?:n_correlations|correlation_count|correlations)=(\d+)$',
        result.stdout,
        re.MULTILINE,
    )
    assert len(counts) == 1, 'The CLI machine fit record must name its correlation count once'
    assert int(counts[0]) == len(REFERENCE['cases'][str(count)]['rows']), (
        'The CLI correlation count must match the same external pairs as the core and Python'
    )


def test_external_loop_survives_load_and_save_byte_for_byte(tmp_path):
    project = edi.Project.load(FIXTURE / 'polynomial-3')
    source = tmp_path / 'input'
    saved_analysis(project, source)
    path = source / 'analysis/analysis.edi'
    loop = (FIXTURE / 'loop-3.edi').read_text()
    path.write_text(path.read_text().rstrip() + '\n\n' + loop)
    loaded = edi.Project.load(source)
    once = saved_analysis(loaded, tmp_path / 'once')
    assert rounded_record(loop.encode()).decode() in once, (
        'Before full-precision coefficient bytes; after IUCr coefficients with every external '
        'row identity and endpoint byte retained'
    )
    twice = saved_analysis(edi.Project.load(tmp_path / 'once'), tmp_path / 'twice')
    assert once == twice, (
        'A second unchanged save must preserve all analysis bytes including correlations'
    )


def test_unfitted_analysis_stays_byte_identical(tmp_path):
    project = edi.Project.load(FIXTURE / 'polynomial-2')
    once = saved_analysis(project, tmp_path / 'once')
    twice = saved_analysis(edi.Project.load(tmp_path / 'once'), tmp_path / 'twice')
    assert PREFIX not in once, 'A project without a fit must not invent a correlation loop'
    assert once == twice, (
        'An unchanged project without correlations must retain every analysis byte'
    )


def test_fixed_parameter_preserves_history_and_refit_replaces_pairs(tmp_path):
    project = edi.Project.load(FIXTURE / 'polynomial-3')
    project.analysis.fit()
    check_pairs(saved_analysis(project, tmp_path / 'first'), 3)
    project.experiment.background_terms[2].coef.free = False
    check_pairs(saved_analysis(project, tmp_path / 'fixed'), 3)
    loaded = edi.Project.load(tmp_path / 'fixed')
    loaded.analysis.fit()
    check_pairs(saved_analysis(loaded, tmp_path / 'refitted'), 2)
    loaded.experiment.background_terms[1].coef.free = False
    loaded.analysis.fit()
    assert not correlations(saved_analysis(loaded, tmp_path / 'single')), (
        'A one-parameter refit must clear every stale pair from the earlier many-parameter fit'
    )


def test_external_loop_does_not_change_unrelated_project_files(tmp_path):
    source = tmp_path / 'source'
    saved_analysis(edi.Project.load(FIXTURE / 'polynomial-3'), source)
    (source / 'analysis/analysis.edi').write_text(
        (source / 'analysis/analysis.edi').read_text().rstrip()
        + '\n\n'
        + (FIXTURE / 'loop-3.edi').read_text()
    )
    saved = tmp_path / 'saved'
    edi.Project.load(source).save_as(saved)
    for folder in ('structures', 'experiments'):
        expected = {
            p.relative_to(source): p.read_bytes()
            for p in (source / folder).rglob('*')
            if p.is_file()
        }
        actual = {
            p.relative_to(saved): p.read_bytes()
            for p in (saved / folder).rglob('*')
            if p.is_file()
        }
        assert actual == expected, (
            'Correlation persistence must preserve every structure and experiment byte'
        )


def test_empty_free_set_never_invents_pairs(tmp_path):
    source = tmp_path / 'empty'
    shutil.copytree(FIXTURE / 'polynomial-1', source)
    path = source / 'experiments/bank.edi'
    path.write_text(path.read_text().replace('4()', '4'))
    project = edi.Project.load(source)
    assert not project.free_parameters, 'The empty-control input must have no free parameters'
    assert not correlations(saved_analysis(project, tmp_path / 'saved')), (
        'An empty free set must have no fabricated correlations'
    )


@pytest.mark.parametrize('mode', ['sequential', 'independent'])
@pytest.mark.parametrize(
    'template',
    [None, '01.xy', '02.xy'],
    ids=['first-by-default', 'declared-first', 'declared-later'],
)
def test_scan_persists_effective_templates_external_pairs_on_save_and_reload(
    tmp_path, mode, template
):
    reference = json.loads((FIXTURE / 'scan-reference.json').read_text())
    source = tmp_path / 'input'
    shutil.copytree(FIXTURE / f'scan-{mode}', source)
    # Before: only a declared template was persisted. After: its absence selects file one.
    analysis = source / 'analysis/analysis.edi'
    if template is not None:
        analysis.write_text(
            analysis.read_text() + '\n_sequential_fit.template_file ' + template + '\n'
        )
    effective = template or reference['cases'][0]['file']
    project = edi.Project.load(source)
    project.analysis.fit()
    assert (source / 'analysis/results.csv').is_file(), (
        'The per-experiment correlation witness must execute a real scan'
    )
    with (source / 'analysis/results.csv').open() as stream:
        fitted = list(csv.DictReader(stream))
    assert [Path(row['file_path']).name for row in fitted] == [
        case['file'] for case in reference['cases']
    ], 'The covariance witness must actually fit both independently authored experiments'
    assert all(row['fit_result.success'].casefold() == 'true' for row in fitted), (
        'Both experiment fits must succeed before claiming their covariance reference'
    )
    once = saved_analysis(project, tmp_path / 'once')
    # Audit the complete saved loop; the app actor separately checks live dataset selection.
    lines = once.splitlines(keepends=True)
    starts = [i for i, line in enumerate(lines) if line.startswith(PREFIX + 'id')]
    rows = [row for i in starts for row in correlations(''.join(lines[i:]))]
    expected = next(case['rows'] for case in reference['cases'] if case['file'] == effective)
    assert len(rows) == len(expected), (
        'Sequential and independent saves retain the declared template pairs, '
        'or the first dataset pairs when none is declared'
    )
    assert all(Path(row.get('file_path', '')).name == effective for row in rows), (
        'Each saved pair keeps the effective template file identity, '
        'including the first-file fallback'
    )
    for pair in (('base', 'ramp'), ('base', 'curve'), ('ramp', 'curve')):

        def identity(row):
            return tuple(
                sorted(
                    row[key].split('.')[-2]
                    for key in ('parameter_unique_name_i', 'parameter_unique_name_j')
                )
            )

        target = tuple(sorted(pair))
        actual = sorted(float(row['correlation']) for row in rows if identity(row) == target)
        truth = sorted(
            float(rounded_correlation(row['correlation']))
            for row in expected
            if identity(row) == target
        )
        assert actual == pytest.approx(truth, abs=1e-14), (
            'The saved template must retain its independently normalized covariance, '
            f'including IUCr significant figures; pair={target}, actual={actual}, expected={truth}'
        )
    twice = saved_analysis(edi.Project.load(tmp_path / 'once'), tmp_path / 'twice')
    assert once == twice, (
        'Save and load must preserve the template correlation and its association byte-for-byte'
    )
