"""Check the retired absorption field across declared public files."""

import hashlib
import json
import re
from pathlib import Path

FIELD = re.compile(r'abscor[\s_-]*2', re.IGNORECASE)
# Unicode IGNORECASE also matches long s; retain that UTF-8 spelling in the byte prefilter.
FULLPROF_INPUTS = {'.pcr', '.inp', '.new'}


def surface_text(path):
    data = path.read_bytes()
    suffix = path.suffix.lower()
    # JSON escapes and FullProf's exemption grammar require decoding even without a literal prefix.
    if suffix not in FULLPROF_INPUTS | {'.json', '.ipynb'}:
        folded = data.lower()
        if b'abscor' not in folded and b'ab\xc5\xbfcor' not in folded:
            return ''
    raw = data.decode('utf-8', errors='replace')
    if suffix in {'.json', '.ipynb'}:
        data = json.loads(raw)
        if path.name == 'python-surface.json':
            assert 'public' in data, 'A Python declaration must prove its live public surface'
            # The manifest also records retired names as historical metadata.
            data = {
                'public': data['public'],
                'members': data.get('classification', {}).get('members', {}),
            }
        return json.dumps(data, ensure_ascii=False)
    return raw


def violations(root, scopes):
    root = Path(root)
    hits = []
    for name in scopes:
        target = root / name
        assert target.exists(), 'Each declared public surface must exist: ' + name
        candidates = sorted(target.rglob('*')) if target.is_dir() else [target]
        checked = []
        for path in candidates:
            assert not (path.is_symlink() and path.is_dir()), (
                'A public surface must not hide an unenumerated linked directory: ' + str(path)
            )
            if path.is_dir():
                continue
            if path.suffix.lower() in FULLPROF_INPUTS:
                text = surface_text(path)
                titled = re.match(r'COMM\s', text.lstrip(), re.IGNORECASE)
                patterns = re.search(r'^\s*NPATT\s+[1-9]\d*\b', text, re.MULTILINE)
                weights = re.search(r'^\s*W_PAT\s+[-+.\d]', text, re.MULTILINE)
                jobs = re.search(r'^\s*!\s*Job\b.*\bNpr\b', text, re.IGNORECASE | re.MULTILINE)
                if jobs and (titled or (patterns and weights)):
                    continue
            checked.append(path)
            if FIELD.search(surface_text(path)):
                hits.append(path.relative_to(root).as_posix())
        assert checked, 'Each public surface must contain nonexempt content: ' + name
    return sorted(set(hits))


FROZEN_STAMP_DATA = 'tests/fixtures/assistant_dev_integration/prechange_stamp_codec.inc'
FROZEN_CPP_DATA = {
    FROZEN_STAMP_DATA: '8b300f35b31f9f5b9bf54a5af9e4e470255f8983817ef4f463b91d46707d7800',
}

CPP_SUFFIXES = {'.cpp', '.cxx', '.cc', '.c', '.h', '.hpp', '.hxx', '.hh', '.inc', '.ipp', '.tpp'}
CPP_DATA = re.compile(
    r'(?:u8|u|U|L)?R"(?P<delimiter>[^ ()\\\t\r\n]{0,16})\(.*?\)(?P=delimiter)"'
    r'|//[^\n]*|/\*.*?\*/'
    r'|(?:u8|u|U|L)?"(?:\\.|[^"\\])*"'
    r"|(?:u8|u|U|L)?'(?:\\.|[^'\\])*'",
    re.DOTALL,
)


def compiled_violations(root, scopes):
    """Find retired C++ identifiers while retaining historical input data and comments."""
    root = Path(root)
    hits = []
    for name in scopes:
        target = root / name
        assert target.exists(), 'Every compiled source inventory scope must exist: ' + name
        candidates = sorted(target.rglob('*')) if target.is_dir() else [target]
        checked = []
        for path in candidates:
            assert not (path.is_symlink() and path.is_dir()), (
                'Compiled source inventory must not omit a linked directory: ' + str(path)
            )
            if not path.is_file() or path.suffix.lower() not in CPP_SUFFIXES:
                continue
            checked.append(path)
            relative = path.relative_to(root).as_posix()
            if relative in FROZEN_CPP_DATA:
                if hashlib.sha256(path.read_bytes()).hexdigest() != FROZEN_CPP_DATA[relative]:
                    hits.append(relative)
                continue
            if re.search(
                r'^\s*#\s*include\s*[<\"][^>\"\n]*prechange_stamp_codec\.inc[>\"]',
                path.read_text(encoding='utf-8'),
                re.MULTILINE,
            ):
                hits.append(relative)
            source = re.sub(r'\\\r?\n', '', path.read_text(encoding='utf-8'))
            code = CPP_DATA.sub(' ', source)
            if re.search(r'\babscor2\b', code):
                hits.append(path.relative_to(root).as_posix())
        assert checked, 'Every compiled inventory scope must contain source: ' + name
    return sorted(set(hits))
