"""Observe tutorial effects; owner strategy and external references supply requirements."""

import ast
import re
from collections import UserDict
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


def observe(source, bindings=None):  # noqa: PLR0914, PLR0915 - finite AST effects kept in execution order
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
    loaded_project = any(
        isinstance(node, ast.Call) and ast.unparse(node.func).endswith('.Project.load')
        for node in ast.walk(tree)
    )
    if loaded_project and 'project' in objects:
        constraints = [str(row.expression) for row in objects['project'].analysis.constraints]
    constraint_aliases = {}
    previous_active = set()

    def path(node):
        value = ast.unparse(node)
        for name, replacement in sorted(aliases.items(), key=lambda pair: -len(pair[0])):
            value = re.sub(
                r'\b' + re.escape(name) + r'\b', lambda _match, bound=replacement: bound, value
            )
        return value

    def visit(statements, context=''):  # noqa: PLR0912, PLR0914, PLR0915 - explicit supported AST nodes
        nonlocal previous_active
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
                    if isinstance(target, ast.Attribute) and target.attr == 'adp_type':
                        site_path = path(target.value)
                        selected = value(node.value)
                        value(target.value).adp_type = selected
                        prefix = (
                            site_path.replace('.atom_sites[', '.atom_site_aniso[') + '.'
                            if selected in {'Biso', 'Uiso'}
                            else site_path + '.adp_iso'
                        )
                        removed = {p for p in active if p.startswith(prefix)}
                        active.difference_update(removed)
                        events.append({
                            'kind': 'replace',
                            'line': node.lineno,
                            'retired': sorted(removed),
                        })
                    if isinstance(target, ast.Attribute) and target.attr == 'free':
                        parameter = path(target.value)
                        category = group(parameter + ' ' + context)
                        setting = value(node.value)
                        if setting is True:
                            if parameter not in active:
                                freed.append(category)
                            active.add(parameter)
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
                        'freed': sorted({group(p) for p in active - previous_active}),
                        'fixed': sorted({group(p) for p in previous_active - active}),
                        'active': sorted({group(value) for value in active}),
                        'constraints': len(constraints),
                    })
                    previous_active = active.copy()
                    free_before.append(sorted(active))
                    freed.clear()
                    fixed.clear()
                    constraints.clear()
                    events.append({
                        'kind': 'fit',
                        'line': call.lineno,
                        'operation': name.rsplit('.', 1)[-1],
                    })
                elif name.endswith('.background.auto_estimate'):
                    prefix = path(call.func.value) + '['
                    retired = {p for p in active if p.startswith(prefix)}
                    active.difference_update(retired)
                    events.append({
                        'kind': 'replace',
                        'line': call.lineno,
                        'retired': sorted(retired),
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
    return {
        'events': events,
        'cycles': cycles,
        'free_before': free_before,
        'source': source,
        'independent': any(
            isinstance(n, ast.Assign)
            and isinstance(n.value, ast.Constant)
            and n.value.value == 'independent'
            and any(ast.unparse(t).endswith('.analysis.fitting_mode') for t in n.targets)
            for n in ast.walk(tree)
        ),
    }


def assert_template_batches(plan):
    fits = [event for event in plan['events'] if event['kind'] == 'fit']
    for index, event in enumerate(fits):
        if event.get('operation') == 'fit_sequential':
            assert index and plan['free_before'][index] == plan['free_before'][index - 1], (
                'Gate 3: a sequential batch reuses its already validated free-parameter template'
            )


def assert_teaching_stages(plan):
    assert_template_batches(plan)
    events = plan['events']
    fits = [
        index
        for index, item in enumerate(events)
        if item['kind'] == 'fit' and item.get('operation') != 'fit_sequential'
    ]
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


class AppPopulation(UserDict):
    """Offered member metadata, with its disposable source model for type-selector changes."""

    def __init__(self, project):
        super().__init__()
        self.project = project
        self.table_names = set()
        self.datablock_names = {
            str(block.name)
            for blocks in [project.structures, project.experiments]
            for block in blocks
        }


def app_population(case=None, *, project=None):  # noqa: PLR0912 - explicit category ownership and eligibility
    """Read offered members from the saved model, independently of replay expectations."""
    import edi  # noqa: PLC0415

    root = Path(__file__).resolve().parents[3]
    if project is None:
        project = edi.Project.load(str(root / 'docs/user/cli' / case / 'project'))
    population = AppPopulation(project)
    reference = (root / 'tests/fixtures/dictionary_display/metadata_reference.hpp').read_text()
    labels = dict(
        re.findall(
            r'\{"([^"\n]+)", "([^"\n]+)", "[^"\n]*", "[^"\n]*"\}',
            reference,
        )
    )
    adp_labels = dict(re.findall(r'\{"atom_site.adp_type", "([^"\n]+)", "([^"\n]+)"\}', reference))
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
                        owner_id = {
                            'atom_sites': 'atom_site',
                            'linked_structures': 'linked_structure',
                        }.get(owner, owner)
                        label = labels.get(owner_id + '.' + name)
                        if owner == 'atom_sites' and name == 'adp_iso':
                            label = adp_labels.get(str(item.adp_type), label)
                        if label and hasattr(parameter, 'free'):
                            population.table_names.add(' '.join(v for v in [row, label] if v))
                            population.table_names.add(
                                ' '.join(v for v in [block.name, row, label] if v)
                            )
                            if owner in {'background', 'background_terms'}:
                                population.table_names.add('Background ' + row + ' ' + label)
                        if (
                            owner == 'atom_sites'
                            and name == 'adp_iso'
                            and str(item.adp_type) not in {'Biso', 'Uiso'}
                        ):
                            continue
                        if owner == 'atom_site_aniso':
                            site = block.atom_sites[row]
                            if str(site.adp_type) in {'Biso', 'Uiso'}:
                                continue
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
        value = re.sub(r"\[['\"]?([^]\"']+)['\"]?\]", r'.\1', value)
        if model is not None:
            value = re.sub(r'^(?:structures|experiments)\.', '', value)
            for kind, blocks in [
                ('structure', model.structures),
                ('experiment', model.experiments),
            ]:
                if len(blocks) == 1 and value.startswith(blocks[0].name + '.'):
                    value = kind + value[len(blocks[0].name) :]
        return value

    model = getattr(population, 'project', None)
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
    previous_active = set()
    awaiting_completion = False
    for step in steps:
        check = step.get('check', '')
        type_change = re.fullmatch(r'pick:atomSiteAdp\.type\.(\d+)=(.+)', check)
        if type_change:
            if model is None or len(model.structures) != 1:
                raise ValueError(
                    'ADP type steps require the independently observed selected structure'
                )
            model.structures[0].atom_sites[int(type_change[1])].adp_type = type_change[2]
            population = app_population(project=model)
            active.intersection_update(population)
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
            categories = {
                population[p][0]
                for p in parameters
                if (p not in active if setting else p in active)
            }
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
                'freed': sorted({population[p][0] for p in active - previous_active}),
                'fixed': sorted({group(p) for p in previous_active - active}),
                'active': sorted({population[p][0] for p in active}),
                'constraints': len(pending | (set(expressions.values()) - seen)),
            })
            previous_active = active.copy()
            freed.clear()
            fixed.clear()
            pending.clear()
            seen.update(expressions.values())
            awaiting_completion = button and not completed
    return cycles


def prose_cycles(source, population=None):  # noqa: PLR0912 - finite written instruction grammar
    """Read stage instructions and declared relations; visual markup contributes no actions."""
    source = re.sub(r'<(?:figure|svg)\b.*?</(?:figure|svg)>', '', source, flags=re.DOTALL)
    source = re.sub(r'<[^>]+>', '', source)
    source = re.sub(r'[*`_]', '', source)
    phrases = [
        ('isotropic displacement', r'\b(?:isotropic|adp.iso|b\s*iso|atomic displacements?)\b'),
        ('anisotropic displacement', r'\b(?:anisotropic|adp.11|bij)\b'),
        ('positions', r'\b(?:positions?|coordinates|fract.[xyz])\b'),
        ('occupancies', r'\boccupanc'),
        ('magnetic moments', r'\b(?:moments?|magnetic model)\b'),
        ('magnetic form factor', r'\b(?:j2|form factor)\b'),
        ('extinction', r'\bextinction\b'),
        ('background', r'\bbackground\b'),
        ('zero shift', r'\b(?:zero|offset)\b'),
        ('calibration', r'\bcalibration\b'),
        ('peak widths', r'\b(?:widths?|peak profile|peak broadening)\b'),
        ('peak asymmetry', r'\b(?:peak asymmetry|asymmetry)\b'),
        ('cell', r'\bcell\b'),
        ('scale', r'\b(?:scales?|linked structures)\b'),
    ]
    active, previous, fixed = set(), set(), set()
    pending_constraints = 0
    model = getattr(population, 'project', None)
    context = ''
    cycles = []
    for paragraph in source.split('\n\n'):
        lower = paragraph.casefold().strip()
        if lower.startswith('#'):
            context = lower.lstrip('# ')
            if context == 'add the relations' and model is not None:
                pending_constraints = len({
                    str(row.expression) for row in model.analysis.constraints
                })
            continue
        if re.search(r'\bfix\s+(?:all|every)\s+param', lower):
            fixed.update(active)
            active.clear()
        relation = re.search(r'\bconstrain\s+.+?\bfollow\b', lower, re.DOTALL)
        if relation:
            pending_constraints += 1
            if 'displacement' in lower:
                fixed.add('isotropic displacement')
        setting_type = re.search(r'choose\s+(biso|uiso|beta|bani)\s+as every site', lower)
        if (
            setting_type
            and setting_type[1] in {'beta', 'bani'}
            and 'isotropic displacement' in active
        ):
            active.remove('isotropic displacement')
            fixed.add('isotropic displacement')
        instruction = re.search(
            r'\b(?:tick|clear|untick)\s+free\s+for\b|\bfree\s*[·:]?\s*all\b'
            r'|^(?:[-•]\s*)?(?:free|fix)\s+'
            r'|\b(?:first|second|third|fourth|last|this) stage frees\b',
            lower,
        )
        if instruction:
            command = re.sub(
                r'on structure, choose .+?as every site.s type in the atomic displacement table;?',
                '',
                lower,
            )
            groups = {name for name, pattern in phrases if re.search(pattern, command)}
            if 'instrument' in command:
                groups.add('zero shift' if re.search(r'zero|offset', context) else 'calibration')
            if 'atomic displacement' in command and 'anisotropic' in context:
                groups.discard('isotropic displacement')
                groups.add('anisotropic displacement')
            if 'peak profile' in command and 'asymmetry' in context:
                groups.discard('peak widths')
                groups.add('peak asymmetry')
            if re.search(r'^(?:[-•]\s*)?fix\s+|\b(?:clear|untick)\s+free\s+for', command):
                fixed.update(groups & active)
                active.difference_update(groups)
            else:
                active.update(groups)
        if re.search(r'\b(?:click|press|run|perform)\s+(?:the\s+)?fit\b(?!\s+results)', lower):
            cycles.append({
                'freed': sorted(active - previous),
                'fixed': sorted(fixed | (previous - active)),
                'active': sorted(active),
                'constraints': pending_constraints,
            })
            previous = active.copy()
            fixed.clear()
            pending_constraints = 0
    return cycles
