# SPDX-License-Identifier: BSD-3-Clause
"""Put crysta's source at one commit on a CI runner and list it for the output checks.

    TOKEN=... python3 tools/ci/crysta_fetch.py SHA

Fetches the commit into $RUNNER_TEMP/crysta, refuses any other, writes the lists source_lists.py
reads, proves the output filter with them and names the checkout and the lists to the later steps.
Nothing a child process prints is passed on: it could be the source.
"""

from __future__ import annotations

import base64
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import source_lists

ROOT = Path(__file__).resolve().parents[2]
SERVER = os.environ.get('GITHUB_SERVER_URL', 'https://github.com')
REPOSITORY = 'enhantica/crysta'
# What the published SDK carries of the source as it is (its public headers and interface record).
PUBLIC = ('include/', 'data/python-surface.json', 'cmake/crystaConfig.cmake.in')


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


def source(home: Path, sha: str) -> tuple[dict[str, bytes], set[bytes]]:
    """Each source file's bytes by its blob id, and the lines of what the SDK publishes."""
    listed = git(home, 'ls-tree', '-r', '-z', sha).decode('utf-8', 'surrogateescape').split('\0')
    wanted, public = set(), set()
    for entry in filter(None, listed):
        head, path = entry.split('\t', 1)
        _, kind, blob = head.split()
        if kind == 'blob':
            (public if path.startswith(PUBLIC) else wanted).add(blob)
    out = git(home, 'cat-file', '--batch', stdin='\n'.join(sorted(wanted | public)).encode())
    contents, at = {}, 0
    while at < len(out):
        end = out.index(b'\n', at)
        blob, _, size = out[at:end].split()
        contents[blob.decode()] = out[end + 1 : end + 1 + int(size)]
        at = end + 2 + int(size)
    shown = set().union(*(lines_of(contents[blob]) for blob in public))
    return {blob: data for blob, data in contents.items() if blob not in public}, shown


def own() -> Iterator[bytes]:
    """Every file edi tracks, which is public."""
    for name in git(ROOT, 'ls-files', '-z').decode('utf-8', 'surrogateescape').split('\0'):
        path = ROOT / name
        if name and path.is_file():
            yield path.read_bytes()


def lines_of(data: bytes) -> set[bytes]:
    """A text file's lines, bare."""
    return set() if b'\0' in data[:8192] else {line.strip() for line in data.splitlines()}


def write_lists(
    contents: dict[str, bytes], shown: set[bytes], home: Path
) -> tuple[Path, Path, bytes]:
    """Write both lists beside the checkout; one listed line comes back for the proof."""
    blobs, lines = set(contents), set().union(*map(lines_of, contents.values())) - shown
    for data in own():
        blobs.discard(source_lists.blob_id(data))
        lines -= lines_of(data)
    listed = {known: line for line in lines if (known := source_lists.line_id(line))}
    if not blobs or not listed:
        raise RefusedError('the source lists are empty')
    blob_list, line_list = home.parent / 'crysta-source-blobs', home.parent / 'crysta-source-lines'
    blob_list.write_text('\n'.join(sorted(blobs)) + '\n', encoding='ascii')
    line_list.write_text('\n'.join(sorted(listed)) + '\n', encoding='ascii')
    return blob_list, line_list, listed[min(listed)]


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


def prepare(temp: Path, sha: str) -> int:
    """Fetch, list and prove; name the checkout and the lists to the later steps."""
    if not re.fullmatch(r'[0-9a-f]{40}', sha):
        raise RefusedError('the commit is not a full id')
    home = temp / 'crysta'
    fetch(home, sha, os.environ['TOKEN'])
    contents, shown = source(home, sha)
    blob_list, line_list, sample = write_lists(contents, shown, home)
    environment = {
        'CRYSTA_SRC': str(home),
        source_lists.BLOBS: str(blob_list),
        source_lists.LINES: str(line_list),
    }
    prove(home, environment, sample)
    with Path(os.environ['GITHUB_ENV']).open('a', encoding='utf-8') as output:
        output.writelines(f'{name}={value}\n' for name, value in environment.items())
    return len(contents)


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
