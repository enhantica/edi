"""Small seeded series on committed external NCAF measurements."""

import shutil
from pathlib import Path

import edi as engine
import pytest

from tests.fixtures.joint_series import cases, ncaf, oracle, prepare_seeded


def check_seeded_fit(tmp_path, points, descent, *, small=False, prepared=None):
    if prepared is None:
        root = ncaf.prepare(tmp_path / 'series', points=points, descent=descent, small=small)
        project = engine.Project.load(root)
        expected_scales = ncaf.linear_scales(project) if small else None
    else:
        root = tmp_path / 'series'
        shutil.copytree(prepared[0], root)
        analysis = root / 'analysis/analysis.edi'
        analysis.write_text(
            analysis.read_text().replace(
                '_minimizer.descent fast_descent', '_minimizer.descent ' + descent
            )
        )
        project = engine.Project.load(root)
        expected_scales = ncaf.linear_scales(project, prepared[1])
    records = []
    project.analysis.fit(on_file_complete=records.append)
    point_file, bank_file = (
        root / 'analysis/results.csv',
        root / 'analysis/results_experiments.csv',
    )
    assert point_file.is_file(), 'A seeded series must write the point results file'
    assert bank_file.is_file(), 'A seeded series must write the experiment results file'
    _, rows = cases.csv_rows(point_file)
    _, banks = cases.csv_rows(bank_file)
    assert [row['point'] for row in rows] == [f'P{i:04d}' for i in range(points)], (
        'Every copied measurement must keep its own point identity'
    )
    assert len(banks) == points * (2 if small else 5), (
        'Every NCAF point must retain every selected experiment'
    )
    for row in rows:
        oracle.outcome(row)
        for name, reference in ({} if expected_scales else ncaf.atom_references()).items():
            column = 'ncaf.atom_site.' + name
            assert float(row[column]) == pytest.approx(
                reference['value'], abs=reference['tol_abs']
            ), 'Seeded NCAF atoms must remain within the committed FullProf standard uncertainty'
        assert row['fit_result.descent'] == descent, (
            'Each point must record the explicit descent instead of the default probe'
        )
        assert float(row['fit_result.chi_square_tolerance']) == pytest.approx(0.0001), (
            'The seeded comparison must preserve the declared chi-square change threshold'
        )
    if expected_scales is not None:
        ncaf.fixed_atoms(project)
        for bank, (expected, sigma) in expected_scales.items():
            fitted = project.experiments[bank].linked_structures['ncaf'].scale
            assert abs(fitted.value - expected) <= 5 * sigma, (
                'Live bank scales must recover the weighted linear optimum within five s.u.'
            )
            oracle.numeric_error(fitted.uncertainty, sigma)
            for row in banks:
                if row['experiment'] == bank:
                    # Repeated observations have the same optimum; allow fit accuracy separately
                    # from file precision, then check each file against its own live fitted scale.
                    assert (
                        abs(float(row['linked_structure.ncaf.scale']) - expected) <= 5 * sigma
                    ), 'Every bank row must recover the independent weighted scale optimum'
                    oracle.series_cells(
                        row, 'linked_structure.ncaf.scale', fitted.value, fitted.uncertainty
                    )
    assert len(records) == points, 'One callback must describe each completed joint point'
    assert all(row.get('fit_result.termination') for row in rows), (
        'The seeded mode comparison must expose the termination reason of every point'
    )
    return rows


@pytest.fixture(scope='module')
def seeded_input():
    return prepare_seeded.prepared(Path(__file__).resolve().parents[3], engine)


@pytest.mark.parametrize('descent', ['fast_descent', 'ladder'])
def test_small_fullprof_seeded_series(tmp_path, descent, seeded_input):
    check_seeded_fit(tmp_path, 1, descent, small=True, prepared=seeded_input)
