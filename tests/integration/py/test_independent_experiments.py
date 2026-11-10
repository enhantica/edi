"""Independent model results equal isolated fits and analytic single-crystal optima."""

import csv
import math
from pathlib import Path

import edi as engine
import gemmi
import pytest

from tests.fixtures.independent_experiments.reference import (
    BANKS,
    MARKERS,
    START,
    optimum,
    project_files,
    scan_files,
)

ROOT = Path(__file__).resolve().parents[3]


def occupancy(project, phase):
    matches = [
        site.occupancy
        for structure in project.structures
        for site in structure.atom_sites
        if site.id == 'Ni'
        and math.isclose(float(site.fract_x.value), MARKERS[phase], rel_tol=0, abs_tol=1e-15)
    ]
    assert len(matches) == 1, 'Each crystal retains its independent immutable coordinate identity'
    return matches[0]


def fit_at(folder, **options):
    model = engine.Project.load(project_files(folder, **options))
    result = model.analysis.fit()
    return model, result


@pytest.fixture(scope='module')
def fits(tmp_path_factory):
    folder = tmp_path_factory.mktemp('independent-experiments')
    singles = {name: fit_at(folder / name, mode='single', selected=name) for name in BANKS}
    joint = fit_at(folder / 'joint', mode='joint', shared=True)
    independent, result, before, error = None, None, {}, None
    try:
        independent = engine.Project.load(project_files(folder / 'independent'))
    except Exception as exception:  # noqa: BLE001 - retain any actual public-entry refusal
        error = type(exception).__name__ + ': ' + str(exception)
    if independent is not None:
        before = {
            name: occupancy(independent, data['phase']).value for name, data in BANKS.items()
        }
        try:
            result = independent.analysis.fit()
        except Exception as exception:  # noqa: BLE001 - each gate separately asserts successful dispatch
            error = type(exception).__name__ + ': ' + str(exception)
    snapshot, banks = {}, {}
    if result is not None:
        snapshot = {
            name: (
                float(occupancy(independent, data['phase']).value),
                float(occupancy(independent, data['phase']).uncertainty),
            )
            for name, data in BANKS.items()
        }
        saved = folder / 'saved-independent'
        independent.save_as(saved)
        source = (saved / 'analysis/analysis.edi').read_text()
        block = gemmi.cif.read_string('data_result\n' + source).sole_block()
        table = block.find([
            '_fit_result_bank.experiment_id',
            '_fit_result_bank.n_data_points',
            '_fit_result_bank.chi_square',
            '_fit_result_bank.prof_wr_factor',
        ])
        banks = {
            row[0]: {'n': int(row[1]), 'chi': float(row[2]), 'rwp': float(row[3])} for row in table
        }
    return {
        'snapshot': snapshot,
        'banks': banks,
        'singles': singles,
        'joint': joint,
        'project': independent,
        'result': result,
        'error': error,
        'before': before,
    }


def successful_run(fits):
    assert fits['error'] is None, (
        'Independent non-scan mode fits each linked crystal without a scan directory: '
        + str(fits['error'])
    )
    assert fits['result'] is not None, 'Independent fitting returns a complete result'
    assert fits['result'].success, (
        'Every independent dataset must complete its real fit successfully'
    )
    return fits['project'], fits['result']


@pytest.mark.parametrize('name', BANKS)
def test_isolated_fit_matches_independent_weighted_normal_equations(name, fits):
    project, result = fits['singles'][name]
    parameter = occupancy(project, BANKS[name]['phase'])
    expected = optimum([name])
    assert result.success, 'The isolated scientific control completes its fit'
    assert parameter.value == pytest.approx(expected['value'], rel=2e-5, abs=1e-9), (
        'An isolated P1 Ni occupancy matches the independent weighted normal equation'
    )
    assert parameter.uncertainty == pytest.approx(expected['su'], rel=3e-4, abs=1e-9), (
        'The isolated uncertainty uses its own residual variance and local Fisher derivative'
    )
    assert result.reduced_chi_square == pytest.approx(expected['reduced'], rel=2e-5, abs=1e-9), (
        'The isolated goodness of fit uses its own reflection count minus one free parameter'
    )


@pytest.mark.parametrize('name', BANKS)
def test_each_independent_crystal_keeps_the_isolated_value_and_su(name, fits):
    _project, _result = successful_run(fits)
    single, _single_result = fits['singles'][name]
    expected = occupancy(single, BANKS[name]['phase'])
    actual_value, actual_su = fits['snapshot'][name]
    assert fits['before'][name] == START, (
        'Every independent fit receives the authored initial state'
    )
    assert actual_value == pytest.approx(expected.value, rel=2e-6, abs=1e-9), (
        'Each structure gets exactly its own isolated fitted value, even with repeated atom IDs'
    )
    assert actual_su == pytest.approx(expected.uncertainty, rel=2e-5, abs=1e-9), (
        'Independent uncertainties equal isolated uncertainties, never a pooled joint estimate'
    )


@pytest.mark.parametrize('name', BANKS)
def test_each_independent_result_keeps_its_named_dataset_quality(name, fits):
    _project, _result = successful_run(fits)
    banks = fits['banks']
    expected = optimum([name])
    assert set(banks) == set(BANKS), 'Each dataset retains one distinct named independent result'
    actual = banks[name]
    assert actual['n'] == expected['n'], 'Independent result counts belong to their own dataset'
    assert actual['chi'] / (actual['n'] - 1) == pytest.approx(
        expected['reduced'], rel=2e-5, abs=1e-9
    ), 'Each dataset reports its own reduced goodness of fit, not a pooled value'
    assert actual['rwp'] == pytest.approx(expected['rwp'], rel=2e-5, abs=1e-9), (
        'Each independent result reports its own weighted profile agreement'
    )


def test_noise_controls_distinguish_independent_from_pooled_uncertainties(fits):
    _project, _result = successful_run(fits)
    references = {name: optimum([name]) for name in BANKS}
    pooled = sum(row['chi'] for row in references.values()) / sum(
        row['n'] - 1 for row in references.values()
    )
    assert len({round(row['reduced'], 5) for row in references.values()}) == 3, (
        'The independent data deliberately have different noise variances and goodness of fit'
    )
    separated = 0
    for name, row in references.items():
        pooled_su = row['su'] * math.sqrt(pooled / row['reduced'])
        actual = fits['snapshot'][name][1]
        separated += abs(actual - pooled_su) > 0.1 * row['su']
    assert separated >= 2, 'At least two uncertainties must reject the pooled-variance alternative'


def test_joint_keeps_its_shared_structure_and_pooled_solution(fits):
    project, result = fits['joint']
    actual = occupancy(project, 'shared')
    expected = optimum(list(BANKS))
    assert result.success, 'The unchanged joint control completes one shared-structure fit'
    assert actual.value == pytest.approx(expected['value'], rel=2e-5, abs=1e-9), (
        'Joint mode still solves the pooled observations for its one shared structure'
    )
    assert actual.uncertainty == pytest.approx(expected['su'], rel=3e-4, abs=1e-9), (
        'Joint mode retains covariance scaled by the pooled residual variance'
    )
    assert result.reduced_chi_square == pytest.approx(expected['reduced'], rel=2e-5, abs=1e-9), (
        'Joint goodness of fit retains all observations and one shared free parameter'
    )


@pytest.mark.parametrize('mode', ['independent', 'sequential'])
def test_declared_scan_keeps_file_results_and_weighted_mean_values(tmp_path, mode):
    folder, expected = scan_files(tmp_path / mode, mode)
    project = engine.Project.load(folder)
    complete = []
    result = project.analysis.fit(on_file_complete=complete.append)
    path = folder / 'analysis/results.csv'
    assert result.success, 'The declared scan still completes its ordinary file fits'
    assert path.is_file(), 'A declared scan still produces its ordinary durable results'
    with path.open(newline='') as stream:
        rows = list(csv.DictReader(stream))
    assert len(complete) == len(rows) == 3, (
        'Scan completion still publishes one event and row per file'
    )
    value_key = next(key for key in rows[0] if key.endswith('base.coef'))
    su_key = value_key.removesuffix('.value') + '.uncertainty'
    for row in rows:
        reference = expected[Path(row['file_path']).name]
        assert float(row[value_key]) == pytest.approx(reference['value'], rel=2e-5, abs=1e-8), (
            'A scan retains its own data-file weighted optimum in either scan mode'
        )
        assert float(row[su_key]) == pytest.approx(reference['su'], rel=3e-4, abs=1e-8), (
            'A scan retains its own data-file uncertainty rather than mixing non-scan experiments'
        )


def test_one_non_scan_experiment_also_uses_its_isolated_fit(tmp_path):
    project = engine.Project.load(project_files(tmp_path / 'one', selected='amber'))
    result = project.analysis.fit()
    expected = optimum(['amber'])
    actual = occupancy(project, BANKS['amber']['phase'])
    assert result.success, 'A single independent experiment needs no synthetic scan declaration'
    assert actual.value == pytest.approx(expected['value'], rel=2e-5, abs=1e-9), (
        'One independent experiment reaches its own isolated fitted value'
    )
    assert actual.uncertainty == pytest.approx(expected['su'], rel=3e-4, abs=1e-9), (
        'One independent experiment retains its own isolated uncertainty'
    )


def test_shared_structure_refuses_before_any_partial_fit_is_published(tmp_path):
    project = engine.Project.load(project_files(tmp_path / 'ambiguous-input', shared=True))
    before = [(repr(p.value), repr(p.uncertainty), bool(p.free)) for p in project.parameters]
    with pytest.raises((ValueError, RuntimeError), match=r'(?i)structure.{0,80}\bshared\b'):
        project.analysis.fit()
    after = [(repr(p.value), repr(p.uncertainty), bool(p.free)) for p in project.parameters]
    assert after == before, 'Independent mode refuses a shared structure before any fit changes it'


def relation_parameters(project):
    return (
        occupancy(project, BANKS['amber']['phase']),
        next(
            site.fract_y
            for structure in project.structures
            for site in structure.atom_sites
            if math.isclose(
                float(site.fract_x.value),
                MARKERS[BANKS['amber']['phase']],
                rel_tol=0,
                abs_tol=1e-15,
            )
        ),
        occupancy(project, BANKS['violet']['phase']),
    )


def relation_snapshot(project, folder):
    project.report.save_cif()
    reports = list((folder / 'reports').glob('*.cif'))
    assert len(reports) == 1, 'The public report export provides one observable result snapshot'
    return (
        [(repr(p.value), repr(p.uncertainty), bool(p.free)) for p in project.parameters],
        reports[0].read_bytes(),
        [(a.id, a.expression, bool(a.enabled)) for a in project.analysis.constraints],
    )


@pytest.mark.parametrize(
    'draft', [False, True], ids=['disabled-cross-dataset', 'disabled-empty-draft']
)
def test_disabled_relation_is_not_an_independent_fit_dependency(tmp_path, draft):
    folder = project_files(tmp_path / 'disabled')
    analysis = folder / 'analysis/analysis.edi'
    text = analysis.read_text()
    if not draft:
        text += (
            'loop_\n_alias.id\n_alias.parameter_unique_name\n'
            'a phase_z.atom_site.Ni.occupancy\nb phase_a.atom_site.Ni.occupancy\n'
        )
    text += 'loop_\n_constraint.id\n_constraint.expression\n_constraint.enabled\n' + (
        "draft '' false\n" if draft else "dormant 'a = b' false\n"
    )
    analysis.write_text(text)
    project = engine.Project.load(folder)
    assert len(project.analysis.constraints) == 1, (
        'The disabled row survives loading rather than being dropped'
    )
    assert not next(iter(project.analysis.constraints)).enabled, (
        'The actual disabled relation remains disabled before fitting'
    )
    project.analysis.calculate()
    result = project.analysis.fit()
    assert result.success, 'Disabled relations and empty drafts keep independent fits admissible'
    for name, data in BANKS.items():
        expected = optimum([name])
        actual = occupancy(project, data['phase'])
        assert actual.value == pytest.approx(expected['value'], rel=2e-5, abs=1e-9), (
            'A disabled relation leaves each dataset at its isolated weighted optimum'
        )
        assert actual.uncertainty == pytest.approx(expected['su'], rel=3e-4, abs=1e-9), (
            'A disabled relation leaves each dataset its own isolated uncertainty'
        )
    assert not next(iter(project.analysis.constraints)).enabled, (
        'Fitting must not silently enable the disabled row'
    )


@pytest.mark.parametrize('foreign_alias', ['e', 'e3'])
@pytest.mark.parametrize(
    ('expression', 'dependent'),
    [
        ('a = 1e-3 * b + 0.75', 0.75027),
        ('a = 1e3 * b - 269.25', 0.75),
        ('a = b + 0.5', 0.77),
    ],
    ids=['negative-exponent', 'positive-exponent', 'unused-alias-control'],
)
def test_number_tokens_do_not_borrow_a_foreign_alias_owner(
    tmp_path, foreign_alias, expression, dependent
):
    project = engine.Project.load(project_files(tmp_path / 'local-literal'))
    target, source, foreign = relation_parameters(project)
    target.free = False
    scale = next(
        experiment.linked_structures[0].scale
        for experiment in project.experiments
        if len(experiment.refln.index_h) == BANKS['amber']['n']
    )
    scale.free = True
    project.analysis.aliases.create(id='a', param=target)
    project.analysis.aliases.create(id='b', param=source)
    project.analysis.aliases.create(id=foreign_alias, param=foreign)
    project.analysis.constraints.create(id='local_literal', expression=expression)
    project.analysis.calculate()
    assert target.value == pytest.approx(dependent, rel=0, abs=1e-12), (
        'The real expression parser consumes each complete numeric literal before fitting'
    )
    result = project.analysis.fit()
    assert result.success, (
        'A numeric exponent cannot make a local relation depend on an unused foreign alias'
    )
    reference = optimum(['amber'])
    expected = BANKS['amber']['scale'] * reference['value'] ** 2 / dependent**2
    expected_su = math.sqrt(
        reference['reduced'] / (reference['gram'] * dependent**4 / BANKS['amber']['scale'] ** 2)
    )
    assert scale.value == pytest.approx(expected, rel=2e-5, abs=1e-9), (
        'The local relation and scale reach the independent linear weighted optimum'
    )
    assert scale.uncertainty == pytest.approx(expected_su, rel=3e-4, abs=1e-9), (
        'The local relation keeps the isolated scale covariance rather than a pooled one'
    )
    for name in ['copper', 'violet']:
        actual = occupancy(project, BANKS[name]['phase'])
        reference = optimum([name])
        assert actual.value == pytest.approx(reference['value'], rel=2e-5, abs=1e-9), (
            'Unused exponent-like aliases cannot alter another dataset solution'
        )
        assert actual.uncertainty == pytest.approx(reference['su'], rel=3e-4, abs=1e-9), (
            'Unused exponent-like aliases cannot alter another dataset uncertainty'
        )


def test_enabled_cross_dataset_relation_refuses_transactionally(tmp_path):
    folder = project_files(tmp_path / 'enabled-cross')
    project = engine.Project.load(folder)
    target, _source, foreign = relation_parameters(project)
    project.analysis.aliases.create(id='a', param=target)
    project.analysis.aliases.create(id='b', param=foreign)
    project.analysis.constraints.create(id='between_banks', expression='a = b')
    assert project.analysis.constraints['between_banks'].enabled, (
        'The cross-dataset refusal witness is genuinely enabled'
    )
    before = relation_snapshot(project, folder)
    disk = {str(p.relative_to(folder)): p.read_bytes() for p in folder.rglob('*') if p.is_file()}
    with pytest.raises(
        (ValueError, RuntimeError),
        match=r'(?i)constraint.{0,80}between_banks|between_banks.{0,80}(cross|experiment|dataset|independent)',
    ):
        project.analysis.fit()
    assert relation_snapshot(project, folder) == before, (
        'Cross-dataset refusal preserves values, s.u., flags, relations and fit report'
    )
    assert {
        str(p.relative_to(folder)): p.read_bytes() for p in folder.rglob('*') if p.is_file()
    } == disk, 'Cross-dataset refusal leaves every original project byte unchanged'


def test_enabled_malformed_relation_keeps_normal_parser_refusal(tmp_path):
    folder = project_files(tmp_path / 'malformed')
    project = engine.Project.load(folder)
    target, source, _foreign = relation_parameters(project)
    project.analysis.aliases.create(id='a', param=target)
    project.analysis.aliases.create(id='b', param=source)
    before = relation_snapshot(project, folder)
    with pytest.raises(
        (ValueError, RuntimeError), match=r'(?i)malformed|expression|constraint|unexpected|parse'
    ):
        project.analysis.constraints.create(id='malformed', expression='a = b +')
    assert relation_snapshot(project, folder) == before, (
        'Normal enabled-expression validation remains transactional'
    )
