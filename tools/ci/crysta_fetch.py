# SPDX-License-Identifier: BSD-3-Clause
"""Put crysta's source at one commit on a CI runner and list it for the output checks.

    TOKEN=... python3 tools/ci/crysta_fetch.py SHA

Fetches the commit into $RUNNER_TEMP/crysta, refuses any other, writes the lists source_lists.py
reads, proves the output filter with them and names the checkout and the lists to the later steps.
Nothing a child process prints is passed on: it could be the source.
"""

from __future__ import annotations

import base64
import io
import os
import re
import shutil
import subprocess
import sys
import zipfile
from collections.abc import Iterable, Iterator
from pathlib import Path

import source_lists

ROOT = Path(__file__).resolve().parents[2]
SERVER = os.environ.get('GITHUB_SERVER_URL', 'https://github.com')
REPOSITORY = 'enhantica/crysta'
COLLECTION = 'enhantica/edi-data'


class RefusedError(Exception):
    """The source cannot be fetched, proven or listed."""


def git(where: Path, *args: str, stdin: bytes | None = None, **env: str) -> bytes:
    """Run git quietly; a failure names the command, never its output."""
    run = subprocess.run(
        ['git', '-C', str(where), *args],
        input=stdin,
        capture_output=True,
        check=False,
        env={**os.environ, **env},
    )
    if run.returncode:
        raise RefusedError(f'git {args[0]} exited {run.returncode}')
    return run.stdout


def fetch(home: Path, sha: str, token: str) -> None:
    """Fetch ``sha`` alone, the token in this process's environment only."""
    shutil.rmtree(home, ignore_errors=True)
    home.mkdir(parents=True)
    git(home, 'init', '-q')
    credential = base64.b64encode(f'x-access-token:{token}'.encode()).decode()
    git(
        home,
        'fetch',
        '-q',
        '--depth',
        '1',
        f'{SERVER}/{REPOSITORY}',
        sha,
        GIT_CONFIG_COUNT='1',
        GIT_CONFIG_KEY_0=f'http.{SERVER}/.extraheader',
        GIT_CONFIG_VALUE_0=f'AUTHORIZATION: basic {credential}',
        GIT_TERMINAL_PROMPT='0',
    )
    git(home, 'checkout', '-q', '--detach', sha)
    if git(home, 'rev-parse', 'HEAD').decode().strip() != sha:
        raise RefusedError('the checkout is another commit')


def tree(where: Path, commit: str) -> dict[str, str]:
    """The regular files of a commit: each path and its blob id (links are not files)."""
    found = {}
    listed = git(where, 'ls-tree', '-r', '-z', commit).decode('utf-8', 'surrogateescape')
    for entry in filter(None, listed.split('\0')):
        head, path = entry.split('\t', 1)
        mode, kind, blob = head.split()
        if kind == 'blob' and mode != '120000':
            found[path] = blob
    return found


def contents(where: Path, ids: set[str]) -> Iterator[bytes]:
    """The blobs this repository holds; a sparse checkout lacks some, and none is fetched."""
    asked = '\n'.join(sorted(ids)).encode()
    out = git(where, 'cat-file', '--batch', stdin=asked, GIT_NO_LAZY_FETCH='1')
    at = 0
    while at < len(out):
        end = out.index(b'\n', at)
        head = out[at:end].split()
        at = end + 1
        if head[1] != b'missing':
            yield out[at : at + int(head[2])]
            at += int(head[2]) + 1


def bare(data: bytes) -> set[bytes]:
    """The bare lines of a text file."""
    if not source_lists.is_text(data):
        return set()
    return {line.strip() for line in data.splitlines()}


def opened(files: Iterable[bytes]) -> Iterator[bytes]:
    """Files, and those in a zip: the collection keeps its projects so."""
    for data in files:
        yield data
        if data.startswith(b'PK') and zipfile.is_zipfile(io.BytesIO(data)):
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                yield from (archive.read(name) for name in archive.namelist())


def lists(
    home: Path, sha: str, public: list[tuple[Path, str]]
) -> tuple[set[str], dict[str, bytes], set[str]]:
    """The source's blob ids and written lines without what edi publishes, and that one's ids."""
    files = tree(home, sha)
    written = [blob for path, blob in files.items() if source_lists.written(path)]
    lines = set().union(*map(bare, contents(home, set(written))))
    known: set[str] = set()
    for where, commit in public:
        shown = set(tree(where, commit).values())
        known |= shown
        for data in opened(contents(where, shown)):
            known.add(source_lists.blob_id(data))
            lines -= bare(data)
    blobs = set(files.values()) - known
    listed = {entry: line for line in lines if (entry := source_lists.line_id(line))}
    if not blobs or not listed:
        raise RefusedError('the source lists are empty')
    return blobs, listed, known


def write_lists(
    blobs: set[str], listed: dict[str, bytes], known: set[str], folder: Path
) -> dict[str, str]:
    """Write the lists beside the checkout and name them."""
    marks = {source_lists.mark_entry(line) for line in listed.values()}
    written = {}
    for variable, entries in (
        (source_lists.BLOBS, blobs),
        (source_lists.LINES, listed),
        (source_lists.MARKS, marks),
        (source_lists.PUBLIC, known),
    ):
        path = folder / variable.lower().replace('_', '-')
        path.write_text('\n'.join(sorted(entries)) + '\n', encoding='ascii')
        written[variable] = str(path)
    return written


def prove(home: Path, environment: dict[str, str], sample: bytes) -> None:
    """The filter withholds a listed line and shows an ordinary one."""
    script, quoted = (
        home.parent / 'crysta-filter-proof.sh',
        home.parent / 'crysta-filter-proof.txt',
    )
    try:
        quoted.write_bytes(sample + b'\nthe output filter is in place\n')
        script.write_text(f'cat "{quoted.as_posix()}"\n', encoding='utf-8')
        run = subprocess.run(
            [sys.executable, str(ROOT / 'tools/ci/public_log.py'), str(script)],
            env={**os.environ, **environment},
            capture_output=True,
            check=False,
        )
    finally:
        script.unlink(missing_ok=True)
        quoted.unlink(missing_ok=True)
    shown = run.stdout.split(b'\n')
    if run.returncode or sample in run.stdout or b'the output filter is in place' not in shown:
        raise RefusedError('the output filter does not withhold a source line')


def checkout(root: Path) -> list[tuple[Path, str]]:
    """The commit of edi itself; without one the lists only hold more."""
    try:
        git(root, 'rev-parse', '--verify', 'HEAD^{commit}')
    except RefusedError:
        return []
    return [(root, 'HEAD')]


def collection(home: Path) -> list[tuple[Path, str]]:
    """The public sample collection edi ships; without it the lists only hold more."""
    shutil.rmtree(home, ignore_errors=True)
    home.mkdir(parents=True)
    try:
        git(home, 'init', '-q')
        git(home, 'remote', 'add', 'origin', f'{SERVER}/{COLLECTION}')
        git(home, 'fetch', '-q', '--depth', '1', 'origin', 'main', GIT_TERMINAL_PROMPT='0')
    except RefusedError:
        return []
    return [(home, 'FETCH_HEAD')]


def prepare(temp: Path, sha: str) -> int:
    """Fetch, list and prove; name the checkout and the lists to the later steps."""
    if not re.fullmatch(r'[0-9a-f]{40}', sha):
        raise RefusedError('the commit is not a full id')
    home = temp / 'crysta'
    fetch(home, sha, os.environ['TOKEN'])
    public = [*checkout(ROOT), *collection(temp / 'edi-data-published')]
    blobs, listed, known = lists(home, sha, public)
    environment = {'CRYSTA_SRC': str(home), **write_lists(blobs, listed, known, temp)}
    prove(home, environment, listed[min(listed)])
    with Path(os.environ['GITHUB_ENV']).open('a', encoding='utf-8') as output:
        output.writelines(f'{name}={value}\n' for name, value in environment.items())
    return len(blobs)


def main() -> int:
    """Prepare the runner; on any failure the source is removed again."""
    temp, sha = Path(os.environ['RUNNER_TEMP']), sys.argv[1]
    try:
        count = prepare(temp, sha)
    except (RefusedError, OSError, KeyError, ValueError) as error:
        shutil.rmtree(temp / 'crysta', ignore_errors=True)
        reason = str(error) if isinstance(error, RefusedError) else type(error).__name__
        print(f'crysta-fetch: REFUSED: {reason}', file=sys.stderr)
        return 1
    print(f'crysta-fetch: {sha}, {count} files listed, the output filter is in place')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
