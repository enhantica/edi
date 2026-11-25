# SPDX-License-Identifier: BSD-3-Clause
"""Put crysta's source at one commit on a CI runner and list it for the output checks.

    TOKEN=... python3 tools/ci/crysta_fetch.py SHA [--history] [--receipts FOLDER] [--site FOLDER]

Fetches the commit into $RUNNER_TEMP/crysta, refuses any other, writes the lists source_lists.py
reads, proves the output filter with them and names the checkout and the lists to the later steps.
A job that publishes what another commit of edi made lists every commit edi's history has pinned
(`--history`) and those its receipts were written against (`--receipts`) as well. A site carries
the list of the commits its content was checked against and is published with it (`--site`), so
what it keeps is compared with the source that content was made from. Nothing a child process
prints is passed on: it could be the source.
"""

from __future__ import annotations

import argparse
import base64
import dataclasses
import io
import json
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
SITE_PINS = 'crysta-commits.json'
PIN = re.compile(rb'^CRYSTA_COMMIT *= *"([0-9a-f]{40})"', re.MULTILINE)


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


def fetch(home: Path, sha: str, also: set[str], token: str) -> None:
    """Fetch ``sha`` and check it out, the others beside it; the token stays in this process."""
    shutil.rmtree(home, ignore_errors=True)
    home.mkdir(parents=True)
    git(home, 'init', '-q')
    credential = base64.b64encode(f'x-access-token:{token}'.encode()).decode()
    wanted = [sha, *sorted(also - {sha})]
    git(
        home,
        *('fetch', '-q', '--depth', '1', f'{SERVER}/{REPOSITORY}', *wanted),
        GIT_CONFIG_COUNT='1',
        GIT_CONFIG_KEY_0=f'http.{SERVER}/.extraheader',
        GIT_CONFIG_VALUE_0=f'AUTHORIZATION: basic {credential}',
        GIT_TERMINAL_PROMPT='0',
    )
    git(home, 'checkout', '-q', '--detach', sha)
    if git(home, 'rev-parse', 'HEAD').decode().strip() != sha:
        raise RefusedError('the checkout is another commit')


def history(root: Path) -> set[str]:
    """Every crysta commit edi's history has pinned; a shallow checkout does not know."""
    if git(root, 'rev-parse', '--is-shallow-repository').strip() != b'false':
        raise RefusedError('the checkout has no history')
    found = set()
    for commit in git(root, 'log', '--format=%H', 'HEAD', '--', 'pixi.toml').decode().split():
        if pin := PIN.search(git(root, 'show', f'{commit}:pixi.toml')):
            found.add(pin[1].decode())
    if not found:
        raise RefusedError('the history has no pin')
    return found


def receipted(folder: Path) -> set[str]:
    """The crysta commits these receipts were written against."""
    found = {json.loads(file.read_bytes())['crysta'] for file in folder.rglob('*.json')}
    if not found or not all(
        isinstance(pin, str) and re.fullmatch(r'[0-9a-f]{40}', pin) for pin in found
    ):
        raise RefusedError('a receipt names no commit')
    return found


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


@dataclasses.dataclass
class Lists:
    """What the output checks know, before it is written."""

    blobs: set[str]
    lines: dict[str, bytes]
    public: set[str]
    members: set[str]


def members(home: Path, sha: str, files: dict[str, str]) -> set[str]:
    """What this commit's SDK carries: the commit, a blob or line id, and the member's name."""
    found = set()
    for kind, name, *sources in source_lists.sdk_members():
        if kind == 'header' and name in files and re.fullmatch(r'include/.+\.hpp', name):
            found.add(f'{sha} {files[name]} {name}')
        elif kind == 'configured':
            held = {files[source] for source in sources if source in files}
            lines = set().union(*map(bare, contents(home, held)))
            known = {source_lists.line_id(line) for line in lines} - {None}
            found |= {f'{sha} {entry} {name}' for entry in known}
    # A commit without one is listed all the same.
    return found or {f'{sha} {sha} .'}


def lists(home: Path, pins: set[str], public: list[tuple[Path, str]]) -> Lists:
    """The source of these commits without what edi publishes, and that one's blob ids."""
    blobs, written, carried = set(), set(), set()
    for sha in pins:
        files = tree(home, sha)
        blobs |= set(files.values())
        written |= {blob for path, blob in files.items() if source_lists.written(path)}
        carried |= members(home, sha, files)
    lines = set().union(*map(bare, contents(home, written)))
    known: set[str] = set()
    for where, commit in public:
        shown = set(tree(where, commit).values())
        known |= shown
        for data in opened(contents(where, shown)):
            known.add(source_lists.blob_id(data))
            lines -= bare(data)
    listed = {entry: line for line in lines if (entry := source_lists.line_id(line))}
    if not blobs - known or not listed:
        raise RefusedError('the source lists are empty')
    return Lists(blobs - known, listed, known, carried)


def write_lists(made: Lists, folder: Path) -> dict[str, str]:
    """Write the lists beside the checkout and name them."""
    marks = {source_lists.mark_entry(line) for line in made.lines.values()}
    written = {}
    for variable, entries in (
        (source_lists.BLOBS, made.blobs),
        (source_lists.LINES, made.lines),
        (source_lists.MARKS, marks),
        (source_lists.PUBLIC, made.public),
        (source_lists.MEMBERS, made.members),
    ):
        path = folder / variable.lower().replace('_', '-')
        path.write_text('\n'.join(sorted(entries)) + '\n', encoding='utf-8')
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


def deployed(folder: Path) -> set[str]:
    """The crysta commits the site here was checked against; none before the first such record."""
    record = folder / SITE_PINS
    found = set(json.loads(record.read_bytes())) if record.is_file() else set()
    if not all(isinstance(pin, str) and re.fullmatch(r'[0-9a-f]{40}', pin) for pin in found):
        raise RefusedError('the site names no commit')
    return found


def prepare(temp: Path, args: argparse.Namespace) -> int:
    """Fetch, list and prove; name the checkout and the lists to the later steps."""
    if not re.fullmatch(r'[0-9a-f]{40}', args.sha):
        raise RefusedError('the commit is not a full id')
    pins = {args.sha}
    if args.history:
        pins |= history(ROOT)
    if args.receipts:
        pins |= receipted(args.receipts)
    if args.site:
        pins |= deployed(args.site)
        (args.site / SITE_PINS).write_text(json.dumps(sorted(pins)) + '\n', encoding='utf-8')
    home = temp / 'crysta'
    fetch(home, args.sha, pins, os.environ['TOKEN'])
    made = lists(home, pins, [*checkout(ROOT), *collection(temp / 'edi-data-published')])
    environment = {
        'CRYSTA_SRC': str(home),
        'CRYSTA_LISTED_SHA': args.sha,
        **write_lists(made, temp),
    }
    prove(home, environment, made.lines[min(made.lines)])
    with Path(os.environ['GITHUB_ENV']).open('a', encoding='utf-8') as output:
        output.writelines(f'{name}={value}\n' for name, value in environment.items())
    return len(made.blobs)


def refused(temp: Path, reason: str) -> int:
    """Remove the source and say why, without a word of it."""
    shutil.rmtree(temp / 'crysta', ignore_errors=True)
    print(f'crysta-fetch: REFUSED: {reason}', file=sys.stderr)
    return 1


def main() -> int:
    """Prepare the runner; on any failure the source is removed again."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('sha')
    parser.add_argument('--history', action='store_true')
    parser.add_argument('--receipts', type=Path)
    parser.add_argument('--site', type=Path)
    args = parser.parse_args()
    temp = Path(os.environ['RUNNER_TEMP'])
    try:
        count = prepare(temp, args)
    except RefusedError as error:
        return refused(temp, str(error))
    except (OSError, KeyError, ValueError) as error:
        return refused(temp, type(error).__name__)
    print(f'crysta-fetch: {args.sha}, {count} files listed, the output filter is in place')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
