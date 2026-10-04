# SPDX-License-Identifier: BSD-3-Clause
"""Scrub a local edi tree for public release: personal paths, private citations, process tags.

    python tools/public-release/scrub.py --tree PATH [--check] [--skip-hidden]

The rules are mechanical and idempotent: a second run over a scrubbed tree changes nothing. Three
classes are scrubbed (`patterns.py`):

- personal and machine paths, anywhere in a text file;
- citations of crysta's private design records and source tree;
- development-process references. Only prose is rewritten: Markdown and text files, code
  comments, Python docstrings, and the prose values of YAML files. Code, string literals and data
  stay byte-identical. A tag's reason survives where the text gives it, and an edi ADR is kept.

A comment block or a Markdown paragraph is rewritten as one text and wrapped again to its width.
A notebook rendered from a jupytext source is rendered again from the scrubbed source.

Test names keep their labels: no file is renamed, test code is not rewritten, and a line naming a
test is left alone. What the rules cannot rewrite is edited by hand once, listed in the reviewed
manual-edit list; the rules then leave those lines unchanged.

`--check` reports what would change and exits 1 if anything would; it writes nothing.
`--skip-hidden` leaves the hidden test tiers (`tests/unit`, `tests/integration`, `tests/system`)
unread and unchanged.
"""

from __future__ import annotations

import argparse
import ast
import io
import re
import subprocess
import sys
import tokenize
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from patterns import (  # the sibling module, importable from any working directory
    EDI_ADR,
    HUB,
    PERSONAL,
    PRIVATE,
    PRIVATE_ADR,
    PRIVATE_SRC,
    PROC_TOKEN,
    PROCESS,
    RUN_POINTER,
    TEST_NAME,
)

HIDDEN_TIERS = ('tests/unit/', 'tests/integration/', 'tests/system/')
# Never rewritten: the release tooling's own patterns, test-name inventories (a node id is a test
# name) and the lock.
SKIP_FILES = {
    'tools/public-release/scrub.py',
    'tools/public-release/patterns.py',
    'tools/public-release/scan.py',
    'tools/public-release/snapshot.py',
    'tests/per-pr-runtimes.tsv',
    'tests/latency-bank.json',
    'tests/hidden-surface.txt',
    'tests/test-groups.json',
    'tests/fit-sites.yml',
    'tests/threshold-dispositions.json',
    'pixi.lock',
}
SKIP_DIRS = ('.git/', '.pixi/', 'build/', 'site/', 'node_modules/', '__pycache__/', 'tmp/')
# Byte-pinned inputs: tests compare these files with recorded hashes or with crysta's own bytes,
# so a rewrite is a re-pin, made with the tests that pin them, never by this script.
PINNED = ('tests/fixtures/',)
PINNED_PROJECT = re.compile(r'^docs/user/cli/[^/]+/project/')
# Comments an existing gate reads word for word; a paragraph holding one is left whole.
KEEP = ('TASK-SCOPED PLACEHOLDER',)
# A generated region runs from its first line to the end of its document; its generator writes it.
GENERATED = {'docs/dev/design/diffraction-lib-parity.md': '| diffraction-lib name | note |'}

KINDS = {
    'prose': {'.md', '.txt', '.html', '.rst'},
    'slash': {'.cpp', '.hpp', '.h', '.c', '.qml', '.js', '.css', '.in', '.qrc'},
    'python': {'.py', '.pyi'},
    'hash': {'.sh', '.toml', '.cmake', '.ini', '.cfg', '.edi', '.cif'},
    'yaml': {'.yml', '.yaml'},
}
NAMED_KINDS = {
    'CMakeLists.txt': 'hash',
    '.gitignore': 'hash',
    '.gitattributes': 'hash',
    '.qmllint.ini': 'hash',
    'README': 'prose',
    'NOTICE': 'prose',
}
# YAML keys whose values are prose: a step's name, an action's description, a note.
YAML_PROSE_KEYS = {'name', 'description', 'note', 'notes', 'reason', 'about', 'summary'}

# ---- prose ---------------------------------------------------------------------------------


def _cap(text: str) -> str:
    return text[:1].upper() + text[1:] if text[:1].islower() else text


def _is_process(text: str) -> bool:
    return bool(PROCESS.search(text) or PRIVATE.search(text))


def _edi_adrs(text: str) -> list[str]:
    stripped = PRIVATE.sub('', text)
    found = (m.group(0).replace('edi ', '') for m in re.finditer(EDI_ADR, stripped))
    return list(dict.fromkeys(found))


PURE_PROCESS = re.compile(
    rf'\s*(?:{PROC_TOKEN}|owner(?:\s+\d{{4}}-\d\d-\d\d)?|review[- ]\d+(?:\s+F\d+)?|F\d+'
    rf'|{HUB}|packet(?:\s+[A-Z]\d+)?)\s*'
)


def _segment(segment: str) -> str | None:
    """Keep one `;`-part of a parenthetical, reduce it to its reason or edi ADRs, or drop it."""
    if not _is_process(segment):
        return segment
    items = segment.split(',')
    kept = [item for item in items if not PURE_PROCESS.fullmatch(item)]
    if kept and len(kept) < len(items):  # "Berar-Baldinozzi, <tag>" -> "Berar-Baldinozzi"
        segment = ','.join(kept).strip()
        if not _is_process(segment):
            return segment
    if ':' in segment:  # "<tag> note 6: a loop is a table" -> "a loop is a table"
        tail = segment.split(':', 1)[1].strip()
        if tail and not _is_process(tail) and not tail.startswith('/'):
            return tail
    adrs = _edi_adrs(segment)
    return ', '.join(adrs) if adrs else None


def _paren(m: re.Match[str]) -> str:
    inner = m.group(2)
    if not _is_process(inner):
        return m.group(0)
    kept = [s for s in (_segment(p.strip()) for p in inner.split(';')) if s]
    return f'{m.group(1)}({"; ".join(kept)})' if kept else ''


def _parens(text: str) -> str:
    prev = None
    while prev != text:
        prev = text
        text = re.sub(r'(\s?)\(([^()]*)\)', _paren, text)
    m = re.search(r'\(([^()]*)$', text)  # opened here, closed on a later line
    if m and _is_process(m.group(1)):
        parts = m.group(1).split(';')
        first = _segment(parts[0].strip())
        while first is None and len(parts) > 1:
            parts.pop(0)
            first = _segment(parts[0].strip())
        if first is not None:
            text = text[: m.start(1)] + '; '.join([first, *[p.strip() for p in parts[1:]]])
    return text


LEAD = re.compile(
    rf'^(?P<mark>\s*(?:(?://+|#+|\*+|--|<!--|>|[-*+]|\d+\.)\s*)?)(?P<bold>\*\*)?'
    rf'(?P<tag>{PROC_TOKEN}(?:\s*(?:,|;|/)\s*{PROC_TOKEN})*)(?P<paren>\s*\([^()]*\))?'
    r'(?P=bold)?\s*(?P<sep>:|\u2014|\u2013|\s-)\s*(?P=bold)?\s*'
)


def _lead(text: str) -> str:
    """Drop a tag that opens the text: "<tag> (ADR-0018): the x" -> "ADR-0018: the x"."""
    m = LEAD.match(text)
    if not m:
        return text
    rest = text[m.end() :]
    mark = m.group('mark')
    if mark and not mark.endswith((' ', '\t')):
        mark += ' '
    adrs = _edi_adrs(m.group('paren') or '')
    return mark + (f'{", ".join(adrs)}: {rest}' if adrs else _cap(rest))


INLINE = [
    # a tag in code spans is still a tag: "`<tag>`" -> "<tag>", for the rules below
    (re.compile(rf'`({PROC_TOKEN})`'), r'\1'),
    # a tag that opened a table cell: "| <tag>: the x |" -> "| The x |"
    (
        re.compile(rf'(?<=\| ){PROC_TOKEN}(?:\s*\([^()]*\))?\s*:\s*(?P<w>\S)'),
        lambda m: m.group('w').upper(),
    ),
    # a tag that opened a sentence mid-paragraph: "... tree. <tag>: the x" -> "... tree. The x"
    (
        re.compile(rf'(?<=[.!?] ){PROC_TOKEN}(?:\s*\([^()]*\))?\s*:\s*(?P<w>\w)'),
        lambda m: m.group('w').upper(),
    ),
    (re.compile(PRIVATE_ADR), 'crysta'),
    (re.compile(PRIVATE_SRC), 'crysta'),
    (re.compile(rf'\b{HUB}\s+#\d+\b'), ''),
    (re.compile(rf"\b{HUB}(?:'s)?\s+`?knowledge/[^\s`,;)]*`?"), 'the design records'),
    (re.compile(rf"\b{HUB}(?:'s)?\s+(?:owner\s+)?decision[- ]records?\b"), 'the design records'),
    # a tag that ends a clause takes its preposition along: "retired by <tag>." -> "retired."
    (
        re.compile(
            rf'\s*\b(?:in|by|of|since|before|after|under|from|per|see|for)\s+{PROC_TOKEN}'
            rf"(?:\s*(?:,|/|and)\s*{PROC_TOKEN})*(?:'s)?(?=\s*(?:[,.;:)]|$))"
        ),
        '',
    ),
    # elsewhere only the tag goes: "the <tag> deliverable" -> "the deliverable"
    (re.compile(rf"{PROC_TOKEN}(?:\s*(?:,|/|and)\s*{PROC_TOKEN})*(?:'s)?(?=[\s,.;:)]|$)"), ''),
    (
        re.compile(
            rf"\b{HUB}(?:'s)?\s+(?=packet|task|issue|review|ruling|hub|gate|tools|row|ledger)"
        ),
        '',
    ),
]

CLEANUP = [
    (re.compile(r' \(\s*[;,]?\s*\)'), ''),
    (re.compile(r'\(\s*[;,]\s*'), '('),
    (re.compile(r'\s*[;,]\s*\)'), ')'),
    (re.compile(r'(?<=\S)  +(?=\S)'), ' '),
    (re.compile(r' +([,.;:])(?=\s|$)'), r'\1'),
    (re.compile(r'(?<=\() +'), ''),
    (re.compile(r',\s*,'), ','),
    (re.compile(r'([,;:])\s*\.'), '.'),
    (re.compile(r'[ \t]+$'), ''),
]


def _scrub_once(text: str) -> str:
    if not _is_process(text):
        return text
    out = _lead(_parens(_lead(text)))
    for pattern, repl in INLINE:
        out = pattern.sub(repl, out)
    if out == text:
        return text
    indent = re.match(r'\s*', out).group(0)
    body = out[len(indent) :]
    for pattern, repl in CLEANUP:
        body = pattern.sub(repl, body)
    return indent + body


def scrub_prose(text: str) -> str:
    """Rewrite the process references in one text of prose, to a fixed point."""
    out = text
    for _ in range(8):
        new = _scrub_once(out)
        if new == out:
            break
        out = new
    return out


def personal(line: str) -> str:
    """Replace personal and machine paths; drop a pointer into a local log directory."""
    for pattern, repl in PERSONAL:
        line = pattern.sub(repl, line)
    return RUN_POINTER.sub('', line)


# ---- where the prose is --------------------------------------------------------------------

LIST_MARK = re.compile(r'(?:[-*+•]|\d+[.)])\s+')
# Markdown constructs, notebook cell markers and commented-out code never join a paragraph.
UNJOINABLE = re.compile(r'[>|`#\[!<%]|[\w.\[\]\'"]+(?:\s*=(?!=)|\()')
SLASH_HEAD = re.compile(r'\s*//+\s?')
HASH_HEAD = re.compile(r'\s*#+\s?')
BLOCK_HEAD = re.compile(r'\s*(?:/\*+|\*(?!/))?\s?')
INDENT = re.compile(r'\s*')
MD_HEAD = re.compile(r'\s*(?:>\s?)*')


class Span:
    """One line's prose: `head` (indent and comment marker) + `body` + `tail` (a closing marker).

    `code` is the code a trailing comment follows; it stays when the comment goes. `cont` is the
    head a continuation line of the same paragraph carries.
    """

    def __init__(
        self,
        head: str,
        body: str,
        *,
        tail: str = '',
        joinable: bool = True,
        cont: str | None = None,
        code: str = '',
    ) -> None:
        if joinable and UNJOINABLE.match(body):
            joinable = False
        m = LIST_MARK.match(body) if joinable else None
        if m:  # a list item: the marker joins the head, a continuation is indented past it
            marker = m.group(0)
            head, body = head + marker, body[m.end() :]
            cont = head[: len(head) - len(marker)] + ' ' * len(marker)
        self.head, self.body, self.tail, self.code = head, body, tail, code
        self.joinable = joinable and not tail
        self.cont = head if cont is None else cont
        self.starts = bool(m)


def _span(prefix: re.Pattern[str], line: str, *, joinable: bool = True) -> Span:
    m = prefix.match(line)
    head = m.group(0) if m else ''
    return Span(head, line[len(head) :], joinable=joinable)


def _classify_markdown(lines: list[str]) -> list[str | Span]:
    out: list[str | Span] = []
    fence = False
    for line in lines:
        if line.lstrip().startswith(('```', '~~~')):
            fence = not fence
            out.append(line)
        elif fence or not line.strip() or TEST_NAME.search(line):
            out.append(line)
        else:
            structural = re.match(r'\s*(?:#|\||<|!\[|\[[^\]]*\]:)', line)
            hard_break = line.endswith(('  ', '\\'))
            out.append(_span(MD_HEAD, line, joinable=not (structural or hard_break)))
    return out


def _slash_comment(line: str, at: int) -> tuple[Span, bool]:
    """The span of a comment starting at `at`, and whether a block comment stays open."""
    if line.startswith('/*', at):
        close = line.find('*/', at + 2)
        if close >= 0:
            return Span(line[: at + 2], line[at + 2 : close], tail=line[close:]), False
        rest = line[at + 2 :]
        pad = len(rest) - len(rest.lstrip())
        return Span(line[: at + 2 + pad], rest[pad:], joinable=False), True
    code = line[:at]
    m = SLASH_HEAD.match(line, at)
    if code.strip():
        return Span(line[: m.end()], line[m.end() :], joinable=False, code=code), False
    return _span(SLASH_HEAD, line), False


def _classify_slash(lines: list[str]) -> list[str | Span]:
    out: list[str | Span] = []
    in_block = False
    for line in lines:
        if TEST_NAME.search(line):
            out.append(line)
        elif in_block:
            end = line.find('*/')
            if end < 0:
                out.append(_span(BLOCK_HEAD, line))
                continue
            in_block = False
            sp = _span(BLOCK_HEAD, line[:end], joinable=False)
            sp.tail = line[end:]
            out.append(sp)
        else:
            at = _find_outside_strings(line, ('//', '/*'))
            if at < 0:
                out.append(line)
                continue
            span, in_block = _slash_comment(line, at)
            out.append(span)
    return out


def _find_outside_strings(line: str, markers: tuple[str, ...]) -> int:
    """Index of the first marker outside a string literal, or -1."""
    quote = ''
    i = 0
    while i < len(line):
        ch = line[i]
        if quote:
            i += 2 if ch == '\\' else 1
            if ch == quote:
                quote = ''
            continue
        if ch in '"\'':
            quote = ch
        elif any(line.startswith(marker, i) for marker in markers):
            return i
        i += 1
    return -1


def _hash_comment(line: str) -> str | Span:
    at = _find_outside_strings(line, ('#',))
    if at < 0 or (at > 0 and not line[at - 1].isspace()) or line.startswith('#!'):
        return line
    m = HASH_HEAD.match(line, at)
    if line[:at].strip():
        return Span(line[: m.end()], line[m.end() :], joinable=False, code=line[:at])
    return Span(line[: m.end()], line[m.end() :])


def _classify_hash(lines: list[str]) -> list[str | Span]:
    return [line if TEST_NAME.search(line) else _hash_comment(line) for line in lines]


YAML_BLOCK = re.compile(r'(\s*(?:-\s+)?)([\w-]+):\s*[|>][-+]?\s*(?:#.*)?$')
YAML_VALUE = re.compile(r'(\s*(?:-\s+)?([\w-]+):\s+)(?![|>\[{&*!#])(.*\S)\s*$')


def _yaml_value(line: str) -> Span | None:
    m = YAML_VALUE.match(line)
    if not m or m.group(2) not in YAML_PROSE_KEYS:
        return None
    value = m.group(3)
    quoted = len(value) > 1 and value[0] in '"\'' and value.endswith(value[0])
    quote = value[0] if quoted else ''
    body = value[len(quote) : len(value) - len(quote)]
    return Span(m.group(1) + quote, body, tail=quote, joinable=False)


def _classify_yaml(lines: list[str]) -> list[str | Span]:
    """Prose block scalars and prose values; elsewhere (a run block, data) only # comments."""
    out: list[str | Span] = []
    block: tuple[int, bool] | None = None  # (indent of the key, is it prose?)
    for line in lines:
        indent = len(line) - len(line.lstrip())
        if block is not None and (not line.strip() or indent > block[0]):
            out.append(_span(INDENT, line) if block[1] and line.strip() else _hash_comment(line))
            continue
        block = None
        m = YAML_BLOCK.match(line)
        if m:
            block = (indent, m.group(2) in YAML_PROSE_KEYS)
        value = None if m else _yaml_value(line)
        out.append(value if value is not None else _hash_comment(line))
    return out


def _docstring_lines(tree: ast.Module) -> dict[int, tuple[int, int]]:
    docs: dict[int, tuple[int, int]] = {}
    for node in ast.walk(tree):
        kinds = (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
        body = getattr(node, 'body', None)
        if not isinstance(node, kinds) or not body:
            continue
        first = body[0]
        value = getattr(first, 'value', None)
        is_text = isinstance(value, ast.Constant) and isinstance(value.value, str)
        if isinstance(first, ast.Expr) and is_text:
            for n in range(first.lineno, first.end_lineno + 1):
                docs[n] = (first.lineno, first.end_lineno)
    return docs


DOC_OPEN = re.compile(r'\s*[rbuRBU]{0,2}("""|\'\'\'|"|\')')


def _docstring_span(line: str, n: int, start: int, end: int) -> str | Span:
    indent = INDENT.match(line).group(0)
    m = DOC_OPEN.match(line) if n == start else None
    if m:
        delim, rest = m.group(1), line[m.end() :]
        if start == end:
            close = rest.rfind(delim)
            return Span(line[: m.end()], rest[:close], tail=rest[close:])
        return Span(line[: m.end()], rest, cont=indent, joinable=bool(rest.strip()))
    if n == end:
        at = max(line.rfind('"""'), line.rfind("'''"))
        if at > 0 and line[:at].strip():
            return Span(indent, line[len(indent) : at], tail=line[at:])
        return line
    return _span(INDENT, line) if line.strip() else line


def _classify_python(lines: list[str]) -> list[str | Span] | None:
    """Comments (the tokenizer's) and docstrings (the syntax tree's); None if it does not parse."""
    source = '\n'.join(lines)
    try:
        docs = _docstring_lines(ast.parse(source))
        tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    except (SyntaxError, tokenize.TokenError, ValueError):
        return None
    comments = {t.start[0] for t in tokens if t.type == tokenize.COMMENT}
    out: list[str | Span] = []
    for n, line in enumerate(lines, 1):
        if TEST_NAME.search(line):
            out.append(line)
        elif n in docs:
            out.append(_docstring_span(line, n, *docs[n]))
        elif n in comments:
            out.append(_hash_comment(line))
        else:
            out.append(line)
    return out


# ---- paragraphs ----------------------------------------------------------------------------


def _wrap(words: list[str], head: str, cont: str, width: int) -> list[str]:
    lines: list[str] = []
    cur = ''
    for word in words:
        prefix = cont if lines else head
        if cur and len(prefix) + len(cur) + 1 + len(word) > width:
            lines.append(prefix + cur)
            cur = word
        else:
            cur = f'{cur} {word}' if cur else word
    lines.append((cont if lines else head) + cur)
    return [line.rstrip() for line in lines]


def _group(items: list[str | Span], i: int) -> list[Span]:
    item = items[i]
    group = [item]
    if not item.joinable or not item.body.strip() or item.body[:1].isspace():
        return group
    for nxt in items[i + 1 :]:
        if not isinstance(nxt, Span) or not nxt.joinable or nxt.starts:
            break
        if not nxt.body.strip() or nxt.head != item.cont or nxt.body[:1].isspace():
            break
        group.append(nxt)
    return group


def _rewrite(group: list[Span]) -> list[str]:
    item = group[0]
    original = [g.head + g.body + g.tail for g in group]
    if any(keep in line for keep in KEEP for line in original):
        return original
    text = ' '.join(g.body.strip() for g in group) if len(group) > 1 else item.body
    new = scrub_prose(text)
    if new == text:
        return original
    if text[:1].strip() and new[:1].isspace():
        new = _cap(new.lstrip())
    if len(group) > 1:
        if not new.strip():
            return []
        width = max(*(len(o) for o in original), len(item.head) + 40)
        return _wrap(new.split(), item.head, item.cont, width)
    if new.strip() or item.tail:
        return [item.head + new + item.tail if item.tail else (item.head + new).rstrip()]
    # the comment was only a process tag: it goes, the code it followed stays
    return [item.code.rstrip()] if item.code.strip() else []


def _paragraphs(items: list[str | Span]) -> list[str]:
    out: list[str] = []
    i = 0
    while i < len(items):
        item = items[i]
        if isinstance(item, str):
            out.append(item)
            i += 1
            continue
        group = _group(items, i)
        i += len(group)
        out.extend(_rewrite(group))
    return out


# ---- files ---------------------------------------------------------------------------------


def _kind(rel: str) -> str | None:
    name = rel.rsplit('/', 1)[-1]
    if name in NAMED_KINDS:
        return NAMED_KINDS[name]
    suffix = Path(name).suffix
    return next((kind for kind, suffixes in KINDS.items() if suffix in suffixes), None)


def _is_test_code(rel: str) -> bool:
    return rel.rsplit('/', 1)[-1].startswith(('test_', 'tst_'))


CLASSIFY = {
    'prose': _classify_markdown,
    'slash': _classify_slash,
    'hash': _classify_hash,
    'yaml': _classify_yaml,
    'python': _classify_python,
}


def scrub_text(text: str, rel: str) -> str:
    """The scrubbed content of the file at `rel`."""
    marker = GENERATED.get(rel)
    if marker and f'\n{marker}' in text:
        at = text.index(f'\n{marker}') + 1
        return _scrub_text(text[:at], rel) + text[at:]
    return _scrub_text(text, rel)


def _scrub_text(text: str, rel: str) -> str:
    lines = [personal(line) for line in text.split('\n')]
    kind = _kind(rel)
    if kind is None or _is_test_code(rel):
        return '\n'.join(lines)
    items = CLASSIFY[kind](lines)
    return '\n'.join(lines if items is None else _paragraphs(items))


def _notebook(py_text: str) -> str:
    """The notebook a jupytext source renders to: cells numbered from 0, outputs stripped."""
    import jupytext  # noqa: PLC0415 - only a tree with paired notebooks needs it

    notebook = jupytext.reads(py_text, fmt='py:percent')
    for index, cell in enumerate(notebook.cells):
        cell['id'] = str(index)
    return jupytext.writes(notebook, fmt='ipynb') + '\n'


def _listing(tree: Path) -> list[Path]:
    """A git checkout's tracked files (untracked build output is not released); else all."""
    if (tree / '.git').exists():
        listed = subprocess.run(
            ['git', '-C', str(tree), 'ls-files', '-z'], capture_output=True, check=True
        )
        return [tree / rel for rel in sorted(listed.stdout.decode().split('\0')) if rel]
    return sorted(tree.rglob('*'))


def iter_files(tree: Path, *, skip_hidden: bool) -> list[tuple[str, Path]]:
    """The text files the scrub reads, as (tree-relative path, path)."""
    files = []
    for path in _listing(tree):
        if not path.is_file() or path.is_symlink():
            continue
        rel = path.relative_to(tree).as_posix()
        if rel in SKIP_FILES or any(rel.startswith(d) or f'/{d}' in rel for d in SKIP_DIRS):
            continue
        if rel.startswith(PINNED) or PINNED_PROJECT.match(rel):
            continue
        if not (skip_hidden and rel.startswith(HIDDEN_TIERS)):
            files.append((rel, path))
    return files


def _renotebook(tree: Path, sources: dict[str, tuple[str, str]], *, check: bool) -> list[str]:
    """Render each notebook paired with a jupytext source again from the scrubbed source."""
    changed = []
    for rel, (before, after) in sources.items():
        notebook = tree / (rel[:-3] + '.ipynb')
        if not notebook.is_file() or notebook.is_symlink():
            continue
        current = notebook.read_text(encoding='utf-8')
        if current not in {_notebook(before), _notebook(after)}:
            continue  # not a rendering of its source: the manual list's
        rendered = _notebook(after)
        if rendered != current:
            changed.append(rel[:-3] + '.ipynb')
            if not check:
                notebook.write_text(rendered, encoding='utf-8')
    return changed


def scrub_tree(tree: Path, *, check: bool = False, skip_hidden: bool = False) -> list[str]:
    """Scrub every text file under `tree` in place; return the changed paths."""
    changed = []
    sources: dict[str, tuple[str, str]] = {}
    for rel, path in iter_files(tree, skip_hidden=skip_hidden):
        try:
            text = path.read_text(encoding='utf-8')
        except (UnicodeDecodeError, OSError):
            continue
        new = scrub_text(text, rel)
        if rel.endswith('.py'):
            sources[rel] = (text, new)
        if new != text:
            changed.append(rel)
            if not check:
                path.write_text(new, encoding='utf-8')
    return changed + _renotebook(tree, sources, check=check)


def main(argv: list[str] | None = None) -> int:
    """Command line: scrub, or with --check report, one tree."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--tree', required=True, type=Path, help='the local tree to scrub')
    parser.add_argument('--check', action='store_true', help='report what would change')
    parser.add_argument('--skip-hidden', action='store_true', help='leave hidden tiers alone')
    args = parser.parse_args(argv)
    if not args.tree.is_dir():
        print(f'scrub: not a directory: {args.tree}', file=sys.stderr)
        return 2
    changed = scrub_tree(args.tree, check=args.check, skip_hidden=args.skip_hidden)
    for rel in changed:
        print(rel)
    verb = 'would change' if args.check else 'changed'
    print(f'scrub: {len(changed)} file(s) {verb}', file=sys.stderr)
    return 1 if (args.check and changed) else 0


if __name__ == '__main__':
    sys.exit(main())
