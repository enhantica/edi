"""Owner 2d09daaf3: copyable tutorial and docs code spells each parameter out."""

import ast
import json
import re
import textwrap

import pytest

from tests.fixtures.tutorial_cases.contract import ROOT
from tests.fixtures.tutorial_cases.install_cell import python_syntax
from tests.fixtures.tutorial_cases.presentation import text


def plain_attributes(source, location):
    # Only the notebook install magic is outside Python syntax.
    source = python_syntax(source)
    try:
        tree = ast.parse(textwrap.dedent(source))
    except SyntaxError as error:
        pytest.fail('Gate 3: copyable docs Python must parse: ' + location + ': ' + str(error))
    string_bindings = set()
    for node in (item for item in ast.walk(tree) if isinstance(item, ast.Assign)):
        value = node.value
        values = value.elts if isinstance(value, (ast.List, ast.Tuple, ast.Set)) else [value]
        if values and all(
            (isinstance(item, ast.Constant) and isinstance(item.value, str))
            or (isinstance(item, ast.Name) and item.id in string_bindings)
            for item in values
        ):
            string_bindings.update(
                target.id for target in node.targets if isinstance(target, ast.Name)
            )
    for node in ast.walk(tree):
        name = (
            node.name.rsplit('.', 1)[-1]
            if isinstance(node, ast.alias)
            else node.id
            if isinstance(node, ast.Name)
            else node.attr
            if isinstance(node, ast.Attribute)
            else ''
        )
        assert name not in {'getattr', 'setattr'}, (
            'Gate 3: tutorials and docs spell parameter attributes out; no getattr/setattr: '
            + location
            + ':'
            + str(getattr(node, 'lineno', 0))
        )
        if not isinstance(node, ast.For):
            continue
        variables = {item.id for item in ast.walk(node.target) if isinstance(item, ast.Name)}
        # Attribute-name loops remain prohibited if reflection is disguised as subscription
        # or an intermediate variable; ordinary loops over datasets are still legitimate.
        strings = [
            item.value
            for item in ast.walk(node.iter)
            if isinstance(item, ast.Constant) and isinstance(item.value, str)
        ]
        string_alias = any(
            isinstance(item, ast.Name) and item.id in string_bindings
            for item in ast.walk(node.iter)
        )
        if not strings and not string_alias:
            continue
        dependent = set(variables)
        for statement in node.body:
            if isinstance(statement, (ast.Assign, ast.AnnAssign)):
                used = {
                    item.id for item in ast.walk(statement.value) if isinstance(item, ast.Name)
                }
                targets = (
                    statement.targets if isinstance(statement, ast.Assign) else [statement.target]
                )
                if used & dependent:
                    dependent.update(
                        item.id
                        for target in targets
                        for item in ast.walk(target)
                        if isinstance(item, ast.Name)
                    )
            else:
                targets = []
            for target in targets:
                parameter_writes = [
                    item
                    for item in ast.walk(target)
                    if isinstance(item, ast.Attribute) and item.attr in {'free', 'value'}
                ]
                for write in parameter_writes:
                    used = {
                        item.id for item in ast.walk(write.value) if isinstance(item, ast.Name)
                    }
                    assert not used & dependent, (
                        'Gate 3: tutorial parameters are explicit, with no attribute-name loop: '
                        + location
                        + ':'
                        + str(node.lineno)
                    )


@pytest.mark.parametrize('surface', ['scripts', 'notebooks', 'docs'])
def test_all_copyable_tutorial_and_docs_code_uses_explicit_attributes(surface):
    snippets = []
    if surface == 'scripts':
        snippets = [
            (str(path.relative_to(ROOT)), path.read_text())
            for path in sorted((ROOT / 'docs/user/tutorials').glob('*.py'))
        ]
    elif surface == 'notebooks':
        snippets = [
            (str(path.relative_to(ROOT)) + ':cell ' + str(index), text(cell))
            for path in sorted((ROOT / 'docs/user/tutorials').glob('*.ipynb'))
            for index, cell in enumerate(json.loads(path.read_text())['cells'])
            if cell['cell_type'] == 'code'
        ]
    else:
        paths = sorted(
            set((ROOT / 'docs').rglob('*.md'))
            | set((ROOT / 'website/surfaces/docs').rglob('*.md'))
        )
        snippets = [
            (str(path.relative_to(ROOT)) + ':snippet ' + str(index), match[2])
            for path in paths
            for index, match in enumerate(
                re.finditer(
                    r'(?m)^([ \t]*)`{3,}(?:python|py)\s*\n(.*?)^\1`{3,}\s*$',
                    path.read_text(),
                    re.DOTALL,
                )
            )
        ]
    assert snippets, 'Gate 3: each tutorial/docs surface must supply copyable Python to check'
    failures = []
    for location, source in snippets:
        try:
            plain_attributes(source, location)
        except (AssertionError, pytest.fail.Exception) as error:
            failures.append(str(error))
    assert not failures, (
        'Gate 3: plain parameter access is required on every surface:\n' + '\n'.join(failures)
    )


@pytest.mark.parametrize(
    'escape',
    [
        'getattr(experiment.peak, "u").free = True',
        'setattr(experiment.peak.u, "free", True)',
        'import builtins as b\nb.getattr(experiment.peak, "u").free = True',
        'fetch = getattr\nfetch(experiment.peak, "u").free = True',
        'from builtins import getattr as fetch\nfetch(experiment.peak, "u").free = True',
        'for name in ("u", "v"):\n    experiment.peak[name].free = True',
        (
            'for name in ("u", "v"):\n    parameter = vars(experiment.peak)[name]\n'
            '    parameter.free = True'
        ),
        ('names = ("u", "v")\nfor name in names:\n    experiment.peak[name].free = True'),
    ],
)
def test_plain_attribute_observer_refuses_dynamic_access_and_string_loop_escapes(escape):
    plain_attributes(
        'experiment.peak.u.free = True\nexperiment.peak.v.free = True', 'positive control'
    )
    with pytest.raises(AssertionError, match='Gate 3:'):
        plain_attributes(escape, 'negative control')


@pytest.mark.parametrize('collection', ['project.free_parameters', 'experiment.background'])
def test_named_model_objects_are_not_mistaken_for_attribute_name_strings(collection):
    plain_attributes(
        "project = edi.Project(name='sample')\n"
        "experiment = edi.Experiment(name='bank')\n"
        f'for parameter in {collection}:\n    parameter.free = True\n',
        'model collection control',
    )
