"""Owner 7101f0fd9 and the app strategy skill, blob 555b7725370d7ea55c8daa6ba0084916dc5ee514.

Independent rules, not a transcription of the tutorial generator or upstream cycles.
'A few' is operationalised as at most three named members of one group per stage.
"""

import re
from collections import defaultdict

from tests.fixtures.tutorial_cases.stages import assert_template_batches, group

NAMED_LIMIT = 3
ALIGNMENT = {'cell', 'scale', 'zero shift', 'calibration'}


def block(category):
    if category in ALIGNMENT:
        return 'alignment'
    if category in {'peak widths', 'peak asymmetry'}:
        return 'profile'
    if 'displacement' in category:
        return 'displacement'
    if 'absorption' in category:
        return 'absorption'
    if 'magnetic_form_factor' in category:
        return 'magnetic form factor'
    return category


def overlaps(left, right):
    def pattern(value):
        return re.escape(value).replace(r'\[\*\]', r'\[[^\]]+\]')

    return bool(re.fullmatch(pattern(left), right) or re.fullmatch(pattern(right), left))


def stage_boundary(plan, event):
    """Identify a distinct teaching stage, keeping repeated fits within their current stage."""
    lines = plan.get('source', '').splitlines()[: event.get('line', 1) - 1]
    return next(
        (i for i in range(len(lines) - 1, -1, -1) if re.match(r'#\s+#{2,3}\s', lines[i])),
        None,
    )


def stage_reason(plan, event, blocks):
    """Require a causal explanation local to the stage introducing the named blocks."""
    if len(blocks) <= 1:
        return False
    lines = plan.get('source', '').splitlines()[: event.get('line', 1) - 1]
    boundaries = [i for i, line in enumerate(lines) if re.match(r'#\s+#{2,3}\s', line)]
    if not boundaries:
        return False
    text = '\n'.join(
        line.lstrip('# ')
        for line in lines[boundaries[-1] :]
        if line.lstrip().startswith('#') and not line.startswith('# %%')
    )
    causal = re.search(
        r'\b(?:because|so that|otherwise|separating)\b(.{20,})', text, re.IGNORECASE | re.DOTALL
    )
    vocabulary = {
        'alignment': r'scale|cell|alignment|offset|zero',
        'profile': r'profile|width|asymmetry',
        'displacement': r'displacement|B iso|ADP',
        'positions': r'position|coordinate',
        'magnetic moments': r'moment|magnetic',
        'magnetic form factor': r'form factor|j2',
    }
    return bool(causal) and all(
        re.search(vocabulary.get(name, re.escape(name)), text, re.IGNORECASE) for name in blocks
    )


def assert_strategy(plan):  # noqa: PLR0914 - distinct cumulative, ownership and stage rules
    assert_template_batches(plan)
    accepted = set()
    fixed_after_fit = set()
    pending = []
    beyond_alignment = False
    index = 0
    previous_boundary = None
    for event in plan['events']:
        if event['kind'] != 'fit':
            pending.append(event)
            continue
        retired = {p for item in pending if item['kind'] == 'replace' for p in item['retired']}
        accepted.difference_update(retired)
        current = set(plan['free_before'][index])
        dependents = {
            item['dependent']
            for item in pending
            if item['kind'] == 'constraint' and item.get('dependent')
        }
        for item in pending:
            if item['kind'] not in {'free', 'fix'}:
                continue
            parameter = item['parameter']
            if item['kind'] == 'fix' and index:
                matched = {value for value in accepted if overlaps(value, parameter)}
                assert not matched or parameter in dependents, (
                    'Gate 3/4: accepted independent parameters stay free; only '
                    'named constraint dependents may be fixed'
                )
                assert 'project.free_parameters' not in parameter, (
                    'Gate 3/4: an accepted fit cannot be followed by a blanket fixed/free reset'
                )
                if matched:
                    fixed_after_fit.add(parameter)
            elif item['kind'] == 'free':
                assert not any(overlaps(parameter, value) for value in fixed_after_fit), (
                    'Gate 3/4: tutorials never fix an accepted parameter and free it again'
                )
        assert not (accepted - current - dependents), (
            'Gate 3/4: every accepted independent parameter remains in the '
            'next actual free population'
        )
        new = current - accepted
        blocks = {block(group(value)) for value in new}
        explained = stage_reason(plan, event, blocks)
        boundary = stage_boundary(plan, event)
        assert (
            blocks
            or dependents
            or event.get('operation') == 'fit_sequential'
            or (index and boundary == previous_boundary)
        ), (
            'Gate 3/4: each new teaching stage introduces a scientific block; '
            'repeated fits stay within their current stage'
        )
        assert len(blocks) <= 1 or explained, (
            'Gate 3/4: a stage combining scientific blocks states its reason in that stage text'
        )
        if index == 0:
            assert 'alignment' in blocks and (blocks == {'alignment'} or explained), (
                'Gate 3/4: alignment with eligible cell, scale and calibration '
                'precedes profile and structure fitting'
            )
        else:

            def owner(parameter):
                match = re.match(r'(.+?\[[^]]+\])\.', parameter)
                return match[1] if match else parameter.split('.')[0]

            new_alignment = {owner(p) for p in new if block(group(p)) == 'alignment'}
            fresh_independent = (
                plan.get('independent')
                and new_alignment
                and not (new_alignment & {owner(p) for p in accepted})
            )
            assert not (beyond_alignment and 'alignment' in blocks and not fresh_independent), (
                'Gate 3/4: complete alignment before introducing later scientific blocks'
            )
        beyond_alignment |= bool(blocks - {'alignment'})
        accepted = current
        previous_boundary = boundary
        pending.clear()
        index += 1
    assert index, 'Gate 3/4: the strategy observer reaches an actual tutorial fit'


def assert_code_group_actions(plan):
    named = defaultdict(set)
    for event in plan['events']:
        if event['kind'] == 'fit':
            named.clear()
        elif event['kind'] in {'free', 'fix'} and not event['collective']:
            key = (event['kind'], group(event['parameter']))
            named[key].add(event['parameter'])
            assert len(named[key]) <= NAMED_LIMIT, (
                'Gate 3/4: larger parameter groups use one collection action, '
                'not a per-member flag list'
            )


def visible_prose(source):
    source = re.sub(r'<svg\b.*?</svg>', '', source, flags=re.DOTALL)
    source = re.sub(r'^\s*```[^\n]*$', '', source, flags=re.MULTILINE)
    return re.sub(r'<[^>]+>', '', source)


def app_actions(source):
    """Read user instructions, excluding machine check/target ids and image markup."""
    prose = re.sub(
        r'(?mi)^([ \t]*(?:[-*]\s+)?(?:free|fix))[ \t]*\n+[ \t]*',
        r'\1 ',
        visible_prose(source),
        flags=re.IGNORECASE,
    )
    for line in prose.splitlines():
        plain = re.sub(r'[*`]', '', line).strip()
        if plain.startswith('#'):
            yield ('boundary', plain.lstrip('# ').strip(), line)
            continue
        if re.search(r'\b(?:free|fixed|fix)\s*(?:[·:]\s*)?all\b', plain, re.IGNORECASE):
            yield ('bulk', plain, line)
            if re.search(r'\b(?:click|press|run)\s+(?:the\s+)?Fit\b', plain, re.IGNORECASE):
                yield ('boundary', '', '')
            continue
        toggle = re.search(r'\b(tick|clear|untick)\s+Free\s+for\s+(.+)', plain, re.IGNORECASE)
        match = re.match(r'(?:[-•]\s*)?(free|fix)\s+(.+)', plain, re.IGNORECASE)
        if toggle:
            yield ('free' if toggle[1].casefold() == 'tick' else 'fix', toggle[2], line)
        if match and not re.match(r'(?:column|header)\b', match[2], re.IGNORECASE):
            yield (match[1].casefold(), match[2], line)
        if re.search(r'\b(?:click|press|run)\s+(?:the\s+)?Fit\b', plain, re.IGNORECASE):
            yield ('boundary', '', '')


def assert_app_group_actions(source):
    named = defaultdict(set)
    context = 'named parameters'
    for action, subject, raw in app_actions(source):
        if action == 'boundary':
            named.clear()
            if raw.lstrip().startswith('#'):
                context = subject.casefold()
            continue
        if action == 'bulk':
            continue
        members = [
            a or b
            for a, b in re.findall(r'`([^`]+)`|\*\*([^*]+)\*\*', raw)
            if (a or b).casefold() not in {'free', 'fix', 'fit', 'analysis', 'parameters'}
        ] or re.split(r',|\band\b', subject)
        if (
            re.search(r'\b(?:all|every|group|category)\b', subject, re.IGNORECASE)
            and len(members) == 1
            and not re.search(r'\b\d+\b', subject)
        ):
            continue
        category = group('parameter.' + subject)
        if category.startswith('other:'):
            category = 'calibration' if re.search(r'\boffset\b', subject) else context
        named[action, category].update(member.strip() for member in members)
        assert len(named[action, category]) <= NAMED_LIMIT, (
            'Gate 3/4: app group actions use category filtering and the '
            'Free header, not long member lists'
        )


def app_labels(reference):
    labels = set(re.findall(r'\{"[^"]+", "([^"]+)", "[^"]*", "[^"]*"\}', reference))
    adp_labels = set(re.findall(r'\{"atom_site\.adp_type", "[^"]+", "([^"]+)"\}', reference))
    return labels | adp_labels


def assert_app_names(source, labels, table_names=(), datablock_names=()):
    actions = list(app_actions(source))
    prose = '\n'.join(raw for action, _subject, raw in actions if action != 'boundary')
    assert not re.search(
        r'\b(?:project|experiments?|structures?|cell|atom_sites|peak|instrument|'
        r'background|linked_structures)(?:\[[^\]\n]*\])?\.[A-Za-z_]'
        r'|\b(?:calib_|broad_|decay_|rise_|adp_|fract_)[a-z_0-9]+',
        prose,
    ), (
        'Gate 3/4: app tutorials use visible table names rather than '
        'Python paths or field identifiers'
    )
    categories = {
        'background',
        'cell',
        'scale',
        'peak widths',
        'positions',
        'coordinates',
        'occupancies',
        'displacements',
        'magnetic moments',
        'extinction',
        'linked structures',
        'instrument',
        'atomic coordinates',
        'atomic occupancies',
        'atomic displacement',
        'atom sites',
        'peak profile',
        'peak broadening',
        'peak mixing',
        'absorption',
        'peak asymmetry',
        'magnetic form factors',
    }
    allowed = {value.casefold() for value in [*labels, *table_names]} | categories
    for action, subject, raw in actions:
        if action == 'boundary':
            continue

        def selector(match):
            names = re.findall(r'\*\*([^*]*)\*\*', match[1])
            assert all(name in datablock_names for name in names if name), (
                'Gate 3/4: a datablock selector names an actual project block'
            )
            return match[0].replace(match[1], '')

        parameter_text = re.sub(
            r'(?:choose\s+|(?:parameters|rows the stage names) of\s+)'
            r'((?:\*\*[^*]*\*\*(?:\s+and\s+)?)+)'
            r'(?=(?:,\s*choosing each in| in) the datablock filter)',
            selector,
            raw,
            flags=re.IGNORECASE,
        )
        parameter_text = re.sub(
            r'(?:on \*\*Structure\*\*, )?choose \*\*[^*]+\*\* as every site.s type '
            r'in the \*\*Atomic displacement\*\* table;?',
            '',
            parameter_text,
            flags=re.IGNORECASE,
        )
        tokens = re.findall(r'`([^`]+)`|\*\*([^*]+)\*\*|"([^"]+)"', parameter_text)
        if not tokens:
            assert any(
                re.search(r'(?<!\w)' + re.escape(label) + r'(?!\w)', subject, re.IGNORECASE)
                for label in allowed
            ), 'Gate 3/4: unquoted app instructions also name real table parameters or categories'
        for spelling in tokens:
            token = ''.join(spelling)
            if token.casefold() in {
                'free',
                'fix',
                'fixed',
                'fit',
                'analysis',
                'parameters',
                'free · all',
                'free all',
                'fixed all',
                'fix all',
                'fixed · all',
                'fix · all',
            }:
                continue
            name = re.split(r'\s*[\u203a→/]\s+', token)[-1].strip().casefold()
            assert token.casefold() in allowed or name in allowed, (
                'Gate 3/4: a named app parameter is an actual dictionary table label: '
                + repr(token)
            )


def assert_command_group_actions(actions):
    named = defaultdict(set)
    for operation, filename, body in actions:
        if operation in {'fit', 'calc'}:
            named.clear()
        elif operation in {'edit', 'free-rows'}:
            rows = [
                line
                for line in body.splitlines()
                if line.strip() and not line.lstrip().startswith('#')
            ]
            if len(rows) != 1:
                continue  # One block edits the group's rows together.
            row = rows[0]
            category = group(row)
            if category.startswith('other:'):
                category = 'loop rows'
            named[filename, category].add(row)
            assert len(named[filename, category]) <= NAMED_LIMIT, (
                'Gate 5: a large Command line group is edited together, not as '
                'individual row instructions'
            )
