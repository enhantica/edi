"""Replay visible project-file edits and CLI stages without inventing a teaching manifest."""

import re
import shlex
import textwrap
import zipfile
from pathlib import Path


def actions(markdown):  # noqa: PLR0912 - finite displayed shell and file instruction grammar
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


def visible_flag_edits(project, filename, excerpt=None):  # noqa: PLR0914, PLR0915 - literal finite row edits
    """Apply the stated remove-every-marker/add-marker operation, preserving fitted values.

    Headerless row examples resolve against their named file, never a second stage plan.
    An explicit 'N more lines' expands only a uniform flag edit covering the remaining
    rows of that same unambiguous loop. Different omitted column patterns refuse.
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
            edit_project(project, filename, line)
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
        columns.append(flags)
    omitted = re.findall(r'(?:…|\.\.\.)\s+and\s+(\d+)\s+more lines', excerpt)
    if omitted:
        assert len(omitted) == 1 and changed and all(value == columns[0] for value in columns), (
            'Gate 5: an abbreviated value edit has one explicitly counted uniform remainder: '
            + filename
            + ' / columns='
            + repr(columns)
        )
        begin = max(index for index in range(min(changed)) if lines[index].strip() == 'loop_')
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
        assert len(rows) == len(changed) + int(omitted[0]), (
            'Gate 5: the stated omitted-line count equals the rest of the identified loop: '
            + filename
            + ' / shown='
            + str(len(changed))
            + ' omitted='
            + repr(omitted)
            + ' actual='
            + str(len(rows))
        )
        for row in rows:
            tokens = shlex.split(lines[row], comments=True)
            for column in columns[0]:
                if not re.search(r'\([^)]*\)$', tokens[column]):
                    tokens[column] += '()'
            lines[row] = ' '.join(tokens)
    path.write_text('\n'.join(lines) + '\n')


def edit_project(project, filename, excerpt):  # noqa: PLR0912, PLR0914, PLR0915 - finite CIF edit observer
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
