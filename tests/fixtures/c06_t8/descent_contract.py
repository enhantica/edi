"""Retired descents may be migration prose, never advertised choices or examples."""

import json
import re
from pathlib import Path

RETIRED = ('fast_descent_linear_snap', 'fast_descent_guarded_linear_snap')
VALID = {'ladder', 'fast_descent', 'multistart_prune'}
SNAP = re.compile(
    r'fast[_\s-]+descent(?:[_\s-]+with)?[_\s-]+(?:guarded[_\s-]+)?linear[_\s-]+snap', re.IGNORECASE
)
RETIRED_NOTICE = re.compile(
    r'\b(?:is|are|was|were)\s+(?:retired|removed)\b|^\s*(?:Retired|Removed):', re.IGNORECASE
)


_PROSE_SPLIT = re.compile(r'\n\s*\n|(?<=[.!?])\s+|\n(?=\s*(?:[-*+]\s|\d+[.)]\s|#))|(?<=:)\s*\n')
_ACTIVE_CHOICE = re.compile(
    r'(?:choose|select|use|--descent)(?:\s+|=)(?:the\s+)?[`\"\']?' + SNAP.pattern,
    re.IGNORECASE,
)


def _advertises_choice(text):
    for match in _ACTIVE_CHOICE.finditer(text):
        if not re.search(
            r'\b(?:(?:do|must|should)\s+not|never)\s*$', text[: match.start()], re.IGNORECASE
        ):
            return True
    return False


def _markdown_units(raw):
    prose = []
    fence = None
    for line in raw.splitlines(keepends=True):
        mark = re.match(r'\s*(`{3,}|~{3,})', line)
        if mark and (fence is None or (mark[1][0] == fence[0] and len(mark[1]) >= len(fence))):
            yield from ((part, False) for part in _PROSE_SPLIT.split(''.join(prose)))
            prose.clear()
            fence = mark[1] if fence is None else None
        elif fence is not None:
            yield line, True
        else:
            prose.append(line)
    yield from ((part, False) for part in _PROSE_SPLIT.split(''.join(prose)))


def advertisements(root, scopes):
    root = Path(root)
    found = []
    for name in scopes:
        target = root / name
        assert target.exists(), 'Each descent surface must exist: ' + name
        paths = sorted(target.rglob('*')) if target.is_dir() else [target]
        checked = 0
        for path in paths:
            assert not (path.is_symlink() and path.is_dir()), (
                'Descent surfaces must not conceal linked directory contents'
            )
            if path.is_dir():
                continue
            raw = path.read_bytes().decode('utf-8', errors='replace')
            checked += 1
            structured = path.suffix.lower() in {'.json', '.ipynb'}
            if structured:
                raw = json.dumps(json.loads(raw), ensure_ascii=False)
            units = (
                [(raw, True)]
                if structured
                else _markdown_units(raw)
                if path.suffix.lower() == '.md'
                else ((line, False) for line in raw.splitlines())
            )
            found.extend(
                str(path.relative_to(root))
                for text, literal in units
                if SNAP.search(text)
                and (literal or _advertises_choice(text) or not RETIRED_NOTICE.search(text))
            )
        assert checked, 'Each descent surface must contain checked files: ' + name
    return sorted(set(found))
