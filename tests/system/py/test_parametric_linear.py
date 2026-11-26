"""Background-only observations have a closed-form block-arrow fit and covariance."""

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

    project.analysis.fit(on_iteration=observe)
    assert iterations, 'The real parametric driver delivers iteration progress'
    assert iterations == sorted(set(iterations)), (
        'Independent blocks deliver one increasing series iteration each round'
    )
    assert len(cases.rows(root)) == 3, 'Final publication retains every admitted scan point'
