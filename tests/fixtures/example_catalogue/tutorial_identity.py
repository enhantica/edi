"""Identify a literal project path or the generated notebook's adjacent download/load."""

import ast


def load_paths(source):
    tree = ast.parse(source)
    paths = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr == 'load' and ast.unparse(node.func.value).endswith('Project'):
            assert len(node.args) == 1 and not node.keywords, (
                'A tutorial must load exactly one identified project without keyword substitutions'
            )
            argument = node.args[0]
            if isinstance(argument, ast.Constant):
                assert isinstance(argument.value, str), (
                    'A direct tutorial load must name a literal project path'
                )
                paths.append(argument.value)
                continue
            paths.append(_download_path(tree, node, argument))
    return paths


def _download_path(tree, load, argument):
    assert isinstance(argument, ast.Name), (
        'A downloaded project must load its assignment name directly'
    )
    # Store/Del includes augmented, annotated, destructuring and loop targets,
    # assignment expressions and deletion, rather than just plain ast.Assign.
    writes = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Name)
        and node.id == argument.id
        and isinstance(node.ctx, (ast.Store, ast.Del))
    ]
    assert len(writes) == 1, (
        'A downloaded project must come from one unambiguous assignment without other writes'
    )
    statements = [
        index
        for index, statement in enumerate(tree.body)
        if (
            isinstance(statement, ast.Expr)
            or (
                isinstance(statement, ast.Assign)
                and len(statement.targets) == 1
                and isinstance(statement.targets[0], ast.Name)
            )
        )
        and statement.value is load
    ]
    assert len(statements) == 1 and statements[0] > 0, (
        'A downloaded project load must be a top-level statement after its download assignment'
    )
    assignment = tree.body[statements[0] - 1]
    assert (
        isinstance(assignment, ast.Assign)
        and len(assignment.targets) == 1
        and assignment.targets[0] is writes[0]
    ), 'A downloaded project load must immediately follow its single-name download assignment'
    value = assignment.value
    assert (
        isinstance(value, ast.Call)
        and ast.unparse(value.func) == 'edi.download_data'
        and len(value.args) == 1
        and isinstance(value.args[0], ast.Constant)
        and isinstance(value.args[0].value, str)
        and len(value.keywords) <= 1
        and all(
            keyword.arg == 'destination'
            and isinstance(keyword.value, ast.Constant)
            and isinstance(keyword.value.value, str)
            for keyword in value.keywords
        )
    ), 'A tutorial must load the result of its own explicitly named collection download'
    return '../cli/' + value.args[0].value + '/project'
