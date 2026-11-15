"""Replay visible project-file edits and CLI stages without inventing a teaching manifest."""

import re
import shlex
import textwrap
import zipfile
from pathlib import Path

from tests.fixtures.tutorial_cases.pins import compare_regression_pin


def actions(markdown):  # noqa: PLR0912, PLR0914, PLR0915 - finite written instruction grammar
    result = []
    previous = 0
    for fence in re.finditer(
        r'^(?P<indent>[ \t]*)```(?P<info>[^\n]*)\n(?P<code>.*?)^(?P=indent)```\s*$',
        markdown,
        re.MULTILINE | re.DOTALL,
    ):
        info, code = fence['info'], textwrap.dedent(fence['code'])
        labels = re.findall(r'^===\s+[^\n]+', markdown[: fence.start()], re.MULTILINE)
        if len(fence['indent']) >= 4 and labels and 'Python package' in labels[-1]:
            previous = fence.end()
            # The built-site gate proves prefix equivalence; run one route per stage.
            continue
        context = markdown[previous : fence.start()].split('\n\n')[-2:]
        names = re.findall(r'[\w./-]+\.edi\b', info + '\n' + '\n'.join(context))
        if (
            info.split(' ', 1)[0] in {'edi', 'cif', 'diff'}
            or (names and re.search(r'^_|^data_|^loop_', code, re.MULTILINE))
            or (names and info.strip() == 'text')
        ):
            assert names and len(set(names)) == 1, (
                'Gate 5: a visible project-file edit names one unambiguous .edi file'
            )
            instruction = '\n'.join(context).casefold()
            if 'remove' in instruction and 'every value' in instruction:
                result.append(('clear-free', names[-1], ''))
            elif 'add' in instruction and '()' in instruction and 'free' in instruction:
                headings = re.findall(r'^##+ (.+)$', markdown[: fence.start()], re.MULTILINE)
                if headings:
                    code = '# tutorial-heading: ' + headings[-1] + '\n' + code
                starts = list(re.finditer(r'^##+ ', markdown[: fence.start()], re.MULTILINE))
                stage = markdown[starts[-1].start() if starts else previous : fence.start()]
                stage = re.sub(r'```.*?```', '', stage, flags=re.DOTALL)
                code = '# tutorial-scope: ' + ' '.join(stage.split()) + '\n' + code
                following = markdown[fence.end() :].split('```', 1)[0]
                remainder = re.search(r'The same for every other row \((\d+) more\)', following)
                if remainder:
                    code += '\n… and ' + remainder[1] + ' more lines\n'
                result.append(('free-rows', names[-1], code))
            else:
                result.append((
                    'write' if re.search(r'\bwrite\b', instruction) else 'edit',
                    names[-1],
                    code,
                ))
                if 'alias and constraint' in instruction and '=' not in code:
                    starts = list(re.finditer(r'^##+ ', markdown[: fence.start()], re.MULTILINE))
                    scope = markdown[starts[-1].start() if starts else previous : fence.start()]
                    following = markdown[fence.end() :].split('```', 1)[0]
                    if re.search(r'The same for every other row \(1 more\)', following) and (
                        relation := written_relation(scope, code)
                    ):
                        result.append(('edit', names[-1], relation))
        elif info.split(' ', 1)[0] in {'sh', 'shell', 'bash', 'console'}:
            for written in code.splitlines():
                line = re.sub(r'^\s*\$\s*', '', written).strip()
                if line.startswith(('edi ', 'python -m edi ', 'python3 -m edi ')):
                    arguments = shlex.split(line)
                    offset = arguments.index('edi')
                    arguments = arguments[offset + 1 :]
                    if arguments and arguments[0] in {'fit', 'calc'}:
                        result.append((arguments[0], arguments[1:], ''))
                    elif arguments and arguments[0] == 'download-data':
                        result.append(('download', arguments, ''))
                elif line.startswith('mkdir -p '):
                    result.append(('mkdir', shlex.split(line)[2:], ''))
                elif line.startswith('mv '):
                    result.append(('move', shlex.split(line)[1:], ''))
                elif line.startswith('tar -xf '):
                    tokens = shlex.split(line)
                    assert len(tokens) == 5 and tokens[3] == '-C', (
                        'Gate 5: an archive setup instruction names its input and destination'
                    )
                    result.append(('unpack', [tokens[2], tokens[4]], ''))
        previous = fence.end()
    return result


def written_relation(scope, code):
    relation = re.search(
        r"constrain\s+(\w+)['\u2019]s\s+to\s+follow\s+(\w+)['\u2019]s",
        re.sub(r'[*`]', '', scope),
        re.IGNORECASE,
    )
    if relation is None:
        return None
    aliases = [shlex.split(line) for line in code.splitlines() if line.strip()]
    owners = []
    for label in relation.groups():
        matches = [
            row[0]
            for row in aliases
            if len(row) == 2
            and len(row[1].split('.')) >= 3
            and row[1].split('.')[-2].casefold() == label.casefold()
        ]
        assert len(matches) == 1, (
            'Gate 5: each explicitly named relation endpoint has one written alias'
        )
        owners.append(matches[0])
    expression = owners[0] + ' = ' + owners[1]
    return shlex.join([owners[0], expression]) + '\n'


def loop_schemas(text):
    return [
        match[1].splitlines() for match in re.finditer(r'(?m)^loop_\s*\n((?:_[^\n]+\n)+)', text)
    ]


def normalized_rows(original, excerpt, schemas):
    """Resolve shown columns through the actual downloaded schema, not fitted numbers."""
    current = loop_schemas(original)
    result = []
    for line in excerpt.splitlines():
        if not line.strip() or line.lstrip().startswith(('#', '_', '…', '...', 'loop_', 'data_')):
            result.append(line)
            continue
        shown = shlex.split(line, comments=True)
        possibilities = set()
        for source in schemas:
            if len(source) != len(shown):
                continue
            for target in current:
                if len(target) == len(source) or not set(target) < set(source):
                    continue
                # A removed transport column must never contain a requested free mark.
                missing = [i for i, name in enumerate(source) if name not in target]
                assert not any(shown[i].endswith('()') for i in missing), (
                    'Gate 5: a displayed free mark cannot target a column absent after saving'
                )
                possibilities.add(tuple(shown[source.index(name)] for name in target))
        assert len(possibilities) <= 1, (
            'Gate 5: historical source columns identify at most one current loop layout'
        )
        result.append(
            ' '.join(
                shlex.quote(v) if any(c.isspace() for c in v) else v
                for v in next(iter(possibilities))
            )
            if possibilities
            else line
        )
    return '\n'.join(result) + '\n'


def visible_flag_edits(project, filename, excerpt=None, schemas=()):  # noqa: PLR0912, PLR0914, PLR0915 - literal finite row edits
    """Apply the stated remove-every-marker/add-marker operation, preserving fitted values.

    Headerless row examples resolve against their named file, never a second stage plan.
    Explicit first-N and atomic independence qualifiers select the counted subset.
    Non-atomic remainders still require one uniform new-marker pattern.
    """
    candidates = [path for path in project.rglob('*.edi') if path.as_posix().endswith(filename)]
    assert len(candidates) == 1, 'Gate 5: the visible flag edit identifies one project file'
    path = candidates[0]
    assert path.resolve().is_relative_to(project.resolve()), (
        'Gate 5: a project edit cannot follow a symlink outside its staged project'
    )
    lines = path.read_text().splitlines()
    if excerpt is None:
        path.write_text('\n'.join(re.sub(r'(?<=[\d.])\(\d*\)', '', line) for line in lines) + '\n')
        return
    excerpt = normalized_rows('\n'.join(lines) + '\n', excerpt, schemas)
    heading = re.search(r'^# tutorial-heading: (.+)$', excerpt, re.MULTILINE)
    table = (
        '_background.'
        if heading and re.fullmatch(r'backgrounds?', heading[1], re.IGNORECASE)
        else None
    )

    def table_row(index):
        if table is None:
            return True
        starts = [i for i in range(index) if lines[i].strip() == 'loop_']
        if not starts:
            return False
        headers = [
            line.strip() for line in lines[starts[-1] + 1 : index] if line.strip().startswith('_')
        ]
        return bool(headers) and all(name.startswith(table) for name in headers)

    before = list(lines)
    changed = []
    columns = []
    for line in excerpt.splitlines():
        if (
            not line.strip()
            or line.lstrip().startswith(('#', '…', '...', 'data_'))
            or line.strip() == 'loop_'
            or (line.strip().startswith('_') and len(shlex.split(line)) == 1)
        ):
            continue
        shown = shlex.split(line, comments=True)
        flags = [index for index, value in enumerate(shown) if value.endswith('()')]
        if not flags:
            path.write_text('\n'.join(lines) + '\n')
            edit_project(project, filename, line, schemas=schemas)
            lines = path.read_text().splitlines()
            continue
        matches = [
            index
            for index, raw in enumerate(lines)
            if (tokens := shlex.split(raw, comments=True))
            and len(tokens) > max(flags)
            and tokens[0] == shown[0]
            and table_row(index)
        ]
        exact = [
            index
            for index in matches
            if len(shlex.split(lines[index], comments=True)) == len(shown)
        ]
        if exact:
            matches = exact
        if len(matches) > 1:
            matches = [
                index
                for index in matches
                if shlex.split(lines[index], comments=True)[: min(flags)] == shown[: min(flags)]
            ]
        if len(matches) > 1:

            def symbolic(value):
                try:
                    float(re.sub(r'\([^)]*\)$', '', value))
                except ValueError:
                    return True
                return False

            fixed_labels = [i for i, value in enumerate(shown) if symbolic(value)]
            matches = [
                index
                for index in matches
                if all(
                    i < len(values := shlex.split(lines[index], comments=True))
                    and values[i] == shown[i]
                    for i in fixed_labels
                )
            ]
        assert len(matches) == 1, (
            'Gate 5: each headerless value-edit row identifies one actual row: '
            + filename
            + ' / '
            + repr(shown)
            + ' / matches='
            + repr(matches)
        )
        row = matches[0]
        tokens = shlex.split(lines[row], comments=True)
        for column in flags:
            if not re.search(r'\([^)]*\)$', tokens[column]):
                tokens[column] += '()'
        lines[row] = ' '.join(
            shlex.quote(value) if any(char.isspace() for char in value) else value
            for value in tokens
        )
        changed.append(row)
        columns.append([
            column
            for column in flags
            if not re.search(r'\([^)]*\)$', shlex.split(before[row], comments=True)[column])
        ])
    omitted = re.findall(r'(?:…|\.\.\.)\s+and\s+(\d+)\s+more lines', excerpt)
    if omitted:
        assert len(omitted) == 1 and changed, (
            'Gate 5: an abbreviated value edit has one explicitly counted uniform remainder: '
            + filename
            + ' / columns='
            + repr(columns)
        )
        loops = [index for index in range(max(changed)) if lines[index].strip() == 'loop_']
        assert loops, 'Gate 5: the counted remainder immediately follows an actual loop'
        begin = loops[-1]
        # The abbreviation follows the last displayed loop, not preceding complete
        # scalar or loop edits in the same fence.
        all_changed = set(changed)
        in_loop = [
            (row, flags) for row, flags in zip(changed, columns, strict=True) if row > begin
        ]
        assert in_loop, 'Gate 5: a counted remainder contains at least one displayed loop row'
        changed, columns = map(list, zip(*in_loop, strict=True))
        end = next(
            (
                index
                for index in range(max(changed) + 1, len(lines))
                if lines[index].strip() == 'loop_' or lines[index].lstrip().startswith('_')
            ),
            len(lines),
        )
        rows = [
            index
            for index in range(begin + 1, end)
            if lines[index].strip() and not lines[index].lstrip().startswith(('_', '#'))
        ]
        headers = [
            lines[index].strip()
            for index in range(begin + 1, min(rows))
            if lines[index].strip().startswith('_')
        ]
        scope = re.search(r'^# tutorial-scope: (.+)$', excerpt, re.MULTILINE)
        scope = scope[1].casefold() if scope else ''
        words = dict(
            zip(
                [
                    'one',
                    'two',
                    'three',
                    'four',
                    'five',
                    'six',
                    'seven',
                    'eight',
                    'nine',
                    'ten',
                    'eleven',
                    'twelve',
                ],
                range(1, 13),
                strict=True,
            )
        )
        first = re.search(r'first (\d+|' + '|'.join(words) + r') (?:background|polynomial)', scope)
        if first and headers and headers[0].startswith('_background.'):
            count = int(first[1]) if first[1].isdigit() else words[first[1]]
            rows = rows[:count]
        if (
            headers
            and headers[0].startswith('_background.')
            and 'first and last stay fixed' in scope
        ):
            bank = re.search(r"bank\s+([\d-]+)['\u2019]s first and last stay fixed", scope)
            if bank is None or Path(filename).stem.endswith(bank[1].replace('-', '_')):
                rows = rows[1:-1]
        new_columns = sorted({column for flags in columns for column in flags})
        semantic = headers and headers[0].startswith((
            '_atom_site.',
            '_atom_site_aniso.',
            '_atom_site_moment.',
        ))
        if semantic:
            loop_rows = list(rows)
            types = {
                tokens[-1]
                for line in excerpt.splitlines()
                if (tokens := shlex.split(line, comments=True))
                and len(tokens) > 2
                and tokens[-1] in {'Biso', 'Uiso', 'Bani', 'beta'}
            }
            adp_type = (
                next(iter(types))
                if len(types) == 1
                and re.search(r'\b(?:isotropic|anisotropic) displacements?\b', scope)
                else None
            )
            selected = eligible_site_columns(
                project,
                before,
                rows,
                headers,
                new_columns,
                adp_type=adp_type,
                scope=scope,
            )
            rows = [row for row in rows if selected[row]]
            assert all(
                set(flags) == set(selected[row])
                for row, flags in zip(changed, columns, strict=True)
            ), 'Gate 5: every shown atomic marker exactly matches its declared independent members'
        else:
            assert all(value == columns[0] for value in columns), (
                'Gate 5: an abbreviated non-atomic value edit has one uniform new-marker pattern'
            )
            selected = dict.fromkeys(rows, new_columns)
        extra = (
            named_form_factor_rows(project, before)
            if headers and headers[0].startswith('_atom_site_moment.') and 'j2' in scope
            else {}
        )
        extra = {row: column for row, column in extra.items() if row not in all_changed}
        assert set(changed) <= set(rows), (
            'Gate 5: each shown new-marker row belongs to the declared independent subset'
        )
        assert len(rows) + len(extra) == len(changed) + int(omitted[0]), (
            'Gate 5: the stated omitted-line count equals the rest of the identified loop: '
            + filename
            + ' / shown='
            + str(len(changed))
            + ' omitted='
            + repr(omitted)
            + ' actual='
            + str(len(rows))
        )
        for row, column in extra.items():
            tokens = shlex.split(lines[row], comments=True)
            if not re.search(r'\([^)]*\)$', tokens[column]):
                tokens[column] += '()'
            lines[row] = ' '.join(tokens)
        if semantic and adp_type is not None:
            assert '_atom_site.adp_type' in headers, (
                'Gate 5: the written displacement choice names an actual type column'
            )
            type_column = headers.index('_atom_site.adp_type')
            for row in loop_rows:
                tokens = shlex.split(lines[row], comments=True)
                tokens[type_column] = adp_type
                lines[row] = ' '.join(tokens)
        for row in rows:
            tokens = shlex.split(lines[row], comments=True)
            for column in selected[row]:
                if not re.search(r'\([^)]*\)$', tokens[column]):
                    tokens[column] += '()'
            lines[row] = ' '.join(tokens)
    path.write_text('\n'.join(lines) + '\n')


def named_form_factor_rows(project, lines):
    """An explicitly named j2 term may follow complete scalar and moment rows."""
    import edi  # noqa: PLC0415

    model = edi.Project.load(str(project))
    block_name = next(line.strip()[5:] for line in lines if line.strip().startswith('data_'))
    block = next(block for block in model.structures if block.name == block_name)
    result = {}
    for begin, line in enumerate(lines):
        if line.strip() != 'loop_':
            continue
        header_end = begin + 1
        while header_end < len(lines) and lines[header_end].strip().startswith('_'):
            header_end += 1
        headers = [line.strip() for line in lines[begin + 1 : header_end]]
        if '_magnetic_form_factor.j2_coefficient' not in headers:
            continue
        column = headers.index('_magnetic_form_factor.j2_coefficient')
        for row in range(header_end, len(lines)):
            if lines[row].strip().startswith(('_', 'loop_', 'data_')):
                break
            tokens = shlex.split(lines[row], comments=True)
            if not tokens:
                continue
            parameter = block.magnetic_form_factor[tokens[0]].j2_coefficient
            if not parameter.symmetry_constrained and not parameter.user_constrained:
                result[row] = column
    assert result, 'Gate 5: the explicitly named j2 remainder has an independent actual member'
    return result


def eligible_site_columns(project, before, rows, headers, columns, *, adp_type=None, scope=''):
    """Observe only the selected independent atomic members in the current saved model."""
    import edi  # noqa: PLC0415

    model = edi.Project.load(str(project))
    block_name = next(line.strip()[5:] for line in before if line.strip().startswith('data_'))
    blocks = [block for block in model.structures if block.name == block_name]
    assert len(blocks) == 1, 'Gate 5: an atomic edit belongs to one actual named structure block'
    block = blocks[0]
    if adp_type is not None:
        for row in rows:
            block.atom_sites[shlex.split(before[row], comments=True)[0]].adp_type = adp_type
    owners = {headers[column].split('.')[0] for column in columns}
    assert len(owners) == 1, 'Gate 5: a remainder names one actual atomic parameter category'
    owner = next(iter(owners))
    names = {headers[column].split('.')[1] for column in columns}
    if owner == '_atom_site' and names & {'fract_x', 'fract_y', 'fract_z'}:
        names |= {'fract_x', 'fract_y', 'fract_z'}
    selected_columns = [
        i
        for i, header in enumerate(headers)
        if header.split('.')[0] == owner and header.split('.')[1] in names
    ]
    result = {}
    for row in rows:
        tokens = shlex.split(before[row], comments=True)
        site = block.atom_sites[tokens[0]]
        if 'oxygen occupanc' in scope and str(site.type_symbol) != 'O':
            result[row] = []
            continue
        holder = (
            getattr(block, owner.removeprefix('_'))[tokens[0]]
            if owner in {'_atom_site_aniso', '_atom_site_moment'}
            else site
        )
        available = []
        for column in selected_columns:
            parameter = getattr(holder, headers[column].split('.')[1])
            if (
                owner == '_atom_site'
                and headers[column].endswith('.adp_iso')
                and str(site.adp_type) not in {'Biso', 'Uiso'}
            ):
                continue
            if (
                parameter.symmetry_constrained
                or parameter.user_constrained
                or re.search(r'\([^)]*\)$', tokens[column])
            ):
                continue
            available.append(column)
        result[row] = available
    return result


def edit_project(project, filename, excerpt, schemas=()):  # noqa: PLR0912, PLR0914, PLR0915 - finite CIF edit observer
    name = Path(filename)
    assert not name.is_absolute() and '..' not in name.parts, (
        'Gate 5: tutorial edits name portable files within their project'
    )
    candidates = [path for path in project.rglob('*.edi') if path.as_posix().endswith(filename)]
    if not candidates:
        candidates = list(project.rglob(name.name))
    assert len(candidates) == 1, (
        'Gate 5: the visible filename resolves to exactly one project file'
    )
    target = candidates[0]
    assert target.resolve().is_relative_to(project.resolve()), (
        'Gate 5: literal edits cannot write through an external project symlink'
    )
    if excerpt.lstrip().startswith('data_'):
        target.write_text(excerpt)
        return
    original = target.read_text()
    excerpt = normalized_rows(original, excerpt, schemas)
    # Scalar excerpts preserve omitted lines. Loop excerpts carry enough column and row
    # identity to apply exactly the displayed edits; ambiguity refuses before any fit.
    lines = excerpt.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        if not line or line.startswith('#') or line in {'...', '…'}:
            index += 1
            continue
        if line == 'loop_':
            index += 1
            headers = []
            while index < len(lines) and lines[index].strip().startswith('_'):
                headers.append(lines[index].strip())
                index += 1
            blocks = list(
                re.finditer(
                    r'(?ms)^loop_\s*\n((?:_[^\n]+\n)+)(.*?)(?=^loop_|^data_|^_[^\s]+[ \t]+\S|\Z)',
                    original,
                )
            )
            matches = [block for block in blocks if set(headers) <= set(block[1].splitlines())]
            assert headers and len(matches) == 1, (
                'Gate 5: a loop edit identifies its original column set'
            )
            block = matches[0]
            full_headers = block[1].splitlines()
            keys = [
                column
                for column in headers
                if column.endswith((
                    '.id',
                    '.label',
                    '.number',
                    '.x',
                    '.structure_id',
                    '.position',
                ))
            ]
            assert keys, 'Gate 5: a loop excerpt includes a stable row key'
            key = keys[0]
            rows = block[2].splitlines()
            while index < len(lines) and not lines[index].strip().startswith((
                '_',
                'loop_',
                'data_',
            )):
                values = shlex.split(lines[index], comments=True)
                index += 1
                if not values or values in [['...'], ['…']]:
                    continue
                assert len(values) == len(headers), (
                    'Gate 5: an edited loop row has every displayed column'
                )
                candidates = [
                    row
                    for row, text in enumerate(rows)
                    if text.strip()
                    and not text.lstrip().startswith('#')
                    and shlex.split(text)[full_headers.index(key)] == values[headers.index(key)]
                ]
                assert len(candidates) == 1, (
                    'Gate 5: an edited row key identifies one original row'
                )
                tokens = shlex.split(rows[candidates[0]])
                for column, value in zip(headers, values, strict=True):
                    tokens[full_headers.index(column)] = value
                rows[candidates[0]] = ' '.join(
                    shlex.quote(value) if any(char.isspace() for char in value) else value
                    for value in tokens
                )
            original = (
                original[: block.start(2)] + '\n'.join(rows) + '\n' + original[block.end(2) :]
            )
            continue
        tokens = shlex.split(line, comments=True)
        if len(tokens) == 2 and tokens[0].startswith('_'):
            pattern = r'(?m)^' + re.escape(tokens[0]) + r'\s+[^\n]+$'
            assert len(re.findall(pattern, original)) <= 1, (
                'Gate 5: a scalar edit refuses duplicate ambiguous fields'
            )
            original = (
                re.sub(pattern, lambda _match, value=line: value, original)
                if re.search(pattern, original)
                else original + '\n' + line + '\n'
            )
        elif len(tokens) > 2 or (
            len(tokens) == 2
            and re.fullmatch(
                r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?(?:\(\d*\))?',
                tokens[1],
            )
        ):
            rows = original.splitlines()
            candidates = [
                row
                for row, text in enumerate(rows)
                if (values := shlex.split(text, comments=True))
                and len(values) == len(tokens)
                and values[0] == tokens[0]
            ]
            assert len(candidates) == 1, (
                'Gate 5: a literal headerless value reset identifies one complete actual row'
            )
            rows[candidates[0]] = line
            original = '\n'.join(rows) + '\n'
        else:
            assert len(tokens) == 2 and ('.' in tokens[1] or '=' in tokens[1]), (
                'Gate 5: a headerless relation row is an explicit alias or constraint'
            )
            prefix, value_tag = (
                ('_constraint', 'expression')
                if '=' in tokens[1]
                else ('_alias', 'parameter_unique_name')
            )
            blocks = list(
                re.finditer(
                    r'(?ms)^loop_\s*\n((?:_[^\n]+\n)+)(.*?)(?=^loop_|^data_|^_[^\s]+[ \t]+\S|\Z)',
                    original,
                )
            )
            matching = [block for block in blocks if prefix + '.id' in block[1].splitlines()]
            assert len(matching) <= 1, (
                'Gate 5: a relation row identifies at most one declared loop'
            )
            if not matching:
                original += (
                    '\nloop_\n' + prefix + '.id\n' + prefix + '.' + value_tag + '\n' + line + '\n'
                )
            else:
                block = matching[0]
                rows = block[2].splitlines()
                indices = [
                    number
                    for number, row in enumerate(rows)
                    if (words := shlex.split(row, comments=True)) and words[0] == tokens[0]
                ]
                assert len(indices) <= 1, 'Gate 5: a relation identity cannot name duplicate rows'
                if indices:
                    rows[indices[0]] = line
                else:
                    rows.append(line)
                original = (
                    original[: block.start(2)] + '\n'.join(rows) + '\n' + original[block.end(2) :]
                )
        index += 1
    target.write_text(original)


def workspace_path(workspace, filename):
    name = Path(filename)
    assert not name.is_absolute() and '..' not in name.parts, (
        'Gate 5: visible setup paths stay relative to their fresh workspace'
    )
    path = workspace / name
    assert path.resolve().is_relative_to(workspace.resolve()), (
        'Gate 5: visible setup paths cannot follow symlinks outside their workspace'
    )
    return path


def setup_action(workspace, operation, arguments):
    """Replay only the finite displayed mkdir/mv/archive vocabulary, without a shell."""
    paths = [workspace_path(workspace, name) for name in arguments]
    if operation == 'mkdir':
        for path in paths:
            path.mkdir(parents=True, exist_ok=True)
    elif operation == 'move':
        assert len(paths) == 2 and paths[0].is_file() and not paths[1].exists(), (
            'Gate 5: a visible move consumes one actual download into a new declared file'
        )
        paths[0].rename(paths[1])
    elif operation == 'unpack':
        assert len(paths) == 2 and paths[0].is_file() and paths[1].is_dir(), (
            'Gate 5: a visible scan extraction uses its actual downloaded archive'
        )
        with zipfile.ZipFile(paths[0]) as archive:
            for name in archive.namelist():
                workspace_path(paths[1], name)
            archive.extractall(paths[1])
    else:
        raise ValueError('Gate 5: unknown visible setup operation: ' + operation)


def write_project(project, filename, content):
    """A visible Write instruction supplies the complete new file, including headerless CIF."""
    target = workspace_path(project, filename)
    assert target.parent.is_dir() and not target.exists(), (
        'Gate 5: Write creates one new file in a directory taught by the setup instructions'
    )
    target.write_text(content)


def compare_staged_regression_pin(actual, quantities):
    """Retain outcome pins; one-shot work counts belong to the one-shot pin gate."""
    count = int(actual['iterations'])
    assert actual['status'] == 'done' and actual['converged'] == 'true' and count > 0, (
        'Gate 5: a staged lesson finishes a real converged fit with positive work'
    )
    assert {
        int(key.split('.')[1]) for key in actual if re.fullmatch(r'iter\.\d+\.rwp', key)
    } == set(range(1, count + 1)), (
        'Gate 5: the final staged fit retains exactly its reported iteration trace'
    )
    compare_regression_pin(
        actual, {key: value for key, value in quantities.items() if key != 'iterations'}
    )
