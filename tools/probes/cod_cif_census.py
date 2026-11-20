"""Resume a headless Edi census against a frozen COD ID and revision catalogue.

The dated COD ZIP is read by byte range. Only one ZIP window and the CIFs
currently being imported need scratch space. Current revisions missing from
the archive are retrieved separately. Use `export` for a CSV of all catalogue
IDs, including pending entries. The database pins the catalogue and both Edi
binaries so that interrupted runs can resume on the same inputs and code.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import http.client
import io
import itertools
import json
import os
import re
import select
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse
import urllib.request
import zipfile
from collections.abc import Iterable, Iterator
from concurrent.futures import Future, ThreadPoolExecutor
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, override

COD = 'https://www.crystallography.net/cod'
ARCHIVE = 'https://www.crystallography.net/archives/2025/data/cod-rev297631-2025.02.07.zip'
ID = re.compile(r'[0-9]{7}')
REVISION = re.compile(rb'(?m)^#\$Revision:\s+([0-9]+)\s+\$')


def _open_https(
    url: str, *, timeout: int, method: str = 'GET', headers: dict[str, str] | None = None
) -> http.client.HTTPResponse:
    if urllib.parse.urlsplit(url).scheme != 'https':
        raise ValueError('COD transfers require HTTPS')
    request = urllib.request.Request(url, method=method, headers=headers or {})  # noqa: S310
    response = urllib.request.urlopen(request, timeout=timeout)  # noqa: S310
    if urllib.parse.urlsplit(response.geturl()).scheme != 'https':
        response.close()
        raise ValueError('The COD transfer redirected outside HTTPS')
    return response


class _RangeZip(io.RawIOBase):
    """Read a stable HTTP ZIP one aligned window at a time."""

    def __init__(self, url: str, window: int) -> None:
        super().__init__()
        self.url = url
        self.window = window
        self.position = 0
        self.cached_start = -1
        self.cached = b''
        with _open_https(url, method='HEAD', timeout=30) as response:
            self.length = int(response.headers['Content-Length'])
            self.etag = response.headers['ETag']
        if not self.etag:
            raise RuntimeError('The archive server returned no version identifier')

    @override
    def seek(self, offset: int, whence: int = os.SEEK_SET) -> int:
        base = {os.SEEK_SET: 0, os.SEEK_CUR: self.position, os.SEEK_END: self.length}[whence]
        position = base + offset
        if position < 0:
            raise OSError('seek before the start of the ZIP')
        self.position = position
        return position

    @override
    def tell(self) -> int:
        return self.position

    @override
    def seekable(self) -> bool:
        return True

    @override
    def readable(self) -> bool:
        return True

    def _fetch(self, start: int) -> bytes:
        end = min(self.length, start + self.window) - 1
        # Keep different byte ranges distinct even through a shared HTTP cache.
        separator = '&' if '?' in self.url else '?'
        url = f'{self.url}{separator}range={start}-{end}'
        for attempt in range(1, 4):
            try:
                return self._read_window(url, start, end)
            except (OSError, http.client.IncompleteRead) as error:
                if attempt == 3:
                    raise
                print(f'Archive byte {start}: retry {attempt} after {error}', flush=True)
                time.sleep(10)
        raise AssertionError('unreachable')

    def _read_window(self, url: str, start: int, end: int) -> bytes:
        headers = {'Range': f'bytes={start}-{end}', 'If-Match': self.etag}
        with _open_https(url, timeout=120, headers=headers) as response:
            expected = f'bytes {start}-{end}/{self.length}'
            if response.status != 206 or response.headers.get('Content-Range') != expected:
                raise RuntimeError(f'Archive range was not served as requested: {expected}')
            if response.headers.get('ETag') != self.etag:
                raise RuntimeError('The bulk archive changed while reading')
            data = response.read()
        if len(data) != end - start + 1:
            raise OSError(f'Truncated archive window at byte {start}')
        return data

    @override
    def read(self, size: int = -1) -> bytes:
        remaining = max(0, self.length - self.position)
        left = remaining if size < 0 else min(size, remaining)
        parts = bytearray()
        while left:
            start = self.position // self.window * self.window
            if start != self.cached_start:
                self.cached = self._fetch(start)
                self.cached_start = start
            offset = self.position - start
            take = min(left, len(self.cached) - offset)
            parts.extend(self.cached[offset : offset + take])
            left -= take
            self.position += take
        return bytes(parts)


@dataclass(frozen=True)
class _Build:
    pythonpath: Path
    extension: Path

    def environment(self) -> dict[str, str]:
        return {
            **os.environ,
            'PYTHONPATH': str(self.pythonpath),
            'EDI_EXTENSION_DIR': str(self.extension),
            'OMP_NUM_THREADS': '1',
            'OPENBLAS_NUM_THREADS': '1',
        }

    def validate(self) -> str:
        process = subprocess.run(
            [sys.executable, '-c', 'import edi; print(edi._edi.__build_commit__)'],
            env=self.environment(),
            timeout=30,
            capture_output=True,
            text=True,
            check=False,
        )
        if process.returncode:
            raise RuntimeError(f'Failed to start Edi at {self.extension}: {process.stderr}')
        return process.stdout.strip()

    def fingerprint(self) -> str:
        (binary,) = self.extension.glob('_edi.*')
        source = hashlib.sha256()
        for path in sorted(self.pythonpath.joinpath('edi').rglob('*.py')):
            source.update(str(path.relative_to(self.pythonpath)).encode())
            source.update(b'\0')
            source.update(path.read_bytes())
        with binary.open('rb') as handle:
            artifact = hashlib.file_digest(handle, 'sha256').hexdigest()
        return f'{source.hexdigest()}:{artifact}'


class _ProbeWorker:
    def __init__(self, build: _Build, seconds: int) -> None:
        self.build = build
        self.seconds = seconds
        self.process: subprocess.Popen[bytes] | None = None

    def close(self) -> None:
        if self.process is not None:
            self.process.kill()
            self.process.wait()
            self.process = None

    def check(self, path: Path) -> tuple[str, str]:
        if self.process is None:
            self.process = subprocess.Popen(
                [sys.executable, str(Path(__file__).with_name('cod_cif_audit.py')), '_serve'],
                env=self.build.environment(),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
            )
        process = self.process
        if process.stdin is None or process.stdout is None:
            raise RuntimeError('Edi worker pipes were not created')
        try:  # noqa: PLW0717
            process.stdin.write(json.dumps(str(path)).encode() + b'\n')
            process.stdin.flush()
            ready, _, _ = select.select([process.stdout], [], [], self.seconds)
            if not ready:
                self.close()
                return 'timed out', f'import exceeded {self.seconds} seconds'
            result = process.stdout.readline()
            if result:
                status, detail = json.loads(result)
                return status, detail
            process.wait(timeout=5)
            report = f'worker exited {process.returncode}'
        except (OSError, ValueError, subprocess.TimeoutExpired) as error:
            report = str(error)
        self.close()
        return 'process failed', report


def _read_revisions(path: Path) -> Iterator[tuple[str, str]]:
    with path.open(encoding='utf-8', newline='') as handle:
        body = itertools.dropwhile(lambda line: line.startswith('#'), handle)
        records = csv.DictReader(body)
        if not {'file', 'svnrevision'} <= set(records.fieldnames or ()):
            raise ValueError('COD revision CSV must have file and svnrevision columns')
        for record in records:
            entry, revision = record['file'], record['svnrevision']
            if not ID.fullmatch(entry) or not (
                revision and revision.isascii() and revision.isdecimal()
            ):
                raise ValueError(f'Invalid COD catalogue record: {entry!r}, revision {revision!r}')
            yield entry, revision


def _initialise(
    connection: sqlite3.Connection, args: argparse.Namespace, builds: tuple[_Build, _Build]
) -> int:
    ids = args.ids.read_text(encoding='ascii').splitlines()
    catalogue = dict(_read_revisions(args.revisions))
    if len(set(ids)) != len(ids) or not ids or not all(ID.fullmatch(entry) for entry in ids):
        raise ValueError('COD ID inventory is empty, malformed, or has duplicates')
    missing = set(ids) - catalogue.keys()
    if missing:
        raise ValueError(
            f'COD revision catalogue lacks {len(missing)} frozen IDs, e.g. {min(missing)}'
        )
    expected = [(entry, catalogue[entry]) for entry in sorted(ids)]
    key = hashlib.sha256(json.dumps(expected).encode()).hexdigest()
    identity = json.dumps((key, args.archive, *(build.fingerprint() for build in builds)))
    connection.executescript("""
        PRAGMA journal_mode = WAL;
        CREATE TABLE IF NOT EXISTS census (identity TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS archive_scan (etag TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS expected (entry_id TEXT PRIMARY KEY, revision TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS results (
            entry_id TEXT PRIMARY KEY,
            revision TEXT NOT NULL,
            sha256 TEXT NOT NULL,
            initial_status TEXT NOT NULL,
            initial_detail TEXT NOT NULL,
            status_after_fix TEXT NOT NULL,
            detail_after_fix TEXT NOT NULL
        );
    """)
    _create_review_tables(connection)
    _protect_audited_inputs(connection)
    with connection:
        current = connection.execute('SELECT identity FROM census').fetchone()
        if current is None:
            connection.execute('INSERT INTO census VALUES (?)', (identity,))
            connection.executemany('INSERT INTO expected VALUES (?, ?)', expected)
        elif current[0] != identity:
            raise ValueError(
                'Census catalogue, archive, or Edi build differs from this checkpoint'
            )
    return len(expected)


def _file_revision(path: Path) -> str:
    with path.open('rb') as handle:
        matched = REVISION.search(handle.read(4096))
    return matched[1].decode('ascii') if matched else ''


class _Audit:
    def __init__(
        self,
        connection: sqlite3.Connection,
        builds: tuple[_Build, _Build],
        spool: Path,
        jobs: int,
        seconds: int,
    ) -> None:
        self.connection = connection
        self.builds = builds
        self.spool = spool
        self.jobs = jobs
        self.seconds = seconds
        self.expected = dict(connection.execute('SELECT entry_id, revision FROM expected'))
        self.withheld = {row[0] for row in connection.execute('SELECT entry_id FROM withheld')}
        self.finished = {
            row[0]
            for row in connection.execute(
                "SELECT entry_id FROM results WHERE initial_status != 'process failed' "
                "AND status_after_fix != 'process failed' AND initial_status != 'timed out' "
                "AND status_after_fix != 'timed out' AND initial_status != 'probe failed' "
                "AND status_after_fix != 'probe failed'"
            )
        }
        self.finished.difference_update(self.withheld)
        self.local = threading.local()
        self.workers: list[_ProbeWorker] = []
        self.executor = ThreadPoolExecutor(max_workers=jobs)
        self.pending: list[Future[tuple[str, ...]]] = []
        self.enqueued: set[str] = set()
        self.archive_mismatches = 0

    def close(self) -> None:
        self.executor.shutdown(wait=True)
        for worker in self.workers:
            worker.close()

    def _import(self, entry: str, revision: str, path: Path) -> tuple[str, ...]:
        pair = getattr(self.local, 'pair', None)
        if pair is None:
            pair = tuple(_ProbeWorker(build, self.seconds) for build in self.builds)
            self.local.pair = pair
            self.workers.extend(pair)
        try:
            with path.open('rb') as handle:
                digest = hashlib.file_digest(handle, 'sha256').hexdigest()
            before, after = (worker.check(path) for worker in pair)
            return entry, revision, digest, before[0], before[1], after[0], after[1]
        finally:
            path.unlink(missing_ok=True)

    def submit(self, entry: str, stream: BinaryIO) -> bool:
        if (
            entry not in self.expected
            or entry in self.withheld
            or entry in self.finished
            or entry in self.enqueued
        ):
            return False
        path = self.spool / f'{entry}.cif'
        with path.open('wb') as target:
            shutil.copyfileobj(stream, target)
        revision = self.expected[entry]
        if _file_revision(path) != revision:
            path.unlink()
            self.archive_mismatches += 1
            return False
        self.enqueued.add(entry)
        self.pending.append(self.executor.submit(self._import, entry, revision, path))
        if len(self.pending) >= self.jobs * 3:
            self.flush()
        return True

    def flush(self) -> None:
        if not self.pending:
            return
        rows = [future.result() for future in self.pending]
        self.pending.clear()
        self.enqueued.clear()
        with self.connection:
            self.connection.executemany(
                'INSERT OR REPLACE INTO results VALUES (?, ?, ?, ?, ?, ?, ?)', rows
            )
        invalid = {'process failed', 'timed out', 'probe failed'}
        previous = len(self.finished)
        self.finished.update(
            row[0] for row in rows if row[3] not in invalid and row[5] not in invalid
        )
        if len(self.finished) // 500 > previous // 500:
            print(
                f'Audited {len(self.finished)}/{len(self.expected)} catalogue entries', flush=True
            )

    def scan_zip(self, archive: zipfile.ZipFile, max_revision: int | None = None) -> None:
        for member in sorted(archive.infolist(), key=lambda info: info.header_offset):
            name = Path(member.filename)
            revision = self.expected.get(name.stem)
            if (
                name.suffix.lower() != '.cif'
                or revision is None
                or name.stem in self.finished
                or name.stem in self.withheld
            ):
                continue
            if max_revision is not None and int(revision) > max_revision:
                continue
            try:
                with archive.open(member) as stream:
                    self.submit(name.stem, stream)
            except zipfile.BadZipFile as error:
                print(f'Invalid archive member for COD {name.stem}: {error}', flush=True)
        self.flush()


def _fill_live(audit: _Audit, directory: Path, entries: set[str], base_url: str) -> None:
    pending = sorted(entries - audit.finished - audit.withheld)
    next_request = time.monotonic()

    def fetch(url: str, target: Path) -> None:
        nonlocal next_request
        time.sleep(max(0.0, next_request - time.monotonic()))
        try:
            with _open_https(url, timeout=90) as response, target.open('wb') as output:
                shutil.copyfileobj(response, output)
        finally:
            next_request = time.monotonic() + 10

    def fetch_group(group: list[str]) -> None:
        params = urllib.parse.urlencode({
            'id': ','.join(group),
            'format': 'zip',
            'include_duplicates': 1,
            'include_errors': 1,
            'include_theoretical': 1,
        })
        bulk = directory / 'live-batch.zip'
        downloaded = False
        try:
            fetch(f'{base_url}/result?{params}', bulk)
            with zipfile.ZipFile(bulk) as archive:
                audit.scan_zip(archive)
            downloaded = True
        except (OSError, http.client.HTTPException, zipfile.BadZipFile) as error:
            print(f'Live ZIP {group[0]} through {group[-1]}: {error}', flush=True)
        finally:
            bulk.unlink(missing_ok=True)
        if not downloaded and len(group) > 5:
            middle = len(group) // 2
            fetch_group(group[:middle])
            fetch_group(group[middle:])
            return

        for entry in group:
            if entry in audit.finished:
                continue
            path = directory / f'{entry}.download'
            try:
                fetch(f'{base_url}/{entry}.cif@{audit.expected[entry]}', path)
                with path.open('rb') as source:
                    if not audit.submit(entry, source):
                        print(f'Unverified CIF revision for COD {entry}', flush=True)
            except (OSError, http.client.HTTPException, zipfile.BadZipFile) as error:
                print(f'Could not retrieve COD {entry}: {error}', flush=True)
            finally:
                path.unlink(missing_ok=True)
        audit.flush()

    for start in range(0, len(pending), 100):
        fetch_group(pending[start : start + 100])


def _run(args: argparse.Namespace) -> int:
    builds = (
        _Build(args.before_lib.resolve(), args.before_extension.resolve()),
        _Build(args.after_lib.resolve(), args.after_extension.resolve()),
    )
    before, after = (build.validate() for build in builds)
    print(f'Edi commits: baseline {before}, candidate {after}', flush=True)
    with closing(sqlite3.connect(args.database, timeout=30)) as db:
        count = _initialise(db, args, builds)
        with tempfile.TemporaryDirectory(prefix='spool-', dir=args.database.parent) as scratch:
            audit = _Audit(db, builds, Path(scratch), args.jobs, args.seconds)
            try:
                print(f'Census opened: {len(audit.finished)}/{count} audited', flush=True)
                if args.local_zip:
                    with zipfile.ZipFile(args.local_zip) as archive:
                        print(
                            f'Opened local archive: {len(archive.infolist())} members', flush=True
                        )
                        audit.scan_zip(archive)
                elif (
                    not args.live_only and not db.execute('SELECT 1 FROM archive_scan').fetchone()
                ):
                    with (
                        _RangeZip(args.archive, args.window_mib * 1024**2) as stream,
                        zipfile.ZipFile(stream) as archive,
                    ):
                        print(
                            f'Opened COD archive {stream.etag}: {len(archive.infolist())} members',
                            flush=True,
                        )
                        named_revision = re.search(r'/cod-rev([0-9]+)-', args.archive)
                        max_revision = int(named_revision[1]) if named_revision else None
                        audit.scan_zip(archive, max_revision)
                    with db:
                        db.execute('INSERT INTO archive_scan VALUES (?)', (stream.etag,))
                    db.execute('PRAGMA wal_checkpoint(TRUNCATE)')
                print(
                    f'Snapshot pass: {len(audit.finished)}/{count}, '
                    f'{audit.archive_mismatches} mismatched revisions',
                    flush=True,
                )
                if args.archive_only:
                    return 0
                entries = set(audit.expected)
                if args.live_ids:
                    entries = set(args.live_ids.read_text(encoding='ascii').splitlines())
                    unknown = entries - audit.expected.keys()
                    if not entries or unknown:
                        raise ValueError('The live ID selection must contain frozen COD IDs only')
                if not args.local_zip:
                    _fill_live(audit, Path(scratch), entries, args.live_base.rstrip('/'))
                if args.live_ids:
                    pending = len(entries - audit.finished - audit.withheld)
                    print(f'Selected live pass: {len(entries)} catalogue IDs, {pending} pending')
                    return 0 if pending == 0 else 1
                pending = count - len(audit.finished) - len(audit.withheld)
                print(
                    f'Census finished: {len(audit.finished)}/{count} audited, '
                    f'{len(audit.withheld)} withheld by COD, {pending} pending',
                    flush=True,
                )
                return 0 if pending == 0 else 1
            finally:
                audit.close()


def _export(database: Path, output: Path) -> None:
    query = """
        SELECT expected.entry_id, expected.revision, coalesce(results.sha256, rechecks.sha256),
               results.initial_status, results.initial_detail,
               coalesce(rechecks.status, results.status_after_fix),
               coalesce(rechecks.detail, results.detail_after_fix), rechecks.edi_commit,
               withheld.release_date
        FROM expected LEFT JOIN results USING (entry_id)
        LEFT JOIN withheld ON withheld.entry_id = expected.entry_id
        LEFT JOIN rechecks ON rechecks.entry_id = expected.entry_id
            AND rechecks.revision = expected.revision
            AND (results.sha256 IS NULL OR rechecks.sha256 = results.sha256)
        ORDER BY expected.entry_id
    """
    with tempfile.TemporaryDirectory(prefix='export-', dir=output.parent) as directory:
        staged = Path(directory) / output.name
        with (
            closing(sqlite3.connect(database, timeout=30)) as db,
            staged.open('w', newline='', encoding='utf-8') as target,
        ):
            _create_review_tables(db)
            writer = csv.writer(target, lineterminator='\n')
            writer.writerow((
                'cod_entry_id',
                'initial_status',
                'status_after_fix',
                'initial_detail',
                'detail_after_fix',
                'source_url',
                'cif_sha256',
                'rechecked_edi_commit',
            ))
            for row in db.execute(query):
                (
                    entry,
                    revision,
                    digest,
                    before,
                    before_detail,
                    after,
                    after_detail,
                    commit,
                    hold,
                ) = row
                if hold:
                    before = after = 'withheld by COD'
                    before_detail = after_detail = f'Frozen COD catalogue release date {hold}'
                    digest = commit = None
                writer.writerow((
                    entry,
                    before or 'pending',
                    after or 'pending',
                    before_detail,
                    after_detail,
                    f'{COD}/{entry}.cif@{revision}',
                    digest,
                    commit,
                ))
        staged.replace(output)


def _create_review_tables(connection: sqlite3.Connection) -> None:
    connection.execute("""
        CREATE TABLE IF NOT EXISTS rechecks (
            entry_id TEXT PRIMARY KEY, revision TEXT NOT NULL, sha256 TEXT NOT NULL,
            status TEXT NOT NULL, detail TEXT NOT NULL, edi_commit TEXT NOT NULL
        )
    """)


def _protect_audited_inputs(connection: sqlite3.Connection) -> None:
    # Two compatible sources can deliver the same revision with different SVN comments.
    # Keep the first completed comparison and its digest so a byte-for-byte replay stays valid.
    connection.execute("""
        CREATE TRIGGER IF NOT EXISTS keep_completed_comparisons
        BEFORE INSERT ON results
        WHEN EXISTS (
            SELECT 1 FROM results
            WHERE entry_id = NEW.entry_id AND revision = NEW.revision
                AND initial_status NOT IN ('process failed', 'timed out', 'probe failed')
                AND status_after_fix NOT IN ('process failed', 'timed out', 'probe failed')
        )
        BEGIN
            SELECT RAISE(IGNORE);
        END
    """)
    connection.execute("""
        CREATE TABLE IF NOT EXISTS withheld (
            entry_id TEXT PRIMARY KEY, release_date TEXT NOT NULL
        )
    """)


def _record_withheld(database: Path, records: Path) -> None:
    rows = [
        (entry, revision, release_date)
        for entry, revision, release_date in csv.reader(
            records.read_text(encoding='utf-8').splitlines(), delimiter='\t'
        )
    ]
    with closing(sqlite3.connect(database, timeout=30)) as db, db:
        _create_review_tables(db)
        for entry, revision, release_date in rows:
            expected = db.execute(
                'SELECT revision FROM expected WHERE entry_id = ?', (entry,)
            ).fetchone()
            if expected != (revision,) or not re.fullmatch(
                r'[0-9]{4}-[0-9]{2}-[0-9]{2}', release_date
            ):
                raise ValueError(
                    f'Withholding record does not match the frozen COD catalogue: {entry}'
                )
            db.execute('INSERT OR REPLACE INTO withheld VALUES (?, ?)', (entry, release_date))
    print(f'Recorded {len(rows)} currently withheld COD IDs')


def _recheck(args: argparse.Namespace) -> int:
    build = _Build(args.after_lib.resolve(), args.after_extension.resolve())
    commit = build.validate()
    worker = _ProbeWorker(build, args.seconds)
    try:
        with closing(sqlite3.connect(args.database, timeout=30)) as db:
            _create_review_tables(db)
            for path in args.cifs:
                entry = path.stem
                expected = db.execute(
                    'SELECT revision FROM expected LEFT JOIN withheld USING (entry_id) '
                    'WHERE expected.entry_id = ? AND withheld.entry_id IS NULL',
                    (entry,),
                ).fetchone()
                revision = _file_revision(path)
                if not expected or revision != expected[0]:
                    raise ValueError(f'{path} does not match the frozen COD revision')
                with path.open('rb') as source:
                    digest = hashlib.file_digest(source, 'sha256').hexdigest()
                original = db.execute(
                    'SELECT sha256 FROM results WHERE entry_id = ?', (entry,)
                ).fetchone()
                if original is not None and original[0] != digest:
                    raise ValueError(f'{path} differs from the CIF bytes used in the census')
                status, detail = worker.check(path.resolve())
                if status in {'process failed', 'timed out', 'probe failed'}:
                    raise RuntimeError(f'Could not recheck {entry}: {status}, {detail}')
                with db:
                    db.execute(
                        'INSERT OR REPLACE INTO rechecks VALUES (?, ?, ?, ?, ?, ?)',
                        (entry, revision, digest, status, detail, commit),
                    )
                print(f'COD {entry}: {status} at {commit}', flush=True)
    finally:
        worker.close()
    return 0


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    run = commands.add_parser('run')
    for flag in (
        'database',
        'ids',
        'revisions',
        'before-lib',
        'before-extension',
        'after-lib',
        'after-extension',
    ):
        run.add_argument(f'--{flag}', type=Path, required=True)
    run.add_argument('--archive', default=ARCHIVE)
    run.add_argument('--jobs', type=int, default=8)
    run.add_argument('--seconds', type=int, default=60)
    run.add_argument('--window-mib', type=int, default=32)
    source = run.add_mutually_exclusive_group()
    source.add_argument('--local-zip', type=Path)
    source.add_argument('--live-only', action='store_true')
    source.add_argument('--archive-only', action='store_true')
    run.add_argument('--live-ids', type=Path, help='limit --live-only to these frozen COD IDs')
    run.add_argument('--live-base', default=COD, help='HTTPS base URL of the COD API or a mirror')
    export = commands.add_parser('export')
    export.add_argument('database', type=Path)
    export.add_argument('output', type=Path)
    recheck = commands.add_parser('recheck')
    for flag in ('database', 'after-lib', 'after-extension'):
        recheck.add_argument(f'--{flag}', required=True, type=Path)
    recheck.add_argument('--seconds', type=int, default=60)
    recheck.add_argument('cifs', nargs='+', type=Path)
    withheld = commands.add_parser('record-withheld')
    withheld.add_argument('database', type=Path)
    withheld.add_argument('records', type=Path)
    args = parser.parse_args(argv)
    if args.command == 'run':
        if min(args.jobs, args.seconds, args.window_mib) < 1:
            parser.error('jobs, seconds and window-mib must be positive')
        if args.live_ids and not args.live_only:
            parser.error('--live-ids requires --live-only')
        return _run(args)
    if args.command == 'recheck':
        if args.seconds < 1:
            parser.error('seconds must be positive')
        return _recheck(args)
    if args.command == 'record-withheld':
        _record_withheld(args.database, args.records)
        return 0
    _export(args.database, args.output)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
