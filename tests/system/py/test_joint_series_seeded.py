"""Small seeded series on committed external NCAF measurements."""

import edi as engine
import pytest

from tests.fixtures.joint_series import cases, ncaf, oracle


def check_seeded_fit(tmp_path, points, descent):
    root = ncaf.prepare(tmp_path / 'series', points=points, descent=descent)
    records = []
    engine.Project.load(root).analysis.fit(on_file_complete=records.append)
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
    assert len(banks) == points * 5, 'Every NCAF point must retain all five experiments'
    for row in rows:
        oracle.outcome(row)
        for name, reference in ncaf.atom_references().items():
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
    assert len(records) == points, 'One callback must describe each completed joint point'
    assert all(row.get('fit_result.termination') for row in rows), (
        'The seeded mode comparison must expose the termination reason of every point'
    )
    return rows


@pytest.mark.parametrize('descent', ['fast_descent', 'ladder'])
def test_small_fullprof_seeded_series(tmp_path, descent):
    check_seeded_fit(tmp_path, 2, descent)
