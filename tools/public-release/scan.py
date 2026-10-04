# SPDX-License-Identifier: BSD-3-Clause
"""Scan a local tree for credentials before it is published, and count the private residue.

    python tools/public-release/scan.py --tree PATH [--residue] [--gitleaks]

Every file is read line by line against credential rules: cloud keys, GitHub, Slack and Google
tokens, and private keys. Each rule matches a credential's own format; a generic "a long value
assigned to a secret-sounding name" rule is left to gitleaks, whose allowlist reviews its false
positives. A finding prints its path, line and rule, never the value, and makes the scan exit 1.

An archive is read member by member, nested archives too (zip, tar, and gzip, bzip2, xz or zstd
files), so a member is scanned like any file and named `archive!member`. An archive that cannot be
read refuses the scan (exit 1): an unread member is never certified. The scrub rewrites no archive,
so an archive member is held to the scrub's result instead: any personal or run path, private
citation, or process reference in a member, other than on a line naming a test, is a finding that
fails the scan (`member_findings`; the snapshot and the cutover rehearsal refuse on it too).

`--residue` also counts the scrub's three classes (`patterns.py`) per file and in total; residue
is reported, it does not fail the scan (the scrub and its reviewed manual-edit list own it).
`--skip-hidden` leaves the hidden test tiers (`tests/unit`, `tests/integration`, `tests/system`)
unread. `--gitleaks` also runs gitleaks over the tree when it is on PATH, as a second scanner;
a gitleaks finding fails the scan too.
"""

from __future__ import annotations

import argparse
import bz2
import gzip
import io
import itertools
import json
import lzma
import os
import re
import shutil
import struct
import subprocess
import sys
import tarfile
import tempfile
import zipfile
import zlib
from collections import Counter
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import NamedTuple

from compression import zstd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from patterns import (  # sibling module
    RESIDUE,
    RESIDUE_LITERALS,
    RESIDUE_WINDOWS,
    mask_test_names,
)

CREDENTIALS = {
    'AWS access key': re.compile(r'\b(?:AKIA|ASIA)[0-9A-Z]{16}\b'),
    'GitHub token': re.compile(r'\bgh[pousr]_[A-Za-z0-9]{36,}\b'),
    'GitHub fine-grained token': re.compile(r'\bgithub_pat_[A-Za-z0-9_]{60,}\b'),
    'Slack token': re.compile(r'\bxox[abposr]-[A-Za-z0-9-]{10,}\b'),
    'Google API key': re.compile(r'\bAIza[0-9A-Za-z_-]{35}\b'),
    'private key': re.compile(r'-----BEGIN (?:[A-Z]+ )*PRIVATE KEY(?: BLOCK)?-----'),
    'AWS secret key': re.compile(
        r'(?i)\baws_?secret_?(?:access_?)?key\s*[:=]\s*["\']?[A-Za-z0-9/+=]{40}\b'
    ),
}
# Per rule, substrings of which every match contains at least one (case-folded for the rule that
# ignores case); each tuple must stay complete for its pattern above.
CREDENTIAL_LITERALS = {
    'AWS access key': ('AKIA', 'ASIA'),
    'GitHub token': ('ghp_', 'gho_', 'ghu_', 'ghs_', 'ghr_'),
    'GitHub fine-grained token': ('github_pat_',),
    'Slack token': ('xox',),
    'Google API key': ('AIza',),
    'private key': ('PRIVATE KEY',),
    'AWS secret key': ('aws',),
}
CASEFOLDED = {'AWS secret key'}
WINDOW_MARGIN = 256  # bytes past a candidate that a windowed class's window keeps
if CREDENTIAL_LITERALS.keys() != CREDENTIALS.keys() or RESIDUE_LITERALS.keys() != RESIDUE.keys():
    raise SystemExit('scan: every pattern needs its prefilter literals')
SKIP_DIRS = ('.git/', '.pixi/', 'build/', 'site/', 'node_modules/', '__pycache__/')
HIDDEN_TIERS = ('tests/unit/', 'tests/integration/', 'tests/system/')


def _ls(tree: Path, *args: str) -> list[str]:
    listed = subprocess.run(
        ['git', '-C', str(tree), 'ls-files', '-z', *args], capture_output=True, check=True
    )
    return [rel for rel in listed.stdout.decode().split('\0') if rel]


def _files(tree: Path, *, skip_hidden: bool = False) -> list[tuple[str, Path]]:
    """Every tracked file, wherever it is, and every untracked one outside build and cache dirs.

    A symlink is listed too: its target is what git stores, so that is what is read.
    """
    if (tree / '.git').exists():
        others = _ls(tree, '--others', '--exclude-standard')
        rels = set(_ls(tree, '--cached')) | {
            rel for rel in others if not rel.startswith(SKIP_DIRS)
        }
    else:
        found = (path.relative_to(tree).as_posix() for path in tree.rglob('*'))
        rels = {rel for rel in found if not rel.startswith(SKIP_DIRS)}
    out = []
    for rel in sorted(rels):
        path = tree / rel
        if skip_hidden and rel.startswith(HIDDEN_TIERS):
            continue
        if path.is_symlink() or path.is_file():
            out.append((rel, path))
    return out


def _read(path: Path) -> bytes:
    """A file's bytes; for a symlink, its target, never what it points to."""
    return os.fsencode(path.readlink()) if path.is_symlink() else path.read_bytes()


class UnreadableArchiveError(Exception):
    """An archive whose members cannot be read: never certified, always refused."""


TAR = ('.tar', '.tgz', '.tar.gz', '.tbz2', '.tar.bz2', '.txz', '.tar.xz', '.tar.zst')
STREAMS = {'.gz': gzip.decompress, '.bz2': bz2.decompress, '.xz': lzma.decompress}
STREAMS['.zst'] = zstd.decompress
# Archives are recognised by their bytes, so a renamed one is read too; the name is the fallback.
SIGNATURES = (
    (b'PK\x03\x04', '.zip'),
    (b'PK\x05\x06', '.zip'),
    (b'\x1f\x8b', '.gz'),
    (b'BZh', '.bz2'),
    (b'\xfd7zXZ\x00', '.xz'),
    (b'\x28\xb5\x2f\xfd', '.zst'),
    (b"7z\xbc\xaf'\x1c", '.7z'),
    (b'Rar!\x1a\x07', '.rar'),
    (b'\x89PNG\r\n\x1a\n', '.png'),
)
# Archive formats read nowhere here: one named so refuses even without its signature.
UNSUPPORTED = ('.7z', '.rar', '.lz', '.lz4', '.lzma', '.z', '.cab', '.arj', '.iso')
UNREADABLE = (zipfile.BadZipFile, tarfile.TarError, OSError, EOFError, lzma.LZMAError, ValueError)
UNREADABLE += (zstd.ZstdError, RuntimeError, zlib.error, struct.error)  # encrypted, damaged
MAX_DEPTH = 4  # nested archives deeper than this refuse rather than recurse without end


def _kind(name: str, data: bytes) -> str | None:
    """What container ``data`` is, by its bytes first and then by its name; None for neither."""
    if len(data) > 262 and data[257:262] == b'ustar':
        return '.tar'
    for signature, kind in SIGNATURES:
        if data.startswith(signature):
            return '.tar' if kind in STREAMS and _is_tar(STREAMS[kind], data) else kind
    lower = name.lower()
    return next((s for s in ('.zip', *TAR, *STREAMS, *UNSUPPORTED) if lower.endswith(s)), None)


def _is_tar(decompress: Callable[[bytes], bytes], data: bytes) -> bool:
    try:
        inner = decompress(data)
    except UNREADABLE:
        return False  # the stream branch reports it unreadable
    return len(inner) > 262 and inner[257:262] == b'ustar'


def _png_texts(data: bytes) -> list[tuple[str, bytes]]:
    """A PNG's compressed text chunks (zTXt, compressed iTXt), decoded.

    Plain text chunks need no decoding: they are scanned already, as the file's own bytes.
    """
    out, at = [], 8
    while at + 8 <= len(data):
        size, chunk = struct.unpack('>I4s', data[at : at + 8])
        body = data[at + 8 : at + 8 + size]
        at += 12 + size
        keyword, _, rest = body.partition(b'\0')
        if chunk == b'zTXt':
            out.append((f'zTXt:{keyword.decode("latin-1")}', zlib.decompress(rest[1:])))
        elif chunk == b'iTXt' and rest[:1] == b'\x01':
            _lang, _, rest = rest[2:].partition(b'\0')
            _translated, _, text = rest.partition(b'\0')
            out.append((f'iTXt:{keyword.decode("latin-1")}', zlib.decompress(text)))
    return out


def _members(name: str, data: bytes, kind: str) -> list[tuple[str, bytes]]:
    """The members of the container ``name`` holds, as ``(member, data)``."""
    if kind == '.zip':
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            return [(i.filename, archive.read(i)) for i in archive.infolist() if not i.is_dir()]
    if kind == '.tar':
        with tarfile.open(fileobj=io.BytesIO(data), mode='r:*') as archive:
            files = [m for m in archive.getmembers() if m.isfile()]
            handles = [(m.name, archive.extractfile(m)) for m in files]
            return [(member, handle.read()) for member, handle in handles if handle is not None]
    if kind == '.png':
        return _png_texts(data)
    if kind in STREAMS:
        base = name.rsplit('/', 1)[-1]
        return [(base[: -len(kind)] if base.lower().endswith(kind) else base, STREAMS[kind](data))]
    raise ValueError(f'{kind} archives cannot be read here')  # refused, never skipped


def _entries(name: str, data: bytes, depth: int = 0) -> list[tuple[str, bytes]]:
    """``(name, data)`` and, for a container, each member below it as ``(name!member, data)``."""
    kind = _kind(name, data)
    if kind is None:
        return [(name, data)]
    if depth >= MAX_DEPTH:
        raise UnreadableArchiveError(f'{name}: archives nested deeper than {MAX_DEPTH}')
    try:
        members = _members(name, data, '.tar' if kind in TAR else kind)
    except UNREADABLE as err:
        raise UnreadableArchiveError(f'{name}: {type(err).__name__}: {err}') from err
    out = [(name, data)]
    for member, content in members:
        out += _entries(f'{name}!{member}', content, depth + 1)
    return out


class Report(NamedTuple):
    """One pass's findings: credentials, residue counts and archive-member findings."""

    credentials: list[tuple[str, int, str]]
    residue: dict[str, Counter[str]]
    members: list[tuple[str, int, str]]


# One pass over a file's bytes finds every literal at once. Every literal is ASCII, and decoding
# never makes an ASCII character out of other bytes, so the decoded text holds a literal exactly
# when the bytes do. The rule ignoring case takes its literal in any case, and the one non-ASCII
# letter folding into it (U+017F folds to s).
_LITERAL_OWNERS: dict[bytes, list[tuple[str, str]]] = {}
for _rule, _literals in CREDENTIAL_LITERALS.items():
    for _literal in _literals:
        _LITERAL_OWNERS.setdefault(_literal.encode(), []).append(('rule', _rule))
for _cls, _literals in RESIDUE_LITERALS.items():
    for _literal in _literals:
        _LITERAL_OWNERS.setdefault(_literal.encode(), []).append(('class', _cls))
_FOLD = '\u017f'.encode()
# The literal ignoring case is listed in every case (a case-insensitive group would cost the
# pattern its fast scan for first characters).
_CASES = [bytes(c) for c in itertools.product(*((ord(x.lower()), ord(x.upper())) for x in 'aws'))]
_ORDERED = sorted((lit for lit in _LITERAL_OWNERS if lit != b'aws'), key=len, reverse=True)
_ANY_LITERAL = re.compile(b'|'.join(map(re.escape, [*_CASES, _FOLD, *_ORDERED])))
# The case-ignoring rule's core, contiguous, at its literal: a literal counts only where the core
# follows. Of its letters only s has a non-ASCII case, U+017F, so the core admits that in each s
# position, and an U+017F counts only within such a core.
_AWS_CORE = re.compile(rb'(?i)aw(?:s|\xc5\xbf)_?(?:s|\xc5\xbf)ecret')


def _window_matches(cls: str, data: bytes, m: re.Match[bytes]) -> bool:
    """Whether the windowed class matches in the window decoded around one of its literals."""
    back, candidate = RESIDUE_WINDOWS[cls]
    at = m.start()
    if not (candidate.match(data, at) or (at and candidate.match(data, at - 1))):
        return False
    window = data[max(0, at - back) : m.end() + WINDOW_MARGIN]
    return RESIDUE[cls].search(window.decode('utf-8', errors='replace')) is not None


def _possible(data: bytes) -> tuple[set[str], set[str]]:
    """The credential rules and residue classes that can match in ``data``'s decoded text.

    A windowed class is tried on each window's own decoding around its literal: a window cut
    mid-character turns the edge into U+FFFD, which only relaxes a lookaround, so the test can
    admit a text but never miss one.
    """
    rules: set[str] = set()
    classes: set[str] = set()
    at = 0
    # Each search starts one byte past the last match's start, not at its end, so a literal
    # overlapping another (`I-` and `-T` in `I-T`) is still seen.
    while (m := _ANY_LITERAL.search(data, at)) is not None:
        at = m.start() + 1
        literal = m.group()
        if literal == _FOLD or literal.lower() == b'aws':
            if _AWS_CORE.search(data, max(0, m.start() - 5), m.start() + 16):
                rules.update(CASEFOLDED)
            continue
        for kind, name in _LITERAL_OWNERS[literal]:
            if kind == 'rule':
                rules.add(name)
            elif name not in classes and (
                name not in RESIDUE_WINDOWS or _window_matches(name, data, m)
            ):
                classes.add(name)
    return rules, classes


def analyse(
    tree: Path,
    *,
    skip_hidden: bool = False,
    only: list[str] | None = None,
    strict: Callable[[str], bool] | None = None,
) -> Report:
    """Read every file and archive member once and judge it line by line; nothing is skipped.

    ``only`` limits the files to those tree-relative paths (a change's files). Archive members are
    held to the scrub's result (``members``); so is every file ``strict`` names.
    """
    files = _files(tree, skip_hidden=skip_hidden)
    if only is not None:
        wanted = set(only)
        files = [(rel, path) for rel, path in files if rel in wanted]
    return judge(((rel, _read(path)) for rel, path in files), strict=strict)


def judge(
    files: Iterable[tuple[str, bytes]], *, strict: Callable[[str], bool] | None = None
) -> Report:
    """Judge each ``(name, bytes)`` and its archive members, as ``analyse`` judges a tree's files.

    Lines are those of ``str.splitlines``, and each line is tested exactly as before. A pattern
    that matches a line matches the whole text, so a text it does not match has no matching line;
    the byte-level test (``_possible``) spares decoding a text no pattern can match.
    """
    report = Report([], {name: Counter() for name in RESIDUE}, [])
    for rel, content in files:
        for name, data in _entries(rel, content):
            # Binary content too: a key pasted into one is as public as one in a text file.
            rules, possible = _possible(data)
            if not rules and not possible:
                continue
            text = data.decode('utf-8', errors='replace')
            credentials = {r: CREDENTIALS[r] for r in rules if CREDENTIALS[r].search(text)}
            classes = {c: RESIDUE[c] for c in possible if RESIDUE[c].search(text)}
            if not credentials and not classes:
                continue
            member = '!' in name or (strict is not None and strict(name))
            for n, line in enumerate(text.splitlines(), 1):
                report.credentials.extend(
                    (name, n, rule) for rule, rx in credentials.items() if rx.search(line)
                )
                for cls, rx in classes.items():
                    if not rx.search(line):
                        continue
                    report.residue[cls][name] += 1
                    if member and not (cls == 'process reference' and _names_a_test(rx, line)):
                        # The scrub rewrites no archive, so a member must already be clean.
                        report.members.append((name, n, cls))
    return report


def _names_a_test(rx: re.Pattern[str], line: str) -> bool:
    """Whether a line's process references all lie inside test names (``mask_test_names``)."""
    return rx.search(mask_test_names(line)) is None


def scan(tree: Path, *, skip_hidden: bool = False) -> list[tuple[str, int, str]]:
    """Every credential finding as (path, line number, rule), archive members included."""
    return analyse(tree, skip_hidden=skip_hidden).credentials


def residue(tree: Path, *, skip_hidden: bool = False) -> dict[str, Counter[str]]:
    """Per class, the matching lines per file and archive member."""
    return analyse(tree, skip_hidden=skip_hidden).residue


def member_findings(tree: Path, *, skip_hidden: bool = False) -> list[tuple[str, int, str]]:
    """Each archive-member line in a residue class, as (archive!member, line, class)."""
    return analyse(tree, skip_hidden=skip_hidden).members


def gitleaks(tree: Path) -> list[str]:
    """Gitleaks' findings over the files (not history) as `path:line rule`; [] when absent."""
    exe = shutil.which('gitleaks')
    if exe is None:
        print('scan: gitleaks is not on PATH; its pass is skipped', file=sys.stderr)
        return []
    with tempfile.TemporaryDirectory() as tmp:
        report = Path(tmp) / 'report.json'
        subprocess.run(
            [
                exe,
                'detect',
                '--no-git',
                '--source',
                str(tree),
                '--report-format',
                'json',
                '--report-path',
                str(report),
                '--exit-code',
                '0',
                '--redact',
            ],
            capture_output=True,
            check=True,
        )
        rows = json.loads(report.read_text() or '[]')
    return [f'{r["File"]}:{r["StartLine"]} {r["RuleID"]}' for r in rows]


def main(argv: list[str] | None = None) -> int:
    """Command line: scan one tree; exit 1 on any credential finding."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--tree', required=True, type=Path, help='the local tree to scan')
    parser.add_argument('--residue', action='store_true', help='count the private residue')
    parser.add_argument('--skip-hidden', action='store_true', help='leave hidden tiers unread')
    parser.add_argument('--gitleaks', action='store_true', help='also run gitleaks if present')
    args = parser.parse_args(argv)
    if not args.tree.is_dir():
        print(f'scan: not a directory: {args.tree}', file=sys.stderr)
        return 2
    try:
        report = analyse(args.tree, skip_hidden=args.skip_hidden)
    except UnreadableArchiveError as err:
        print(f'scan: refused, an archive cannot be read: {err}', file=sys.stderr)
        return 1
    findings = [f'{rel}:{n} {rule}' for rel, n, rule in report.credentials]
    members = report.members
    for name, n, cls in members:
        print(f'archive member: {name}:{n} {cls}')
    if args.gitleaks:
        findings += [f'gitleaks {row}' for row in gitleaks(args.tree)]
    for row in findings:
        print(f'secret found: {row}')
    if args.residue:
        for name, per_file in report.residue.items():
            for rel, count in sorted(per_file.items()):
                print(f'residue: {name}: {rel}: {count}')
            print(
                f'residue total: {name}: {sum(per_file.values())} line(s)'
                f' in {len(per_file)} file(s)'
            )
    count = len(_files(args.tree, skip_hidden=args.skip_hidden))
    print(
        f'scan: {count} file(s) scanned, {len(findings)} credential finding(s), '
        f'{len(members)} archive-member finding(s)',
        file=sys.stderr,
    )
    return 1 if findings or members else 0


if __name__ == '__main__':
    sys.exit(main())
