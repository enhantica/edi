"""Owner 7101f0fd9 / 58c51248e / 1c330632f: strategy governs stages; retain constraints."""

import json
from types import SimpleNamespace

import pytest

from tests.fixtures.tutorial_cases.contract import CASES, CONTRACT, ROOT, cases_for, interfaces_for
from tests.fixtures.tutorial_cases.presentation import notebook, text
from tests.fixtures.tutorial_cases.stages import (
    app_cycles,
    app_population,
    assert_correlation_lesson,
    assert_teaching_stages,
    observe,
    prose_cycles,
)
from tests.fixtures.tutorial_cases.strategy import assert_strategy

FITTING = [case for case in CASES if case not in CONTRACT['simulations']]
REFERENCE = json.loads((ROOT / 'tests/fixtures/tutorial_outline/stages.json').read_text())
CORRELATION = sorted(
    {'pd-neut-cwl_lbco-hrpt', 'pd-neut-cwl_cosio-d20'}
    | {
        case
        for case, plan in REFERENCE['cases'].items()
        if any(
            event['kind'] == 'constraint'
            and any(previous['kind'] == 'fit' for previous in plan['events'][:index])
            for index, event in enumerate(plan['events'])
        )
    }
)


def source(case, surface):
    if surface == 'script':
        return (ROOT / 'docs/user/tutorials' / (case + '.py')).read_text()
    return '\n'.join(
        text(cell)
        if cell['cell_type'] == 'code'
        else '\n'.join('# ' + line for line in text(cell).splitlines())
        for cell in notebook(case)['cells']
    )


@pytest.mark.parametrize('case', [case for case in FITTING if 'python' in interfaces_for(case)])
@pytest.mark.parametrize('surface', ['script', 'notebook'])
def test_each_fitting_tutorial_shows_and_teaches_successive_parameter_groups(case, surface):
    assert_teaching_stages(observe(source(case, surface)))


@pytest.mark.parametrize('case', [case for case in FITTING if 'python' in interfaces_for(case)])
def test_notebook_and_script_teach_the_same_exact_stage_sequence(case):
    first, second = [observe(source(case, surface)) for surface in ['script', 'notebook']]
    assert first['cycles'] == second['cycles'] and first['free_before'] == second['free_before'], (
        'Gate 3: source and notebook have identical free parameters, stages and repeated cycles'
    )


@pytest.mark.parametrize('case', [case for case in FITTING if case in cases_for('app', 'python')])
def test_app_tutorial_teaches_the_same_fitting_groups_cycles_and_constraints(case):
    entries = json.loads((ROOT / 'app/tutorials/manifest.json').read_text())['tutorials']
    matches = [entry for entry in entries if entry['id'] == case]
    assert len(matches) == 1, (
        'Gate 3/4: each fitting case has its own built-in tutorial to compare'
    )
    entry = matches[0]
    if 'tour' in entry:
        document = json.loads((ROOT / 'app/tutorials' / entry['tour']).read_text())
        steps = [step for page in document['pages'] for step in page['steps']]
    else:
        steps = entry.get('steps', [])
    assert app_cycles(steps, app_population(case)) == observe(source(case, 'script'))['cycles'], (
        'Gate 3/4: the app teaches the same groups, fit order, repeats and constraints as Python'
    )


@pytest.mark.parametrize('case', [case for case in FITTING if case in cases_for('app', 'python')])
def test_app_docs_teach_the_same_fit_stages_as_the_executable_tutorial(case):
    path = ROOT / CONTRACT['tutorials']['app_docs'].format(case=case)
    assert path.is_file(), 'Gate 3/4: each fitting case has its app tutorial page'
    assert prose_cycles(path.read_text()) == observe(source(case, 'script'))['cycles'], (
        'Gate 3/4: the app page teaches the same groups and fitting cycles as the notebook'
    )


def test_instruction_and_app_observers_preserve_the_same_nontrivial_stage_changes():
    written = 'Free the scale and background.\n\nClick Fit.\n\nFree the cell.\n\nClick Fit again.'
    steps = [
        {'check': 'free:linked_structure.scale,background.intensity'},
        {'target': 'statusBar.fit.button'},
        {'check': 'free:cell.length_a'},
        {'target': 'statusBar.fit.button'},
    ]
    assert prose_cycles(written) == app_cycles(steps), (
        'Gate 3/4: instruction and app observers retain stage boundaries and cumulative groups'
    )
    assert prose_cycles(written) != prose_cycles(
        written.replace('Free the cell.', 'Free the peak widths.')
    ), 'Gate 3/4: changing a stage parameter group changes the observed tutorial sequence'


@pytest.mark.parametrize('case', [case for case in FITTING if 'python' in interfaces_for(case)])
@pytest.mark.parametrize('surface', ['script', 'notebook'])
def test_each_fitting_case_follows_cumulative_strategy_with_one_new_block(case, surface):
    # Owner 7101f0fd9 replaces exact upstream cycles and the prose-deviation escape.
    assert_strategy(observe(source(case, surface)))


@pytest.mark.parametrize(
    'case', [case for case in CORRELATION if 'python' in interfaces_for(case)]
)
@pytest.mark.parametrize('surface', ['script', 'notebook'])
def test_correlation_lesson_shows_the_pair_before_constraining_and_refitting(case, surface):
    assert_correlation_lesson(observe(source(case, surface)))


@pytest.mark.parametrize(
    'escape',
    ['single-fit', 'all-free-first', 'no-start-pattern', 'no-stage-pattern', 'no-results'],
)
def test_stage_observer_rejects_flat_fits_and_missing_teaching_outputs(escape):
    good = (
        'project.display.pattern()\nexperiment.scale.free = True\nproject.analysis.fit()\n'
        'project.display.pattern()\nproject.display.fit.results()\n'
        'structure.cell.length_a.free = True\nproject.analysis.fit()\n'
        'project.display.pattern()\nproject.display.fit.results()\n'
    )
    assert_teaching_stages(observe(good))
    broken = good
    if escape == 'single-fit':
        broken = good[: good.rindex('project.analysis.fit()')]
    elif escape == 'all-free-first':
        broken = 'structure.cell.length_a.free = True\n' + good
    elif escape == 'no-start-pattern':
        broken = good.replace('project.display.pattern()\n', '', 1)
    elif escape == 'no-stage-pattern':
        broken = good.replace(
            'project.display.pattern()\nproject.display.fit.results()',
            'project.display.fit.results()',
            1,
        )
    else:
        broken = good.replace('project.display.fit.results()\n', '')
    with pytest.raises(AssertionError, match='Gate 3:'):
        assert_teaching_stages(observe(broken))


@pytest.mark.parametrize('escape', ['before-fit', 'no-correlations', 'no-constraint', 'no-refit'])
def test_correlation_order_observer_refuses_missing_and_reordered_steps(escape):
    events = [
        {'kind': value} for value in ['fit', 'correlations', 'constraint', 'fit', 'correlations']
    ]
    assert_correlation_lesson({'events': events})
    if escape == 'before-fit':
        events[0], events[2] = events[2], events[0]
    else:
        kind = {
            'no-correlations': 'correlations',
            'no-constraint': 'constraint',
            'no-refit': 'fit',
        }[escape]
        events = [
            item
            for index, item in enumerate(events)
            if item['kind'] != kind or (kind == 'fit' and index == 0)
        ]
    with pytest.raises(AssertionError, match='Gate 3:'):
        assert_correlation_lesson({'events': events})


def test_app_observer_tracks_members_resets_and_completed_unique_constraints():
    population = {
        'structure.atom_sites.A.adp_iso': ('isotropic displacement', 'sample'),
        'structure.atom_sites.B.adp_iso': ('isotropic displacement', 'sample'),
    }
    steps = [
        {'check': 'tick:experiment.scale'},
        {'check': 'free-choice:free:Atomic displacement'},
        {'check': 'untick:structure.atom_sites.A.adp_iso'},
        {'check': 'rows:constraints.append=1'},
        {'check': 'field:constraint.expression.0=a = b'},
        {'check': 'field:constraint.expression.0='},
        {'target': 'statusBar.fit.button'},
        {'check': 'fit-done'},
        {'check': 'field:constraint.expression.0=b = a'},
        {'check': 'field:constraint.expression.0=b = a'},
        {'check': 'field:constraint.expression.1=b = a'},
        {'target': 'statusBar.fit.button', 'check': 'fit-done'},
        {'check': 'free-choice:fixed:All categories'},
        {'check': 'tick:structure.atom_sites.A.adp_iso'},
        {'check': 'fit-done'},
    ]
    cycles = app_cycles(steps, population)
    assert len(cycles) == 3, 'Gate 3/4: a button followed by completion is one fit cycle'
    assert cycles[0]['active'] == ['isotropic displacement', 'scale'], (
        'Gate 3/4: unticking one member preserves the other active displacement member'
    )
    assert [cycle['constraints'] for cycle in cycles] == [0, 1, 0], (
        'Gate 3/4: empty rows are not constraints and completed identical expressions count once'
    )
    assert cycles[-1]['active'] == ['isotropic displacement'], (
        'Gate 3/4: Fixed All clears every parameter before individual rows can be freed again'
    )
    assert app_cycles(steps[:3] + [{'check': 'fit-done'}], population) != app_cycles(
        steps[:3] + [{'check': 'untick:structure.atom_sites.B.adp_iso'}, {'check': 'fit-done'}],
        population,
    ), 'Gate 3/4: removing the final member removes its scientific group'


def test_source_observer_expands_loops_and_evaluates_symmetry_and_user_constraints():
    sites = [SimpleNamespace(id='A'), SimpleNamespace(id='B')]
    for site in sites:
        site.fract_x = SimpleNamespace(symmetry_constrained=site.id == 'A')
        site.fract_y = SimpleNamespace(symmetry_constrained=False)
        site.adp_iso = SimpleNamespace(user_constrained=site.id == 'B')
    code = """for site in structure.atom_sites:
    site.adp_iso.free = not site.adp_iso.user_constrained
    for coordinate in (site.fract_x, site.fract_y):
        coordinate.free = not coordinate.symmetry_constrained
project.analysis.fit()
for parameter in project.free_parameters:
    parameter.free = False
experiment.scale.free = True
project.analysis.fit()
"""
    bindings = {'structure': SimpleNamespace(atom_sites=sites)}
    plan = observe(code, bindings)
    assert plan['free_before'][0] == [
        "structure.atom_sites['A'].adp_iso",
        "structure.atom_sites['A'].fract_y",
        "structure.atom_sites['B'].fract_x",
        "structure.atom_sites['B'].fract_y",
    ], 'Gate 3: tuple and collection loops retain each eligible independent parameter'
    assert plan['free_before'][1] == ['experiment.scale'], (
        'Gate 3: a reset clears the actual active population before the next fit'
    )
    sites[0].fract_x.symmetry_constrained = False
    assert observe(code, bindings)['free_before'] != plan['free_before'], (
        'Gate 3: changing symmetry eligibility changes the actual observed free population'
    )

    counted = observe(
        'for index in range(2):\n    experiment.background[index].intensity.free = True\n'
        'experiment.background[0].intensity.free = False\nproject.analysis.fit()\n'
    )
    assert counted['free_before'] == [['experiment.background[1].intensity']], (
        'Gate 3: range indices resolve to actual members so a later explicit fix reaches them'
    )

    points = [SimpleNamespace(id='1'), SimpleNamespace(id='2')]
    indexed = observe(
        'for point in experiment.background:\n    point.intensity.free = True\n'
        'experiment.background[0].intensity.free = False\nproject.analysis.fit()\n',
        {'experiment': SimpleNamespace(background=points)},
    )
    assert indexed['free_before'] == counted['free_before'], (
        'Gate 3: background iteration uses sequence indices rather than display row ids'
    )
