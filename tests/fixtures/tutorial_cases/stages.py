"""Observe tutorial effects; owner strategy and external references supply requirements."""

import ast
import re
from contextlib import suppress
from pathlib import Path

from tests.fixtures.tutorial_cases.install_cell import python_syntax


def group(path):
    value = '.' + path.casefold()
    for token, name in [
        ('adp_iso', 'isotropic displacement'),
        ('adp_', 'anisotropic displacement'),
        ('fract_', 'positions'),
        ('occupancy', 'occupancies'),
        ('magnetic_form_factor', 'magnetic form factor'),
        ('moment', 'magnetic moments'),
        ('absorption', 'absorption'),
        ('background_terms', 'background'),
        ('extinction', 'extinction'),
        ('background', 'background'),
        ('point.intensity', 'background'),
        ('calib_twotheta_offset', 'zero shift'),
        ('calib_', 'calibration'),
        ('asym_', 'peak asymmetry'),
        ('rise_alpha_', 'peak asymmetry'),
        ('decay_beta_', 'peak asymmetry'),
        ('.peak.', 'peak widths'),
        ('broad_', 'peak widths'),
        ('.cell.', 'cell'),
        ('.scale', 'scale'),
    ]:
        if token in value:
            return name
    return 'other: ' + path


def observe(source, bindings=None):  # noqa: PLR0915 - finite AST effects kept in execution order
    source = python_syntax(source)
    tree = ast.parse(source)
    aliases = {}
    objects = dict(bindings or {})
    # Read the saved starting model locally; never download data or execute tutorial code.
    downloads = re.findall(r"download_data\(['\"]([^'\"]+)", source)
    case = next(
        (
            directory.name
            for name in downloads
            for directory in sorted(
                (Path(__file__).resolve().parents[3] / 'docs/user/cli').iterdir(),
                key=lambda p: -len(p.name),
            )
            if name.startswith(directory.name) and (directory / 'project').is_dir()
        ),
        None,
    )
    if case and 'project' not in objects:
        import edi  # noqa: PLC0415

        saved = Path(__file__).resolve().parents[3] / 'docs/user/cli' / case / 'project'
        objects['project'] = edi.Project.load(str(saved))

    def value(node):  # noqa: PLR0911 - finite expression evaluator
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            return objects[node.id]
        if isinstance(node, ast.Attribute):
            return getattr(value(node.value), node.attr)
        if isinstance(node, ast.Subscript):
            return value(node.value)[value(node.slice)]
        if isinstance(node, ast.Slice):
            return slice(*(value(n) if n else None for n in (node.lower, node.upper, node.step)))
        if isinstance(node, (ast.Tuple, ast.List)):
            return [value(item) for item in node.elts]
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            left, right = value(node.left), value(node.comparators[0])
            if isinstance(node.ops[0], ast.NotEq):
                return left != right
            if isinstance(node.ops[0], ast.Eq):
                return left == right
            raise ValueError('Unsupported tutorial comparison')
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            return not value(node.operand)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            constructor = {'range': range, 'list': list, 'tuple': tuple}.get(node.func.id)
            if constructor:
                return constructor(*(value(item) for item in node.args))
        raise ValueError('Unsupported tutorial expression: ' + ast.unparse(node))

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
        for node in statements:  # noqa: PLR1702 - ordered AST statement effects
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue  # A definition is not an executed teaching stage.
            if isinstance(node, ast.For):
                iterable = node.iter
                if ast.unparse(iterable).endswith('.items()') and not any(
                    (isinstance(item, ast.Attribute) and item.attr == 'free')
                    or (
                        isinstance(item, ast.Call)
                        and any(
                            token in ast.unparse(item.func)
                            for token in ['fit', 'display', 'constraints', 'aliases']
                        )
                    )
                    for statement in node.body
                    for item in ast.walk(statement)
                ):
                    continue  # Data-file construction has no stage effect.

                if path(iterable) == 'project.free_parameters':
                    members = [(parameter, None) for parameter in sorted(active)]
                    if not members:
                        continue
                elif isinstance(iterable, (ast.Tuple, ast.List)):
                    members = []
                    for item in iterable.elts:
                        try:
                            obj = value(item)
                        except KeyError:
                            obj = None
                        members.append((path(item), obj))
                else:
                    try:
                        population = list(value(iterable))
                    except KeyError:
                        population = None
                    if population is None:
                        members = [(path(iterable) + '[*]', None)]
                    else:
                        members = []
                        base = iterable
                        if isinstance(base, ast.Subscript) and isinstance(base.slice, ast.Slice):
                            base = base.value
                        if (
                            isinstance(base, ast.Call)
                            and isinstance(base.func, ast.Name)
                            and base.func.id in {'list', 'tuple'}
                        ):
                            base = base.args[0]
                        for i, obj in enumerate(population):
                            if isinstance(obj, (str, int, float, bool)):
                                member = repr(obj)
                            else:
                                key = (
                                    i
                                    if path(base).endswith(('.background', '.background_terms'))
                                    else getattr(obj, 'id', getattr(obj, 'name', i))
                                )
                                member = f'{path(base)}[{key!r}]'
                            members.append((member, obj))
                old_aliases, old_objects = aliases.copy(), objects.copy()
                for parameter, obj in members:
                    if not isinstance(node.target, ast.Name):
                        raise TypeError('Tutorial loop target must be a name')
                    aliases[node.target.id] = parameter
                    if obj is not None:
                        objects[node.target.id] = obj
                    visit(node.body, context + ' ' + path(iterable))
                aliases.clear()
                aliases.update(old_aliases)
                objects.clear()
                objects.update(old_objects)
                visit(node.orelse, context)
                continue
            if isinstance(node, ast.If):
                # Source conditionals with two different fit paths need an explicit tutorial
                # adaptation; preserve both lexical branches rather than silently dropping one.
                if 'importlib.util.find_spec' in ast.unparse(node.test):
                    continue  # Notebook installation is outside the scientific stage sequence.
                condition = value(node.test)
                visit(node.body if condition else node.orelse, context)
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
                        with suppress(KeyError):
                            objects[target.id] = value(node.value)
                    if isinstance(target, ast.Attribute) and target.attr == 'free':
                        parameter = path(target.value)
                        category = group(parameter + ' ' + context)
                        setting = value(node.value)
                        if setting is True:
                            active.add(parameter)
                            freed.append(category)
                            events.append({
                                'kind': 'free',
                                'group': category,
                                'line': node.lineno,
                                'parameter': parameter,
                                'collective': bool(context.strip()),
                            })
                        elif setting is False:
                            if parameter in active:
                                fixed.append(category)
                            active.discard(parameter)
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
                    events.append({
                        'kind': 'fit',
                        'line': call.lineno,
                        'operation': name.rsplit('.', 1)[-1],
                    })
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
    return {'events': events, 'cycles': cycles, 'free_before': free_before, 'source': source}


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


APP_CATEGORIES = {
    'Cell': 'cell',
    'Linked structures': 'scale',
    'Instrument': 'calibration',
    'Background': 'background',
    'Atomic coordinates': 'positions',
    'Atomic displacement': 'isotropic displacement',
    'Atomic occupancies': 'occupancies',
    'Peak broadening': 'peak widths',
    'Peak asymmetry': 'peak asymmetry',
    'Magnetic moments': 'magnetic moments',
    'Extinction': 'extinction',
}


def app_population(case):
    """Read offered members from the saved model, independently of replay expectations."""
    import edi  # noqa: PLC0415

    root = Path(__file__).resolve().parents[3]
    project = edi.Project.load(str(root / 'docs/user/cli' / case / 'project'))
    population = {}
    for kind, blocks in [('structure', project.structures), ('experiment', project.experiments)]:  # noqa: PLR1702 - finite model walk
        for block in blocks:
            for owner in [
                'cell',
                'atom_sites',
                'atom_site_aniso',
                'atom_site_moment',
                'magnetic_form_factor',
                'instrument',
                'peak',
                'linked_structures',
                'background',
                'background_terms',
                'extinction',
                'absorption',
            ]:
                holder = getattr(block, owner, None)
                if holder is None:
                    continue
                try:
                    items = [
                        (str(getattr(item, 'id', getattr(item, 'structure_id', i))), item)
                        for i, item in enumerate(holder)
                    ]
                except TypeError:
                    items = [('', holder)]
                for row, item in items:
                    for name in dir(item):
                        if name.startswith('_'):
                            continue
                        parameter = getattr(item, name)
                        if (
                            not hasattr(parameter, 'free')
                            or parameter.symmetry_constrained
                            or parameter.user_constrained
                        ):
                            continue
                        prefix = kind if len(blocks) == 1 else block.name
                        path = '.'.join(v for v in [prefix, owner, row, name] if v)
                        population[path] = (group(path), block.name)
    return population


def app_cycles(steps, population=None):  # noqa: PLR0912, PLR0914, PLR0915 - ordered manifest effects
    def canonical(value):
        return re.sub(r"\[['\"]?([^]\"']+)['\"]?\]", r'.\1', value)

    population = dict(population or {})
    for step in steps:
        check = step.get('check', '')
        if check.startswith(('tick:', 'untick:', 'free:', 'fixed:')):
            for spelling in check.split(':', 1)[1].split(','):
                parameter = canonical(spelling)
                population.setdefault(parameter, (group(parameter), ''))
    active, freed, fixed = set(), set(), set()
    expressions, pending, seen = {}, set(), set()
    cycles = []
    awaiting_completion = False
    for step in steps:
        check = step.get('check', '')
        if check.startswith(('tick:', 'untick:', 'free:', 'fixed:', 'free-choice:')):
            if check.startswith('free-choice:'):
                _, action, category, *block = check.split(':')
                if category == 'All categories':
                    parameters = set(population) | active
                else:
                    if category not in APP_CATEGORIES:
                        raise ValueError('Unknown app free category: ' + category)
                    parameters = {
                        p
                        for p, (g, b) in population.items()
                        if (
                            g == APP_CATEGORIES[category]
                            or (category == 'Atomic displacement' and 'displacement' in g)
                            or (category == 'Instrument' and g == 'zero shift')
                        )
                        and (not block or b == block[0])
                    }
                    if not parameters:
                        raise ValueError('No independently observed members for ' + check)
                setting = action == 'free'
            else:
                action, parameters = check.split(':', 1)
                parameters = {canonical(p) for p in parameters.split(',')}
                setting = action in {'tick', 'free'}
            categories = {population[p][0] for p in parameters if setting or p in active}
            (freed if setting else fixed).update(categories)
            if setting:
                active.update(parameters)
            else:
                active.difference_update(parameters)
        if check.startswith('field:constraint.expression.'):
            row, expression = check.removeprefix('field:constraint.expression.').split('=', 1)
            expression = expression.strip()
            if re.fullmatch(r'[^=]+=[^=]+', expression):
                expressions[row] = expression
            else:
                expressions.pop(row, None)
        if check.startswith('constraint:'):
            expression = check.split(':', 1)[1].strip()
            if re.fullmatch(r'[^=]+=[^=]+', expression):
                pending.add(expression)
        button = step.get('target') == 'statusBar.fit.button'
        completed = check in {'fitted', 'fit-done'}
        if completed and awaiting_completion and not button:
            awaiting_completion = False
            continue
        if button or completed:
            cycles.append({
                'freed': sorted(freed),
                'fixed': sorted(fixed),
                'active': sorted({population[p][0] for p in active}),
                'constraints': len(pending | (set(expressions.values()) - seen)),
            })
            freed.clear()
            fixed.clear()
            pending.clear()
            seen.update(expressions.values())
            awaiting_completion = button and not completed
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
