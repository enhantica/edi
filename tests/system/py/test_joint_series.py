"""A point owns a joint fit and two consistent, append-only result tables."""

import shutil

import edi as engine
import numpy as np
import pytest

from tests.fixtures.joint_series import cases, oracle, persistence


def result_tables(directory):
    point_file = directory / 'analysis/results.csv'
    bank_file = directory / 'analysis/results_experiments.csv'
    assert point_file.is_file(), 'A joint series must produce its point table'
    assert bank_file.is_file(), 'A joint series must produce its experiment table'
    return cases.csv_rows(point_file), cases.csv_rows(bank_file)


@pytest.mark.parametrize('mode', ['sequential', 'independent'])
def test_known_cells_and_unequal_bank_scales_recover_at_their_point(tmp_path, mode):
    root = cases.generated_series(tmp_path / 'series', engine, mode=mode)
    engine.Project.load(root).analysis.fit()
    (header, points), (bank_header, banks) = result_tables(root)
    assert [row['point'] for row in points] == list(cases.POINTS), (
        'Point identities must survive grouping as exact nonnumeric keys'
    )
    assert len(banks) == 6, 'Three points and two experiments require six experiment rows'
    assert 'phase.cell.length_a' in header, 'The shared cell belongs in the point table'
    assert 'linked_structure.phase.scale' in bank_header, (
        'An experiment parameter uses its path without the datablock prefix'
    )
    assert not any(name.startswith(('alpha.', 'zeta.')) for name in header), (
        'The point table must not expand into one parameter column per experiment'
    )
    for index, row in enumerate(points):
        assert float(row['phase.cell.length_a']) == pytest.approx(cases.CELLS[index], abs=0.002), (
            'The fitted shared cell must recover the authored cell of its own point'
        )
        assert abs(float(row['phase.cell.length_a']) - cases.CELLS[index]) <= 5 * float(
            row['phase.cell.length_a.uncertainty']
        ), 'The recovered cell must agree with its generating value within five reported s.u.'
        assert row['fit_result.success'] == 'True', (
            'Every known-input point must finish successfully'
        )
        selected = [bank for bank in banks if bank['point'] == row['point']]
        assert [bank['experiment'] for bank in selected] == list(cases.BANKS), (
            'Experiment rows follow project order rather than input filenames'
        )
        for bank_index, bank in enumerate(selected):
            assert float(bank['linked_structure.phase.scale']) == pytest.approx(
                cases.SCALES[index][bank_index], rel=0.015
            ), 'The per-experiment scale must recover its own authored value without carry-over'
            assert float(bank['linked_structure.phase.scale.uncertainty']) > 0, (
                'Every fitted scale must retain a positive uncertainty from the joint covariance'
            )
            assert abs(
                float(bank['linked_structure.phase.scale']) - cases.SCALES[index][bank_index]
            ) <= 5 * float(bank['linked_structure.phase.scale.uncertainty']), (
                'Each bank scale must recover its generating value within five reported s.u.'
            )
            physical = root / bank['file_path']
            assert physical.name == f'{row["point"]}_{("b5", "b1")[bank_index]}.xy', (
                'A result row must name the pattern actually assigned to that experiment and point'
            )
            assert int(bank['file_size']) == physical.stat().st_size, (
                'Each experiment receipt must record the fitted file size'
            )
            assert int(bank['file_modified']) == physical.stat().st_mtime_ns, (
                'Modification times use whole nanoseconds since the Unix epoch'
            )


def test_completed_series_refits_its_points_then_admits_new_data(tmp_path):
    root = cases.generated_series(tmp_path / 'series', engine)
    engine.Project.load(root).analysis.fit()
    result_tables(root)
    completed = []
    engine.Project.load(root).analysis.fit(on_file_complete=completed.append)
    assert len(completed) == len(cases.POINTS), (
        'A completed joint series starts a fresh fit of every point'
    )
    for suffix in ('b5', 'b1'):
        shutil.copyfile(root / f'scan/T500K_{suffix}.xy', root / f'scan/T900K_{suffix}.xy')
    engine.Project.load(root).analysis.fit()
    (_, points), (_, banks) = result_tables(root)
    assert [row['point'] for row in points] == [*cases.POINTS, 'T900K'], (
        'The next scan admits the new point and publishes each point once'
    )
    assert len(banks) == 8, 'The new scan publishes two experiment rows per point'


def test_uncommitted_complete_experiment_rows_are_removed_before_resume(tmp_path):
    root = cases.generated_series(tmp_path / 'series', engine)
    engine.Project.load(root).analysis.fit()
    (header, points), (_, original_banks) = result_tables(root)
    original_points = points
    cases.write_rows(root / 'analysis/results.csv', header, points[:-1])
    engine.Project.load(root).analysis.fit()
    (_, points), (_, banks) = result_tables(root)
    assert points == original_points, (
        'Owner a2fe1e722 requires resumed and uninterrupted point results to agree exactly'
    )
    assert banks == original_banks, (
        'Owner a2fe1e722 requires resumed experiment results to equal uninterrupted results'
    )
    assert len(points) == 3, 'Recovering an orphan tail must finish the three points once'
    assert len(banks) == 6, 'Recovering an orphan tail must retain six experiment rows'
    assert [(r['point'], r['experiment']) for r in banks] == [
        (point, bank) for point in cases.POINTS for bank in cases.BANKS
    ], 'The recovered tables must contain one complete experiment group per committed point'


@pytest.mark.parametrize(
    'damage',
    [
        'point-tail',
        'experiment-tail',
        'duplicate-point',
        'missing-experiment',
        'foreign-experiment',
        'foreign-header',
    ],
)
def test_damaged_join_refuses_before_changing_either_results_file(tmp_path, damage):
    root = cases.generated_series(tmp_path / 'series', engine)
    engine.Project.load(root).analysis.fit()
    (header, points), (bank_header, banks) = result_tables(root)
    point_path, bank_path = (
        root / 'analysis/results.csv',
        root / 'analysis/results_experiments.csv',
    )
    if damage.endswith('tail'):
        target = point_path if damage == 'point-tail' else bank_path
        target.write_bytes(target.read_bytes()[:-5])
    elif damage == 'duplicate-point':
        cases.write_rows(point_path, header, [*points, points[0]])
    elif damage == 'missing-experiment':
        cases.write_rows(bank_path, bank_header, banks[:-1])
    elif damage == 'foreign-experiment':
        banks[0]['experiment'] = 'foreign'
        cases.write_rows(bank_path, bank_header, banks)
    else:
        bank_path.write_text(bank_path.read_text().replace('experiment,', 'foreign,', 1))
    before = point_path.read_bytes(), bank_path.read_bytes()
    with pytest.raises((ValueError, RuntimeError), match=r'results|experiment|point|header|tail'):
        engine.Project.load(root).analysis.fit()
    assert (point_path.read_bytes(), bank_path.read_bytes()) == before, (
        'A foreign, torn or inconsistent pair must be refused before any rewrite or append'
    )


@pytest.mark.parametrize('damage', ['malformed', 'missing', 'zero-signal'])
def test_bad_point_is_listed_and_later_points_are_fitted(tmp_path, damage):
    root = cases.generated_series(
        tmp_path / 'series', engine, keys=('0007', '07', 'T300K', 'T500K', 'T900K')
    )
    bad = root / 'scan/T300K_b1.xy'
    if damage == 'missing':
        bad.unlink()
    elif damage == 'malformed':
        bad.write_text('unreadable numeric columns\n')
    else:
        bad.write_text(''.join(f'{x} 0 1\n' for x in cases.GRID))
    engine.Project.load(root).analysis.fit()
    (_, points), (_, banks) = result_tables(root)
    assert [row['point'] for row in points] == ['0007', '07', 'T500K', 'T900K'], (
        'Skip the bad point while keeping exact point keys and fitting later points'
    )
    assert len(banks) == 8, 'A skipped joint point must contribute no experiment rows'
    _, notes = cases.csv_rows(root / 'analysis/scan-notes.csv')
    relevant = [row for row in notes if 'T300K' in row['file_path']]
    assert relevant, 'The skipped point must have a durable note naming its input file'
    assert all(row['refusal'] for row in relevant), 'Every skipped-point note must name a cause'


@pytest.mark.parametrize(
    'declaration',
    ['both-forms', 'missing-bank', 'duplicate-bank', 'foreign-bank', 'no-star', 'two-stars'],
)
def test_invalid_group_declaration_is_scan_level(tmp_path, declaration):
    root = cases.generated_series(tmp_path / 'series', engine)
    analysis = root / 'analysis/analysis.edi'
    text = analysis.read_text()
    changes = {
        'both-forms': text + '\n_sequential_fit.file_pattern "*.xy"\n',
        'missing-bank': text.replace('alpha "*_b1.xy"\n', ''),
        'duplicate-bank': text + 'alpha "*_b1.xy"\n',
        'foreign-bank': text.replace('alpha "*_b1.xy"', 'foreign "*_b1.xy"'),
        'no-star': text.replace('*_b1.xy', 'T300K_b1.xy'),
        'two-stars': text.replace('*_b1.xy', '*_b*.xy'),
    }
    analysis.write_text(changes[declaration])
    with pytest.raises(
        (ValueError, RuntimeError),
        match=r'file_pattern|_sequential_fit_experiment|unknown experiment|missing.*experiment|'
        r'duplicate.*experiment|experiment.*twice',
    ):
        engine.Project.load(root).analysis.fit()
    assert not (root / 'analysis/results.csv').exists(), (
        'Invalid shared configuration must stop the scan before fitting any point'
    )
    assert not (root / 'analysis/scan-notes.csv').exists(), (
        'An invalid shared declaration must not be disguised as a per-point skip'
    )


def test_single_experiment_keeps_legacy_file_and_refuses_foreign_sidecar(tmp_path):
    root = cases.generated_series(tmp_path / 'single', engine, single=True)
    engine.Project.load(root).analysis.fit()
    header, rows = cases.csv_rows(root / 'analysis/results.csv')
    assert header[0] == 'file_path', 'One experiment must retain the legacy file-based header'
    assert len(rows) == 3, 'One experiment must retain one legacy row per file'
    sidecar = root / 'analysis/results_experiments.csv'
    assert not sidecar.exists(), 'One experiment must write no second results file'
    sidecar.write_text('point,experiment\nT050K,zeta\n')
    before = (root / 'analysis/results.csv').read_bytes(), sidecar.read_bytes()
    with pytest.raises(
        (ValueError, RuntimeError), match=r'results_experiments|foreign|experiment'
    ):
        engine.Project.load(root).analysis.fit()
    assert ((root / 'analysis/results.csv').read_bytes(), sidecar.read_bytes()) == before, (
        'A foreign sidecar in a single-experiment scan must be retained for diagnosis'
    )


def test_single_structure_cross_bank_equality_has_joint_free_count_and_covariance(tmp_path):
    root = cases.base_project(tmp_path / 'joint')
    aliases = [('leader', 'zeta.peak.broad_gauss_w'), ('follower', 'alpha.peak.broad_gauss_w')]
    cases.relations(root, aliases, ['follower = leader'])
    project = engine.Project.load(root)
    project.experiments['zeta'].peak.broad_gauss_w.free = True
    project.analysis.calculate()
    for bank_index, bank in enumerate(cases.BANKS):
        data = project.experiments[bank].data
        y = np.asarray(data.intensity_calc).copy()
        project.experiments[bank].data = engine.PdCwlData(
            two_theta=cases.GRID,
            intensity_meas=y + 0.05 * np.sin(np.arange(len(y)) * 1.7 + bank_index),
            intensity_meas_su=np.ones(len(y)),
        )
    project.structure.cell.length_a.value = 4.102
    result = project.analysis.fit()
    assert result.converged, 'A powder equality across banks must enter one successful joint solve'
    free = list(project.free_parameters)
    assert len(free) == 4, (
        'One cell, two independent scales and one shared width make four independent columns'
    )
    a = project.experiments['zeta'].peak.broad_gauss_w
    b = project.experiments['alpha'].peak.broad_gauss_w
    assert b.value == a.value, 'An equality follower must have its leader value'
    assert b.uncertainty == a.uncertainty, (
        'An equality follower must have its leader joint propagated uncertainty'
    )
    covariance, chi_square = cases.calculation_covariance(project, free)
    assert result.reduced_chi_square == pytest.approx(chi_square, rel=1e-6), (
        'The powder joint reduced chi-square must divide by observations minus four independents'
    )
    np.testing.assert_allclose(
        [p.uncertainty for p in free],
        np.sqrt(np.diag(covariance)),
        rtol=0.03,
        err_msg='Joint covariance must follow the calculation Jacobian and N minus four',
    )


def test_two_phase_ratio_fit_retains_three_independents_and_joint_covariance(tmp_path):
    project = cases.ratio_covariance_project(tmp_path / 'ratio', engine, source='leader')
    other = project.structures['other'].cell
    other.length_a.value = 4.7
    other.length_b.value = 4.9
    other.length_c.value = 4.1 * 5.3 * 6.7 / (4.7 * 4.9)
    for bank, phase in [('zeta', 'phase'), ('zeta', 'other'), ('alpha', 'phase')]:
        project.experiments[bank].linked_structures[phase].scale.free = True
    project.analysis.calculate()
    for index, bank in enumerate(cases.BANKS):
        y = np.asarray(project.experiments[bank].data.intensity_calc).copy()
        project.experiments[bank].data = engine.PdCwlData(
            two_theta=cases.GRID,
            intensity_meas=y + 0.05 * np.sin(np.arange(len(y)) * 1.7 + index),
            intensity_meas_su=np.ones(len(y)),
        )
    result = project.analysis.fit()
    assert result.converged, 'A phase-ratio relation must participate in a successful joint fit'
    free = list(project.free_parameters)
    assert len(free) == 3, (
        'Four phase scales with one ratio follower have three independent columns'
    )
    fractions = [
        project.experiments[bank].linked_structures['other'].weight_fraction
        for bank in cases.BANKS
    ]
    fraction_values = [(fraction.value, fraction.uncertainty) for fraction in fractions]
    for value, uncertainty in fraction_values:
        assert uncertainty is not None, 'A fitted phase ratio must have a defined uncertainty'
        assert uncertainty > 0, 'Uncertain leader ratios must give a positive fraction s.u.'
        assert abs(value - 1 / 3) <= 5 * uncertainty, (
            'Fitted fractions must recover their authored equal-ZMV ratio within five s.u.'
        )
    parameters = [
        project.experiments[bank].linked_structures[phase].scale
        for bank, phase in [('zeta', 'phase'), ('zeta', 'other'), ('alpha', 'phase')]
    ]
    covariance, chi_square = cases.calculation_covariance(project, parameters)
    u, v, _t = [parameter.value for parameter in parameters]
    gradient = np.array([-v, u, 0.0]) / (u + v) ** 2
    expected_sigma = float(np.sqrt(gradient @ covariance @ gradient))
    for _value, error in fraction_values:
        oracle.numeric_error(error, expected_sigma)
    assert result.reduced_chi_square == pytest.approx(chi_square, rel=1e-6), (
        'The phase-sum reduced chi-square must divide by observations minus three independents'
    )
    np.testing.assert_allclose(
        [parameter.uncertainty for parameter in parameters],
        np.sqrt(np.diag(covariance)),
        rtol=0.03,
        err_msg='The phase-sum joint covariance must use the relation Jacobian and N minus three',
    )
    check_saved_fitted_fraction(project, parameters, covariance, tmp_path / 'fitted-saved')
    assert fraction_values[0][0] == pytest.approx(fraction_values[1][0], abs=1e-12), (
        'Shared phase ratios must produce the same weight fractions in unequal-scale banks'
    )
    assert fraction_values[0][1] == pytest.approx(fraction_values[1][1], rel=1e-5), (
        'The fitted joint covariance must give shared weight fractions the same uncertainty'
    )


def test_completion_event_sees_both_tables_and_a_vanished_next_file_is_skipped(tmp_path):
    root = cases.generated_series(tmp_path / 'series', engine)
    events = []

    def completed(event):
        events.append(event)
        (_, points), (_, banks) = result_tables(root)
        assert len(banks) == 2 * len(points), (
            'A completion event must observe both files after the complete point group is written'
        )
        if len(events) == 1:
            (root / 'scan/T300K_b1.xy').unlink()

    engine.Project.load(root).analysis.fit(on_file_complete=completed)
    (_, points), (_, banks) = result_tables(root)
    assert [row['point'] for row in points] == ['T050K', 'T500K'], (
        'A file vanishing during the run must skip its point and allow the next point to fit'
    )
    assert len(banks) == 4, 'A vanished point must leave no partial experiment rows'
    assert len(events) == 2, 'Only the completed points must emit completion events'


def test_invalid_shared_relation_is_scan_level_before_any_dataset_skip(tmp_path):
    root = cases.generated_series(tmp_path / 'series', engine)
    cases.relations(
        root,
        [('structural', 'phase.cell.length_a'), ('bank', 'zeta.linked_structure.phase.scale')],
        ['structural = bank'],
    )
    with pytest.raises((ValueError, RuntimeError), match=r'phase.cell.length_a|zeta.*scale'):
        engine.Project.load(root).analysis.fit()
    assert not (root / 'analysis/results.csv').exists(), (
        'An invalid shared relation must stop before producing a point result'
    )
    assert not (root / 'analysis/scan-notes.csv').exists(), (
        'A shared configuration error must not be reported as a skip for every dataset'
    )


def check_saved_fitted_fraction(project, parameters, covariance, destination):
    cells = [
        [getattr(project.structures[phase].cell, item).value for item in persistence.CELL_ITEMS]
        for phase in ('phase', 'other')
    ]
    adopted = persistence.adopted_fraction(
        [p.value for p in parameters], [p.uncertainty for p in parameters], covariance, cells
    )
    project.save_as(destination)
    parameters = [
        project.experiments[b].linked_structures[p].scale
        for b, p in [('zeta', 'phase'), ('zeta', 'other'), ('alpha', 'phase')]
    ]
    persistence.check_adopted(project, parameters, adopted)
    persistence.correlations(
        (destination / 'analysis/analysis.edi').read_text(),
        [
            b + '.linked_structure.' + p + '.scale'
            for b, p in [('zeta', 'phase'), ('zeta', 'other'), ('alpha', 'phase')]
        ],
        adopted['rho'],
    )
    for file in (destination / 'experiments').glob('*.edi'):
        oracle.category(
            file.read_text(),
            '_linked_structure.weight_fraction',
            adopted['fraction'],
            adopted['sigma'],
        )
