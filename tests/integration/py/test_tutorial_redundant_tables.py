"""Owner e581fd29c: show the free set when it changes, without repeating fitted results."""

import ast

import pytest

from tests.fixtures.tutorial_cases.contract import interfaces_for
from tests.fixtures.tutorial_cases.install_cell import python_syntax
from tests.integration.py.test_tutorial_fit_stages import FITTING, source


def assert_no_repeated_free_table(code):  # noqa: PLR0912 - explicit teaching-state transitions
    tree = ast.parse(python_syntax(code))
    events = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Attribute) and target.attr == 'free' for target in node.targets
        ):
            events.append((node.lineno, node.col_offset, 'changed'))
        if isinstance(node, ast.Call):
            name = ast.unparse(node.func)
            if name.endswith('.analysis.fit'):
                kind = 'fit'
            elif name.endswith('.display.fit.results'):
                kind = 'results'
            elif name.endswith('.display.parameters.free'):
                kind = 'free-table'
            elif '.constraints.' in name and name.endswith((
                '.create',
                '.add',
                '.remove',
                '.clear',
            )):
                kind = 'changed'
            else:
                continue
            events.append((node.lineno, node.col_offset, kind))
    fitted = False
    results = False
    for _line, _column, kind in sorted(events):
        if kind == 'fit':
            fitted, results = True, False
        elif kind == 'changed':
            results = False
        elif kind == 'results' and fitted:
            results = True
        elif kind == 'free-table':
            assert not results, (
                'Gate 3: a free-parameter table after fit results repeats the fitted table; '
                'show it only when teaching a changed free set'
            )


@pytest.mark.parametrize('case', [case for case in FITTING if 'python' in interfaces_for(case)])
@pytest.mark.parametrize('surface', ['script', 'notebook'])
def test_tutorial_does_not_repeat_the_fitted_table_after_any_stage(case, surface):
    assert_no_repeated_free_table(source(case, surface))


@pytest.mark.parametrize(
    'interlude', ['', 'project.display.pattern()\n', 'project.display.fit.correlations()\n']
)
def test_redundant_table_observer_refuses_footer_and_interleaved_chart_repetitions(interlude):
    prefix = 'project.analysis.fit()\nproject.display.fit.results()\n'
    with pytest.raises(AssertionError, match='Gate 3:'):
        assert_no_repeated_free_table(prefix + interlude + 'project.display.parameters.free()\n')


def test_changed_free_set_and_pre_fit_free_table_remain_teachable():
    assert_no_repeated_free_table(
        'project.display.parameters.free()\nproject.analysis.fit()\n'
        'project.display.fit.results()\nstructure.cell.length_a.free = True\n'
        'project.display.parameters.free()\nproject.analysis.fit()\nproject.display.fit.results()\n'
    )
