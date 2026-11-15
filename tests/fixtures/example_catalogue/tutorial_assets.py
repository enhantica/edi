"""Observe literal collection assets reaching adjacent model-building calls."""

import ast
from pathlib import PurePosixPath

from tests.fixtures.tutorial_cases.install_cell import python_syntax


def _consume(statement, variable):
    assert isinstance(statement, ast.Expr)
    call = statement.value
    assert isinstance(call, ast.Call)
    method = ast.unparse(call.func)
    if method == 'project.structures.add_from_cif_path':
        assert len(call.args) == 1
        assert not call.keywords
        argument = call.args[0]
    else:
        assert method == 'project.experiments.add_from_data_path'
        assert not call.args
        assert all(item.arg is not None for item in call.keywords)
        paths = [item.value for item in call.keywords if item.arg == 'data_path']
        assert len(paths) == 1
        argument = paths[0]
    assert isinstance(argument, ast.Name)
    assert argument.id == variable


def _archive_consumer(tree, index, variable):
    following = tree.body[index + 1 : index + 3]
    assert len(following) == 2 and isinstance(following[0], ast.With), (
        'A scan archive download reaches its adjacent ZipFile context'
    )
    context, setting = following
    assert len(context.items) == 1, 'A scan archive has one original ZIP context owner'
    item = context.items[0]
    call = item.context_expr
    assert (
        isinstance(call, ast.Call)
        and ast.unparse(call.func) == 'zipfile.ZipFile'
        and len(call.args) == 1
        and isinstance(call.args[0], ast.Name)
        and call.args[0].id == variable
        and not call.keywords
        and isinstance(item.optional_vars, ast.Name)
    ), 'The actual downloaded scan path opens its own ZIP context directly'
    writes = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Name)
        and node.id == variable
        and isinstance(node.ctx, (ast.Store, ast.Del))
    ]
    assert len(writes) == 1, 'The downloaded scan path cannot be reassigned before consumption'
    assert len(context.body) == 1 and isinstance(context.body[0], ast.Expr), (
        'The scan ZIP context extracts its original archive once'
    )
    extract = context.body[0].value
    assert (
        isinstance(extract, ast.Call)
        and ast.unparse(extract.func) == item.optional_vars.id + '.extractall'
        and len(extract.args) == 1
        and not extract.keywords
        and isinstance(extract.args[0], ast.Constant)
        and isinstance(extract.args[0].value, str)
    ), 'The original ZIP archive extracts to one explicitly named directory'
    assert (
        isinstance(setting, ast.Assign)
        and len(setting.targets) == 1
        and ast.unparse(setting.targets[0]) == 'project.analysis.sequential_fit.data_dir'
        and isinstance(setting.value, ast.Constant)
        and isinstance(setting.value.value, str)
    ), 'The extracted archive directly supplies the declared sequential-fit directory'
    constructors = [
        node.value
        for node in tree.body[:index]
        if isinstance(node, ast.Assign)
        and ast.unparse(node.targets[0]) == 'project'
        and isinstance(node.value, ast.Call)
        and ast.unparse(node.value.func) == 'edi.Project'
    ]
    assert len(constructors) == 1, 'The archive belongs to one previously constructed project'
    names = [
        word.value.value
        for word in constructors[0].keywords
        if word.arg == 'name'
        and isinstance(word.value, ast.Constant)
        and isinstance(word.value.value, str)
    ]
    destination, directory = (
        PurePosixPath(extract.args[0].value),
        PurePosixPath(setting.value.value),
    )
    assert (
        len(names) == 1
        and not destination.is_absolute()
        and not directory.is_absolute()
        and '..' not in destination.parts
        and '..' not in directory.parts
        and destination.parts == (names[0], *directory.parts)
    ), 'The archive extraction supplies this project and its exact relative scan directory'


def assets(source):
    """Return consumed IDs; refuse unused, reassigned or indirect downloads."""
    tree = ast.parse(python_syntax(source))
    observed = []
    reached = set()

    def download(call):
        assert isinstance(call, ast.Call)
        assert ast.unparse(call.func) == 'edi.download_data'
        assert len(call.args) == 1
        assert isinstance(call.args[0], ast.Constant)
        assert isinstance(call.args[0].value, str)
        assert len(call.keywords) <= 1
        assert all(
            item.arg == 'destination'
            and isinstance(item.value, ast.Constant)
            and isinstance(item.value.value, str)
            for item in call.keywords
        )
        reached.add(call)
        observed.append(call.args[0].value)

    for index, statement in enumerate(tree.body):
        if not isinstance(statement, ast.Assign):
            continue
        value = statement.value
        if isinstance(value, ast.Call) and ast.unparse(value.func) == 'edi.download_data':
            assert len(statement.targets) == 1
            assert isinstance(statement.targets[0], ast.Name)
            if index + 1 < len(tree.body) and isinstance(tree.body[index + 1], ast.With):
                _archive_consumer(tree, index, statement.targets[0].id)
            else:
                _consume(tree.body[index + 1], statement.targets[0].id)
            download(value)
        elif isinstance(value, ast.Dict) and any(
            isinstance(item, ast.Call) and ast.unparse(item.func) == 'edi.download_data'
            for item in value.values
        ):
            assert len(statement.targets) == 1
            target = statement.targets[0]
            assert isinstance(target, ast.Name)
            writes = [
                item
                for item in ast.walk(tree)
                if isinstance(item, ast.Name)
                and item.id == target.id
                and isinstance(item.ctx, (ast.Store, ast.Del))
            ]
            assert writes == [target]
            assert all(
                isinstance(key, ast.Constant) and isinstance(key.value, str) for key in value.keys
            )
            assert len({key.value for key in value.keys}) == len(value.keys)
            loop = tree.body[index + 1]
            assert isinstance(loop, ast.For)
            assert ast.unparse(loop.iter) == target.id + '.items()'
            assert isinstance(loop.target, ast.Tuple) and len(loop.target.elts) == 2
            assert all(isinstance(item, ast.Name) for item in loop.target.elts)
            _consume(loop.body[0], loop.target.elts[1].id)
            for item in value.values:
                download(item)
    declared = {
        item
        for item in ast.walk(tree)
        if isinstance(item, ast.Call) and ast.unparse(item.func) == 'edi.download_data'
    }
    assert declared == reached and observed, (
        'Every download must reach its adjacent model consumer'
    )
    assert len(observed) == len(set(observed)), 'Each required input is downloaded once'
    constructors = [
        statement
        for statement in tree.body
        if isinstance(statement, ast.Assign)
        and isinstance(statement.value, ast.Call)
        and ast.unparse(statement.value.func) == 'edi.Project'
    ]
    assert len(constructors) == 1
    assert len(constructors[0].targets) == 1
    assert ast.unparse(constructors[0].targets[0]) == 'project'
    assert constructors[0].lineno < min(item.lineno for item in declared)
    return observed
