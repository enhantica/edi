"""Background-only observations have a closed-form block-arrow fit and covariance."""

from pathlib import Path

import edi as engine
import numpy as np
import pytest

from tests.fixtures.parametric_series import cases
from tests.fixtures.report_units.iucr_reference import rounded_pair


@pytest.mark.parametrize('fixed', [False, True])
def test_shared_linear_fit_recovers_truth_and_undamped_covariance(tmp_path, fixed):
    root = cases.scan(tmp_path / 'series', fixed=fixed)
    project = engine.Project.load(root)
    project.analysis.fit()
    assert (root / 'analysis/results.csv').is_file(), (
        'A parametric fit publishes one row per admitted scan point'
    )
    rows = cases.rows(root)
    assert len(rows) == 3, 'The authored three-point scan fits every file'
    covariance = cases.linear_covariance(fixed=fixed)
    for index, row in enumerate(rows):
        left = (
            project.experiments['zeta'].background[0].intensity.value
            if fixed
            else float(row['zeta.background.1.intensity'])
        )
        right = float(row['zeta.background.2.intensity'])
        assert left == pytest.approx(
            3.25 if fixed else rounded_pair(3.25, np.sqrt(covariance[0, 0]), 'iucr_99')[0],
            abs=1e-8,
        ), 'A shared linear term recovers the independently authored intercept'
        assert right == pytest.approx(
            rounded_pair(
                (7.75, 9.25, 6.5)[index],
                np.sqrt(covariance[index if fixed else index + 1, index if fixed else index + 1]),
                'iucr_99',
            )[0],
            abs=1e-8,
        ), 'An unshared endpoint retains its own analytic optimum'
        column = index if fixed else index + 1
        assert float(row['zeta.background.2.intensity.uncertainty']) == pytest.approx(
            rounded_pair(0, np.sqrt(covariance[column, column]), 'iucr_99')[1], rel=1e-10
        ), 'Local uncertainties use the undamped joint inverse and global reduced chi square'
        if not fixed:
            assert float(row['zeta.background.1.intensity.uncertainty']) == pytest.approx(
                rounded_pair(0, np.sqrt(covariance[0, 0]), 'iucr_99')[1], rel=1e-10
            ), 'Every shared follower receives the analytic leader uncertainty'
        assert row['fit_result.success'] == 'True', (
            'Every well-conditioned linear point must finish successfully'
        )


def test_nothing_shared_matches_independent_with_global_uncertainty_scale(tmp_path):
    outputs = []
    for mode in ('independent', 'parametric'):
        root = cases.scan(tmp_path / mode, shared=False, mode=mode)
        engine.Project.load(root).analysis.fit()
        assert (root / 'analysis/results.csv').is_file(), (
            'Both modes publish their complete scan results'
        )
        outputs.append(cases.rows(root))
    independent, parametric = outputs
    assert len(independent) == len(parametric) == 3, (
        'Both modes admit the same three observations files'
    )
    covariance = cases.linear_covariance(shared=False)
    for index, (old, new) in enumerate(zip(independent, parametric, strict=True)):
        for endpoint in ('1', '2'):
            name = f'zeta.background.{endpoint}.intensity'
            assert float(new[name]) == pytest.approx(float(old[name]), abs=1e-8), (
                'Independent block descent preserves each point optimum'
            )
            column = 2 * index + int(endpoint) - 1
            assert float(new[name + '.uncertainty']) == pytest.approx(
                rounded_pair(0, np.sqrt(covariance[column, column]), 'iucr_99')[1], rel=1e-10
            ), 'No-sharing uncertainties use independently counted global degrees of freedom'
        assert new['fit_result.termination'] == old['fit_result.termination'], (
            'Each independent block retains its own termination'
        )


def test_repeated_fit_never_turns_results_into_start_rows(tmp_path):
    root = cases.scan(tmp_path / 'series')
    for _ in range(2):
        project = engine.Project.load(root)
        project.analysis.fit()
        assert (root / 'analysis/results.csv').is_file(), (
            'Each parametric invocation publishes a complete result'
        )
        project.save_as(tmp_path / 'saved')
        text = (tmp_path / 'saved/analysis/analysis.edi').read_text()
        assert cases.START_TAGS[0] not in text, (
            'A fit never silently promotes its output into explicit point starts'
        )


def test_independent_control_matches_the_authored_linear_reference(tmp_path):
    root = cases.scan(tmp_path / 'control', shared=False, mode='independent')
    engine.Project.load(root).analysis.fit()
    rows = cases.rows(root)
    assert len(rows) == 3, 'The Independent control must fit every authored data file'
    design = np.column_stack((1 - np.linspace(0, 1, 5), np.linspace(0, 1, 5)))
    inverse = np.linalg.inv(design.T @ design)
    for index, row in enumerate(rows):
        covariance = inverse * (14 * 0.03**2 * (index + 1) ** 2 / 3)
        for endpoint, truth in enumerate((3.25, (7.75, 9.25, 6.5)[index])):
            name = f'zeta.background.{endpoint + 1}.intensity'
            value, uncertainty = rounded_pair(
                truth, np.sqrt(covariance[endpoint, endpoint]), 'iucr_99'
            )
            assert float(row[name]) == pytest.approx(value, abs=1e-8), (
                'The control recovers the authored optimum at the file precision'
            )
            assert float(row[name + '.uncertainty']) == pytest.approx(uncertainty, rel=1e-10), (
                'The control covariance uses the authored residual and parameter count'
            )


def test_cancel_preserves_the_prior_published_generation(tmp_path):
    root = cases.scan(tmp_path / 'series', mode='independent')
    engine.Project.load(root).analysis.fit()
    analysis = root / 'analysis/analysis.edi'
    analysis.write_text(
        analysis.read_text().replace(
            '_fitting_mode.type independent', '_fitting_mode.type parametric'
        )
    )
    prior = {
        'results.csv': (root / 'analysis/results.csv').read_bytes(),
        'scan-notes.csv': b'prior notes generation\n',
    }
    for name, contents in prior.items():
        (root / 'analysis' / name).write_bytes(contents)
    project = engine.Project.load(root)
    called = []

    def cancel():
        called.append(True)
        return True

    project.analysis.fit(should_cancel=cancel)
    assert called, 'Cancellation must reach the actual parametric solve boundary'
    assert {name: (root / 'analysis' / name).read_bytes() for name in prior} == prior, (
        'A cancelled fit preserves every prior result file byte'
    )


def test_iteration_delivery_has_one_series_record_per_round(tmp_path):
    root = cases.scan(tmp_path / 'series', shared=False)
    project = engine.Project.load(root)
    iterations = []

    def observe(record):
        iterations.append(record.iteration)
        if (root / 'analysis/results.csv').exists():
            assert len(cases.rows(root)) == 3, (
                'An iterate observer can only see a whole published generation'
            )

    published = []

    def read_back(record):
        rows = cases.rows(root)
        assert [Path(row['file_path']).name for row in rows] == ['p0.xy', 'p1.xy', 'p2.xy'], (
            'The first completion already exposes the complete published generation'
        )
        row = rows[len(published)]
        assert Path(record.file_name).name == Path(row['file_path']).name, (
            'The reported completion identifies its own row in the published CSV'
        )
        assert record.iterations == int(row['fit_result.iterations']), (
            'The completion retains its published iteration count'
        )
        assert record.reduced_chi_square == pytest.approx(
            float(row['fit_result.reduced_chi_square'])
        ), 'The completion retains its published agreement'
        published.append(Path(record.file_name).name)

    project.analysis.fit(on_iteration=observe, on_file_complete=read_back)
    assert published == ['p0.xy', 'p1.xy', 'p2.xy'], (
        'A subscriber receives every published row in scan order'
    )
    assert iterations, 'The real parametric driver delivers iteration progress'
    assert iterations == sorted(set(iterations)), (
        'Independent blocks deliver one increasing series iteration each round'
    )
    assert len(cases.rows(root)) == 3, 'Final publication retains every admitted scan point'


@pytest.mark.parametrize('fixed', [False, True])
def test_shared_scale_and_local_background_follow_the_analytic_fit(tmp_path, fixed):
    root = tmp_path / 'scale'
    covariance = cases.scale_scan(root, fixed=fixed)
    project = engine.Project.load(root)
    project.save_as(tmp_path / 'reloaded')
    root = tmp_path / 'reloaded'
    project = engine.Project.load(root)
    project.analysis.fit()
    rows = cases.rows(root)
    assert len(rows) == 3, 'A shared scale fit publishes every independently authored point'
    for index, row in enumerate(rows):
        name = 'zeta.linked_structure.phase.scale'
        actual = (
            project.experiments['zeta'].linked_structures['phase'].scale.value
            if fixed
            else float(row[name])
        )
        expected = 2.5 if fixed else rounded_pair(2.5, np.sqrt(covariance[0, 0]), 'iucr_99')[0]
        assert actual == pytest.approx(expected, abs=1e-8), (
            'Shared scale retains the authored amplitude after reload and solve'
        )
        if not fixed:
            assert float(row[name + '.uncertainty']) == pytest.approx(
                rounded_pair(0, np.sqrt(covariance[0, 0]), 'iucr_99')[1], rel=1e-8
            ), 'Shared scale uncertainty matches the independent design matrix'
        for endpoint, truth in enumerate((3.25 + index, 8.75 - index)):
            column = 2 * index + endpoint + (0 if fixed else 1)
            value, uncertainty = rounded_pair(
                truth, np.sqrt(covariance[column, column]), 'iucr_99'
            )
            name = f'zeta.background.{endpoint + 1}.intensity'
            assert float(row[name]) == pytest.approx(value, abs=1e-8), (
                'Sharing scale retains both local background degrees of freedom'
            )
            assert float(row[name + '.uncertainty']) == pytest.approx(uncertainty, rel=1e-8), (
                'Local uncertainty includes shared-scale coupling and global degrees of freedom'
            )
