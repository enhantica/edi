"""Observe tutorial effects; owner strategy and external references supply requirements."""

import ast
import re

from tests.fixtures.tutorial_cases.install_cell import python_syntax


def group(path):
    value = path.casefold()
    for token, name in [
        ('adp_iso', 'isotropic displacement'),
        ('adp_', 'anisotropic displacement'),
        ('fract_', 'positions'),
        ('occupancy', 'occupancies'),
        ('moment', 'magnetic moments'),
        ('extinction', 'extinction'),
        ('background', 'background'),
        ('point.intensity', 'background'),
        ('calib_twotheta_offset', 'zero shift'),
        ('calib_', 'calibration'),
        ('.peak.', 'peak widths'),
        ('broad_', 'peak widths'),
        ('asym_', 'peak asymmetry'),
        ('.cell.', 'cell'),
        ('.scale', 'scale'),
    ]:
        if token in value:
            return name
    return 'other: ' + path


def observe(source):  # noqa: PLR0915 - finite AST effects kept in execution order
    source = python_syntax(source)
    tree = ast.parse(source)
    aliases = {}
    events = []
    cycles = []
    free_before = []
    active = set()
    freed = []
    fixed = []
    constraints = []
    constraint_aliases = {}

    def path(node):
        value = ast.unparse(node)
        for name, replacement in sorted(aliases.items(), key=lambda pair: -len(pair[0])):
            value = re.sub(
                r'\b' + re.escape(name) + r'\b', lambda _match, bound=replacement: bound, value
            )
        return value

    def visit(statements, context=''):  # noqa: PLR0912, PLR0915 - explicit supported AST nodes
        for node in statements:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue  # A definition is not an executed teaching stage.
            if isinstance(node, ast.For):
                iterable = node.iter
                count = 1
                if (
                    isinstance(iterable, ast.Call)
                    and isinstance(iterable.func, ast.Name)
                    and iterable.func.id == 'range'
                ) and all(
                    isinstance(item, ast.Constant) and type(item.value) is int
                    for item in iterable.args
                ):
                    count = len(range(*(item.value for item in iterable.args)))
                if isinstance(node.target, ast.Name):
                    aliases[node.target.id] = ast.unparse(iterable) + '[*]'
                for _ in range(count):
                    visit(node.body, context + ' ' + ast.unparse(iterable))
                visit(node.orelse, context)
                continue
            if isinstance(node, ast.If):
                # Source conditionals with two different fit paths need an explicit tutorial
                # adaptation; preserve both lexical branches rather than silently dropping one.
                visit(node.body, context)
                visit(node.orelse, context)
                continue
            if isinstance(node, (ast.With, ast.AsyncWith)):
                visit(node.body, context)
                continue
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and isinstance(
                        node.value, (ast.Name, ast.Attribute, ast.Subscript)
                    ):
                        aliases[target.id] = path(node.value)
                    if (
                        isinstance(target, ast.Attribute)
                        and target.attr == 'free'
                        and isinstance(node.value, ast.Constant)
                    ):
                        parameter = path(target.value)
                        category = group(parameter + ' ' + context)
                        if node.value.value is True:
                            active.add(parameter)
                            freed.append(category)
                            events.append({
                                'kind': 'free',
                                'group': category,
                                'line': node.lineno,
                                'parameter': parameter,
                                'collective': bool(context.strip()),
                            })
                        elif node.value.value is False:
                            active.discard(parameter)
                            fixed.append(category)
                            events.append({
                                'kind': 'fix',
                                'group': category,
                                'line': node.lineno,
                                'parameter': parameter,
                                'collective': bool(context.strip()),
                            })
            for call in (item for item in ast.walk(node) if isinstance(item, ast.Call)):
                name = ast.unparse(call.func)
                if (
                    name.endswith(('.analysis.fit', '.fit', '.fit_joint', '.fit_sequential'))
                    and '.display.' not in name
                ):
                    cycles.append({
                        'freed': sorted(set(freed)),
                        'fixed': sorted(set(fixed)),
                        'active': sorted({group(value) for value in active}),
                        'constraints': len(constraints),
                    })
                    free_before.append(sorted(active))
                    freed.clear()
                    fixed.clear()
                    constraints.clear()
                    events.append({'kind': 'fit', 'line': call.lineno})
                elif name.endswith('.display.pattern'):
                    events.append({'kind': 'pattern', 'line': call.lineno})
                elif name.endswith(('.display.fit.correlations', '.display.correlations')):
                    events.append({'kind': 'correlations', 'line': call.lineno})
                elif name.endswith('.display.fit.results'):
                    events.append({'kind': 'results', 'line': call.lineno})
                elif '.aliases.' in name and name.endswith(('.create', '.add', '.append')):
                    keywords = {item.arg: item.value for item in call.keywords}
                    if isinstance(keywords.get('id'), ast.Constant) and 'param' in keywords:
                        constraint_aliases[keywords['id'].value] = path(keywords['param'])
                elif '.constraints.' in name and name.endswith(('.create', '.add', '.append')):
                    expression = next(
                        (
                            item.value.value
                            for item in call.keywords
                            if item.arg == 'expression' and isinstance(item.value, ast.Constant)
                        ),
                        '',
                    )
                    constraints.append(expression)
                    events.append({
                        'kind': 'constraint',
                        'line': call.lineno,
                        'expression': expression,
                        'dependent': constraint_aliases.get(expression.split('=')[0].strip()),
                    })

    visit(tree.body)
    return {'events': events, 'cycles': cycles, 'free_before': free_before}


def assert_teaching_stages(plan):
    events = plan['events']
    fits = [index for index, item in enumerate(events) if item['kind'] == 'fit']
    assert len(fits) >= 2, 'Gate 3: a fitting tutorial teaches at least two actual fit stages'
    assert any(item['kind'] == 'pattern' for item in events[: fits[0]]), (
        'Gate 3: the pattern at starting values is displayed before the first fit'
    )
    first = set(plan['free_before'][0])
    assert any(set(parameters) - first for parameters in plan['free_before'][1:]), (
        'Gate 3: a later stage frees more parameters; all cannot be free before the first fit'
    )
    for start, end in zip(fits, fits[1:] + [len(events)], strict=True):
        after = events[start + 1 : end]
        assert any(item['kind'] == 'pattern' for item in after), (
            'Gate 3: each fit stage displays its resulting pattern before the next fit'
        )
        assert any(item['kind'] == 'results' for item in after), (
            'Gate 3: each fit stage displays its fit-results table'
        )


def assert_correlation_lesson(plan):
    wanted = iter(['fit', 'correlations', 'constraint', 'fit', 'correlations'])
    next_kind = next(wanted)
    for event in plan['events']:
        if event['kind'] == next_kind:
            next_kind = next(wanted, None)
            if next_kind is None:
                return
    raise AssertionError(
        'Gate 3: teach fit, show correlations, add a constraint, refit and show correlations again'
    )


def app_cycles(steps):
    active, freed, fixed = set(), set(), set()
    pending_constraints = 0
    cycles = []
    for step in steps:
        check = step.get('check', '')
        for prefix, target in [('free:', freed), ('fixed:', fixed)]:
            if check.startswith(prefix):
                groups = {group('parameter.' + value) for value in check[len(prefix) :].split(',')}
                target.update(groups)
                if prefix == 'free:':
                    active.update(groups)
                else:
                    active.difference_update(groups)
        if check.startswith('constraint:'):
            pending_constraints += 1
        if step.get('target') == 'statusBar.fit.button' or check in {'fitted', 'fit-done'}:
            cycles.append({
                'freed': sorted(freed),
                'fixed': sorted(fixed),
                'active': sorted(active),
                'constraints': pending_constraints,
            })
            freed.clear()
            fixed.clear()
            pending_constraints = 0
    return cycles


def prose_cycles(source):
    # Observe imperative app instructions, never a heading or prose saying "fit results".
    source = re.sub(r'[*`_]', '', source)
    phrases = [
        ('isotropic displacement', r'\b(?:isotropic|adp.iso|biso)\b'),
        ('anisotropic displacement', r'\b(?:anisotropic|adp.11|bij)\b'),
        ('positions', r'\b(?:positions?|coordinates|fract.[xyz])\b'),
        ('occupancies', r'\boccupanc'),
        ('magnetic moments', r'\b(?:moments?|magnetic)\b'),
        ('extinction', r'\bextinction\b'),
        ('background', r'\bbackground\b'),
        ('zero shift', r'\b(?:zero|offset)\b'),
        ('calibration', r'\bcalibration\b'),
        ('peak widths', r'\b(?:widths?|profile|peaks?)\b'),
        ('cell', r'\bcell\b'),
        ('scale', r'\bscale\b'),
    ]
    active, freed, fixed = set(), set(), set()
    pending_constraints = 0
    cycles = []
    for paragraph in source.split('\n\n'):
        lower = paragraph.casefold()
        groups = {name for name, pattern in phrases if re.search(pattern, lower)}
        if re.search(r'\bfree\b', lower):
            active.update(groups)
            freed.update(groups)
        if re.search(r'\bfix\b', lower):
            active.difference_update(groups)
            fixed.update(groups)
        if re.search(r'\b(?:add|create)\b.*\bconstraint\b', lower):
            pending_constraints += 1
        if re.search(r'\b(?:click|press|run|perform)\s+(?:the\s+)?fit\b(?!\s+results)', lower):
            cycles.append({
                'freed': sorted(freed),
                'fixed': sorted(fixed),
                'active': sorted(active),
                'constraints': pending_constraints,
            })
            freed.clear()
            fixed.clear()
            pending_constraints = 0
    return cycles
