# SPDX-License-Identifier: BSD-3-Clause
"""Check a change against the public-content rules: its files, commit messages and pull request.

    python tools/public-release/content_check.py --base SHA|root [--head SHA]
        [--title TEXT] [--body-file PATH]

`--base root` (or GitHub's all-zero base) checks every file and every commit up to --head: a
repository's first push.

edi is public, or about to be, so everything a change adds must be fit to publish. This runs in CI
on every push and pull request (`.github/workflows/content.yml`) and exits 1 naming each problem.

Files: every version a commit in the range writes, as git stores it, even one a later commit
deletes or cleans (a symlink's version is its target):
- no credential (`scan.py`'s rules);
- every file and archive member is held as `scan.py` holds a member: no personal or run path, no
  private citation, and a process reference only inside the name of a test, in tests as anywhere;
- nothing the scrub (`scrub.py`) would still rewrite.

Commit messages (each commit in the range) and the pull request's title and body:
- a subject or title of at most 72 characters, and a short body;
- no credential, no task, issue or hub ids, no personal or run paths, no private citations;
- no attribution lines (`Co-Authored-By:`, `Signed-off-by:`, "Generated with", and the like).
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import scan  # the sibling modules, importable from any working directory
import scrub
from patterns import RESIDUE

SUBJECT_LIMIT = 72
BODY_LIMIT = 800  # a commit body of a few sentences
PR_BODY_LIMIT = 1500  # a pull request's summary
ATTRIBUTION = re.compile(
    r'(?im)^\s*(?:co-authored-by|signed-off-by|claude-session)\s*:|generated with|\N{ROBOT FACE}'
)


def _git(*args: str) -> str:
    result = subprocess.run(['git', *args], capture_output=True, text=True, check=False)
    if result.returncode:
        sys.exit(f'content check: git {" ".join(args)} failed: {result.stderr.strip()[:300]}')
    return result.stdout


def text_problems(where: str, text: str, *, first_limit: int, rest_limit: int) -> list[str]:
    """The public-rule problems of one message: a first line, then a body."""
    first, _, rest = text.strip().partition('\n')
    secrets = [rule for rule, rx in scan.CREDENTIALS.items() if rx.search(text)]
    problems = [f'{where}: {rule} (not shown)' for rule in secrets]
    if len(first) > first_limit:
        problems.append(f'{where}: the first line is {len(first)} characters, over {first_limit}')
    if len(rest.strip()) > rest_limit:
        problems.append(f'{where}: the body is {len(rest.strip())} characters, over {rest_limit}')
    problems.extend(
        f'{where}: {cls}: {"(not shown)" if secrets else line.strip()[:120]}'
        for cls, rx in RESIDUE.items()
        for line in text.splitlines()
        if rx.search(line)
    )
    if ATTRIBUTION.search(text):
        problems.append(f'{where}: an attribution line')
    return problems


def commit_problems(base: str, head: str) -> list[str]:
    """Each commit message in ``base..head`` against the public rules."""
    problems = []
    span = head if base == 'root' else f'{base}..{head}'
    for sha in _git('rev-list', '--reverse', span).split():
        message = _git('log', '-1', '--format=%B', sha)
        problems += text_problems(
            f'commit {sha[:12]}', message, first_limit=SUBJECT_LIMIT, rest_limit=BODY_LIMIT
        )
    return problems


def _versions(base: str, head: str) -> list[tuple[str, str]]:
    """``(path, blob)`` for each file version a commit in ``base..head`` writes."""
    span = head if base == 'root' else f'{base}..{head}'
    versions = {}
    for sha in _git('rev-list', span).split():
        # A merge is compared with each parent, so what it brings in is read as well.
        raw = _git('diff-tree', '-r', '-m', '--root', '--no-commit-id', '--no-renames', '-z', sha)
        fields = raw.split('\0')
        for meta, path in zip(fields[0::2], fields[1::2], strict=False):
            _, mode, _, blob, status = meta.split()
            if status != 'D' and mode != '160000':  # a submodule's commit is not content here
                versions[path, blob] = None
    return list(versions)


def _blobs(shas: list[str]) -> dict[str, bytes]:
    """Each blob's bytes, read in one ``git cat-file --batch``."""
    batch = subprocess.run(
        ['git', 'cat-file', '--batch'],
        input=''.join(f'{sha}\n' for sha in shas).encode(),
        capture_output=True,
        check=False,
    )
    if batch.returncode:
        sys.exit(f'content check: git cat-file failed: {batch.stderr.decode()[:300]}')
    out, at = {}, 0
    for sha in shas:
        end = batch.stdout.index(b'\n', at)
        size = int(batch.stdout[at:end].split()[2])
        out[sha] = batch.stdout[end + 1 : end + 1 + size]
        at = end + 2 + size
    return out


def file_problems(base: str, head: str) -> list[str]:
    """Every file version written in ``base..head`` against the public rules."""
    versions = _versions(base, head)
    blobs = _blobs(sorted({blob for _, blob in versions}))
    try:
        report = scan.judge(((rel, blobs[blob]) for rel, blob in versions), strict=_every)
    except scan.UnreadableArchiveError as err:
        return [f'{err}: an archive that cannot be read']
    problems = [f'{rel}:{n}: {rule}' for rel, n, rule in report.credentials]
    problems += [f'{rel}:{n}: {cls}' for rel, n, cls in report.members]
    for rel, blob in versions:
        if not _scrubbed(rel):
            continue
        try:
            text = blobs[blob].decode('utf-8')
        except UnicodeDecodeError:
            continue
        if scrub.scrub_text(text, rel) != text:
            problems.append(f'{rel}: the scrub would rewrite it (tools/public-release/scrub.py)')
    return list(dict.fromkeys(problems))


def _every(_name: str) -> bool:
    return True


def _scrubbed(rel: str) -> bool:
    """Whether the scrub reads the file at ``rel`` when it makes the released tree."""
    skipped = rel.startswith(scrub.HIDDEN_TIERS) or rel in scrub.SKIP_FILES
    skipped = skipped or any(rel.startswith(d) or f'/{d}' in rel for d in scrub.SKIP_DIRS)
    return not (skipped or rel.startswith(scrub.PINNED) or scrub.PINNED_PROJECT.match(rel))


def main(argv: list[str] | None = None) -> int:
    """Command line: check one change; exit 1 on any problem."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--base', required=True, help='the commit the change starts from')
    parser.add_argument('--head', default='HEAD', help="the change's last commit (default HEAD)")
    parser.add_argument('--title', help="the pull request's title")
    parser.add_argument('--body-file', type=Path, help="a file holding the pull request's body")
    args = parser.parse_args(argv)
    if set(args.base) == {'0'}:
        args.base = 'root'
    problems = file_problems(args.base, args.head) + commit_problems(args.base, args.head)
    if args.title is not None:
        body = args.body_file.read_text(encoding='utf-8') if args.body_file else ''
        problems += text_problems(
            'pull request',
            f'{args.title}\n{body}',
            first_limit=SUBJECT_LIMIT,
            rest_limit=PR_BODY_LIMIT,
        )
    for problem in problems:
        print(f'content check: {problem}')
    print(f'content check: {len(problems)} problem(s)', file=sys.stderr)
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
