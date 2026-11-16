"""Recipe effects and comparisons, independent of the built-in translator and manifest."""

import copy
import math
import re

import gemmi


def canonical(path):
    return re.sub(r'[\]"\']', '', path.replace('[', '.'))


def recipe_action_error(translate, baseline, recipe, step_index, action_index):
    """A redundant literal write must still consume its exact source operand and target."""
    item = recipe['steps'][step_index]
    action = item['actions'][action_index]

    def attempt(changed):
        try:
            result = translate(changed)
        except (ValueError, RuntimeError, SystemExit) as error:
            named = (
                item['id'] in str(error)
                or any(
                    word in str(error).casefold()
                    for word in ['action', 'recipe', 'plan', 'translate']
                )
                or any(
                    'step ' + repr(row['check']) in str(error)
                    for row in baseline
                    if row.get('check')
                )
            )
            return None, None if named else 'unnamed refusal'
        except Exception as error:  # noqa: BLE001 - an arbitrary crash never proves consumption
            return None, type(error).__name__
        if not isinstance(result, list) or not all(isinstance(row, dict) for row in result):
            return None, 'malformed translation'
        return result, None

    changed = copy.deepcopy(recipe)
    del changed['steps'][step_index]['actions'][action_index]
    observed, error = attempt(changed)
    if error or observed is None or observed != baseline:
        return error
    match = re.fullmatch(r'(fill|choose-token):([^=]+)=(.*)', action)
    if match:
        kind, target, value = match.groups()
        check = 'field' if kind == 'fill' else 'token'
    elif action.startswith('type:') and action_index:
        kind, target, value, check = 'type', item['actions'][action_index - 1], action[5:], 'pick'
        if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_.]*', target):
            return 'no effect'
    else:
        return 'no effect'
    # This is a sensitivity probe, not a new physical expected value or a generated pin.
    if re.fullmatch(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?', value):
        replacement = format(float(value) + max(1, abs(float(value))) * 0.125 + 0.371, '.17g')
    else:
        replacement = value + '__source_operand_probe__'
    changed = copy.deepcopy(recipe)
    changed['steps'][step_index]['actions'][action_index] = (
        'type:' + replacement if kind == 'type' else kind + ':' + target + '=' + replacement
    )
    observed, error = attempt(changed)
    if error or observed is None:
        return error
    if not any(
        row.get('target') == target
        and row.get('check') == check + ':' + target + '=' + replacement
        for row in observed
    ):
        return 'literal operand or target ignored'
    return None


def significant(item, action):  # noqa: PLR0911 - finite action vocabulary fails closed
    if action.startswith((
        'fill:createProject.name=',
        'fill:createProject.title=',
        'fill:createProject.location=',
    )):
        return False  # Workspace naming/location are supplied by the learner or capture host.
    if re.fullmatch(
        r'(?:tick|untick):(?:structures?|experiments?)(?:\[[\w.-]+\])?\.[\w.\[\]\'-]+', action
    ):
        return True
    if action.startswith('choose:'):
        actions = item.get('actions', [])
        positions = [index for index, value in enumerate(actions) if value == action]
        filters = positions and all(
            index > 0 and actions[index - 1] in {'parameters.category', 'parameters.datablock'}
            for index in positions
        )
        if filters and not any(
            value in {'parameters.freeHeader.free', 'parameters.freeHeader.fixed'}
            for value in actions
        ):
            return False
    if action.startswith(('fill:', 'type:', 'choose:', 'choose-token:')):
        return True
    if action in {
        'parameters.freeHeader.free',
        'parameters.freeHeader.fixed',
        'background.estimate',
        'statusBar.fit.button',
    }:
        return True
    if item['id'] in {'group-free-all', 'data-from-file', 'data-from-file-closed'} and action in {
        'parameters.freeHeader',
        'experiments.load',
        'key:Escape',
    }:
        return True
    if action.startswith((
        'reveal:',
        'expand:',
        'show:',
        'key:',
        'platform:',
        'theme:',
        'pin-time:',
    )):
        return False  # Presentation/commit keys fold into the corresponding model action.
    inert = {
        'aliases.append',
        'constraints.append',
        'atomSites.append',
        'background.append',
        'excludedRegions.append',
        'background_estimate.use_model',
        'createProject.accept',
        'experimentType.beamMode',
        'experimentType.radiationProbe',
        'experimentType.sampleForm',
        'experiments.create',
        'experiments.load',
        'experiments.load.dataWeb',
        'experiments.load.experimentWeb',
        'home.start',
        'onlineLoad.row.0',
        'onlineLoad.search',
        'onlineLoad.source',
        'parameters.category',
        'parameters.clearFilters',
        'parameters.datablock',
        'parameters.freeHeader',
        'project.create',
        'spaceGroup.nameHM',
        'structures.create',
        'structures.load',
        'structures.load.web',
        'wait-fit',
        'wait-online',
        'close-fit-results',
        'appBar.tab.analysis',
        'appBar.tab.experiment',
        'appBar.tab.report',
        'appBar.tab.structure',
        'sideBar.tab.basic',
        'sideBar.tab.extras',
        'mainArea.tab.correlations',
        'mainArea.tab.pattern',
        'mainArea.analysis.tab.correlations',
        'mainArea.analysis.tab.fitting',
    }
    if action in inert or re.fullmatch(
        r'(alias\.parameter|atomSite\.typeSymbol|atomSite\.wyckoffLetter|atomSiteAdp\.type)\.\d+',
        action,
    ):
        return False  # Focus/construction/waits are checked by fields, state and navigation.
    raise ValueError('Unclassified docs recipe action: ' + action)


def boundary_contracts(recipe):  # noqa: PLR0912, PLR0914, PLR0915 - finite docs recipe effects
    aliases, constraints, regions, points, values, estimate = {}, {}, {}, {}, {}, {}
    alias_ids, alias_paths, names = {}, {}, {}
    chosen = ''
    selected = ''
    seen_estimate = False
    estimate_calls = 0
    experiment_name = ''
    experiment_types = {}
    wyckoff = {}
    wyckoff_row = ''
    boundaries = []
    fit = 0
    for item in recipe['plan']['steps']:
        for action in item['actions']:
            if action.startswith('fill:'):
                target, value = action[5:].split('=', 1)
                if target == 'experiments.name.0':
                    experiment_name = value
                if experiment_name and target.startswith(('peak.', 'instrument.')):
                    values[experiment_name + '.' + target] = float(value)
                match = re.fullmatch(r'alias.id.(\d+)', target)
                if match:
                    alias_ids[match[1]] = value
                match = re.fullmatch(r'constraint.expression.(\d+)', target)
                if match:
                    lhs = value.split('=', 1)[0].strip()
                    constraints[lhs] = re.sub(r'\s+', '', value)
                match = re.fullmatch(r'excludedRegion.(start|end).(\d+)', target)
                if match:
                    regions.setdefault(match[2], {})[match[1]] = float(value)
                match = re.fullmatch(r'background.(position|intensity).(\d+)', target)
                if match:
                    points.setdefault(match[2], {})[match[1]] = float(value)
                if target == 'parameters.nameFilter':
                    selected = value
                if target == 'parameters.value.0':
                    values[canonical(selected)] = float(value)
                if target.startswith('background_estimate.'):
                    estimate[target.split('.', 1)[1]] = int(value) if value.isdigit() else value
                match = re.fullmatch(r'atomSite.label.(\d+)', target)
                if match:
                    names[match[1]] = value
                match = re.fullmatch(r'atomSite.occupancy.(\d+)', target)
                if match:
                    values['lbco.atom_site.' + names[match[1]] + '.occupancy'] = float(value)
            if action.startswith('atomSite.wyckoffLetter.'):
                wyckoff_row = action.rsplit('.', 1)[1]
            elif action.startswith('type:') and wyckoff_row:
                wyckoff[names[wyckoff_row]] = action[5:].rstrip(':')
                wyckoff_row = ''
            if action.startswith('choose-token:experimentType.'):
                control, value = action.split('=', 1)
                key = {
                    'sampleForm': 'sample_form',
                    'beamMode': 'beam_mode',
                    'radiationProbe': 'radiation_probe',
                }[control.split('.', 1)[1]]
                experiment_types[key] = value
            if action.startswith('alias.parameter.'):
                chosen = action.rsplit('.', 1)[1]
            if action.startswith('type:') and chosen:
                alias_paths[chosen] = action[5:]
                chosen = ''
            if action.startswith('choose-token:background_estimate.'):
                target, value = action.split('=', 1)
                estimate[target.split('.', 1)[1]] = value
            if action == 'background.estimate':
                seen_estimate = True
                estimate_calls += 1
                points.clear()  # ADR-0040: estimation replaces the manual point rows.
        aliases.update({name: alias_paths[i] for i, name in alias_ids.items() if i in alias_paths})
        if 'wait-fit' not in item['actions']:
            continue
        title, paths = recipe['fits'][fit]
        fit += 1
        state = {
            'stage': fit,
            'title': title,
            'free': sorted(
                recipe.get('estimated_background_paths', {}).get(canonical(p), canonical(p))
                if seen_estimate
                else canonical(p)
                for p in paths
            ),
            'aliases': copy.deepcopy(aliases),
            'constraints': copy.deepcopy(constraints),
            'values': copy.deepcopy(values),
            'experiment_types': copy.deepcopy(experiment_types),
            'wyckoff': copy.deepcopy(wyckoff),
            'regions': copy.deepcopy(regions),
            'points': copy.deepcopy(points),
            'estimate': copy.deepcopy(estimate) if seen_estimate else {},
            'estimate_calls': estimate_calls,
            'file_required': any(
                step['id'] == 'data-from-file' for step in recipe['plan']['steps']
            ),
        }
        boundaries.append(state)
        # Pre-fit resets are obligations; fitted values are not correctness pins.
        values = {key: value for key, value in values.items() if key.endswith('.occupancy')}
        for point in points.values():
            point.pop('intensity', None)
    return boundaries


def _block(text):
    return gemmi.cif.read_string(
        text if re.search(r'^data_', text, re.MULTILINE) else 'data_observed\n' + text
    ).sole_block()


def state_errors(expected, actual):  # noqa: PLR0912, PLR0915 - finite independent model fields
    errors = []
    if expected.get('file_required') and not actual.get('fileAlternativeSeen'):
        errors.append('From file alternative not shown')
    if sorted(canonical(path) for path in actual['free']) != expected['free']:
        errors.append('free set')
    analysis = _block(actual['analysis'])
    aliases = {
        gemmi.cif.as_string(row[0]): gemmi.cif.as_string(row[1])
        for row in analysis.find(['_alias.id', '_alias.parameter_unique_name'])
    }
    if aliases != expected['aliases']:
        errors.append('aliases')
    constraints = {
        expr.split('=', 1)[0].strip(): re.sub(r'\s+', '', expr)
        for row in analysis.find(['_constraint.expression'])
        for expr in [gemmi.cif.as_string(row[0])]
    }
    if constraints != expected['constraints']:
        errors.append('relation expressions')
    if actual['targets'].count('background.estimate') != expected['estimate_calls']:
        errors.append('background estimate action count')
    if actual.get('applied_estimates', 0) != expected['estimate_calls']:
        errors.append('background estimate model replacement count')
    for key, value in expected['values'].items():
        if key not in actual['values'] or abs(actual['values'][key] - value) > 1e-9:
            errors.append('value reset: ' + key)
    if expected.get('wyckoff'):
        sites = [
            (gemmi.cif.as_string(row[0]), gemmi.cif.as_string(row[1]))
            for structure in actual.get('structures', [])
            for row in _block(structure['text']).find([
                '_atom_site.id',
                '_atom_site.wyckoff_letter',
            ])
        ]
        if len(sites) != len(expected['wyckoff']) or dict(sites) != expected['wyckoff']:
            errors.append('initial Wyckoff choices')
    if expected.get('experiment_types') and len(actual['experiments']) != 1:
        errors.append('initial experiment identity')
    for experiment in actual['experiments']:
        block = _block(experiment['text'])
        for field, value in expected.get('experiment_types', {}).items():
            observed = block.find_value('_experiment_type.' + field)
            if observed is None or gemmi.cif.as_string(observed) != value:
                errors.append('initial experiment ' + field)
        if expected['regions']:
            rows = [
                [float(row[0]), float(row[1])]
                for row in block.find(['_excluded_region.start', '_excluded_region.end'])
            ]
            want = [
                [v['start'], v['end']]
                for _i, v in sorted(expected['regions'].items(), key=lambda x: int(x[0]))
            ]
            if rows != want:
                errors.append('excluded regions')
        if expected['points']:
            rows = list(block.find(['_background.position', '_background.intensity']))
            if len(rows) != len(expected['points']):
                errors.append('background point count')
            else:
                errors.extend(
                    'background point ' + field
                    for i, row in enumerate(rows)
                    for field, value in expected['points'][str(i)].items()
                    if abs(gemmi.cif.as_number(row[0 if field == 'position' else 1]) - value)
                    > 1e-7
                )
        if expected['estimate']:
            want = expected['estimate']
            if 'n_points' in want and experiment['n_points'] != want['n_points']:
                errors.append('background estimate settings')
            if 'use_model' in want and experiment['use_model'] != want['use_model']:
                errors.append('background residual/model setting')
            rows = list(
                block.find(['_background.id', '_background.position', '_background.intensity'])
            )
            count = want.get('n_points', experiment['n_points'])
            if len(rows) != count or [gemmi.cif.as_string(row[0]) for row in rows] != [
                str(i + 1) for i in range(count)
            ]:
                errors.append('background estimate point identities')
            coordinates = [
                (gemmi.cif.as_number(row[1]), gemmi.cif.as_number(row[2])) for row in rows
            ]
            if not all(math.isfinite(value) for row in coordinates for value in row) or any(
                a[0] >= b[0] for a, b in zip(coordinates, coordinates[1:], strict=False)
            ):
                errors.append('background estimate point geometry')
    return errors
