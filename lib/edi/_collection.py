# SPDX-License-Identifier: BSD-3-Clause
"""EasyDiffraction's data collection and tutorials: list them and download what you name.

A collection is plain files behind one base URL or folder with an ``index.json`` at its root
(ADR-0068). The core reads the index, resolves names and listing numbers, falls back between
locations, checks every file's size and digest, and decides where it goes and how a project
archive is unpacked (ADR-0075). This module only reads URLs and prints.
"""

from __future__ import annotations

import os as _os
import urllib.error as _error
import urllib.request as _request
from pathlib import Path as _Path

from edi._edi import (
    _collection_entries,
    _collection_find,
    _collection_listing,
    _collection_read,
    _collection_read_path,
    _collection_resolve,
    _collection_search,
    _collection_store,
    _collection_stored,
)

# EasyDiffraction's collection: one source, two locations in order; a request uses the first and
# falls back to the next only when it cannot be reached (ADR-0068).
DEFAULT_SOURCES = (
    'https://raw.githubusercontent.com/enhantica/edi-data/main',
    'https://data.easydiffraction.org',
)
DEFAULT_SOURCE = DEFAULT_SOURCES[0]
# The tutorials the documentation publishes, indexed beside its notebooks (ADR-0075).
DEFAULT_TUTORIALS = 'https://enhantica.github.io/edi/tutorials'
_FIELDS = frozenset({
    'id',
    'name',
    'formula',
    'elements',
    'space_group',
    'radiation',
    'technique',
    'instrument',
})


def _transport(url: str) -> tuple[bytes | None, str, bool]:
    """Read one URL or file for the core: its bytes, or why not and whether it was an outage.

    A server error (5xx), a transport failure or a missing local folder is an outage, after which
    the core tries the next location; a 404 or a refusal is an answer.
    """
    try:
        if url.startswith(('http://', 'https://')):
            with _request.urlopen(url, timeout=30) as answer:  # noqa: S310 - http(s) only
                return answer.read(), '', False
        return _Path(url.removeprefix('file://')).read_bytes(), '', False
    except _error.HTTPError as problem:
        return None, f'{url} answered {problem.code}', problem.code >= 500
    except (_error.URLError, TimeoutError, ConnectionError, FileNotFoundError) as problem:
        return None, f'{url}: {problem}', True
    except OSError as problem:
        return None, f'{url}: {problem}', False


def _reached(call: object, *args: object, **kwargs: object) -> object:
    """Run a core read, turning 'no location could be reached' into ConnectionError."""
    try:
        return call(*args, **kwargs)
    except RuntimeError as problem:
        raise ConnectionError(str(problem)) from None


class Collection:
    """The entries of one collection, read from its ``index.json``.

    ``source`` is the folder or base URL the index came from. ``entries`` lists every entry as a
    dict with ``id``, ``kind`` (``structure``, ``experiment``, ``data`` or ``project``, or
    ``tutorial`` in the tutorials index), ``name``, ``description``, ``formula``, ``elements``,
    ``space_group``, ``cell``, ``radiation``, ``technique``, ``instrument``, ``facility``,
    ``source`` and ``files`` (each with ``path``, ``format``, ``sha256`` and ``bytes``).
    """

    def __init__(self, source: str | tuple[str, ...] | list[str], text: str) -> None:
        # One source may have several locations, tried in order when one cannot be reached.
        self._sources = (source,) if isinstance(source, str) else tuple(source)
        self._source = self._sources[0] if self._sources else ''
        self._text = text
        self._entries = _collection_entries(text)

    @property
    def source(self) -> str:
        return self._source

    @property
    def entries(self) -> list[dict]:
        return list(self._entries)

    def find(self, entry_id: str) -> dict | None:
        """The entry with ``entry_id``, or None."""
        return _collection_find(self._text, entry_id)

    def search(self, kind: str, **fields: str) -> list[dict]:
        """The entries of ``kind`` matching the fields.

        The fields are ``id``, ``name``, ``formula``, ``elements``, ``space_group``,
        ``radiation``, ``technique`` and ``instrument``; an empty field does not filter.
        """
        unknown = set(fields) - _FIELDS
        if unknown:
            raise ValueError(f'unknown search fields: {sorted(unknown)}')
        return _collection_search(self._text, kind, {k: str(v) for k, v in fields.items()})

    def listing(self, kind: str = '') -> list[dict]:
        """The entries a listing shows, in its numbered order (from 1)."""
        return _collection_listing(self._text, kind)

    def resolve(self, name: int | str, kind: str = '') -> dict:
        """The entry an id or a listing number names; a number is for interactive use only."""
        return _collection_resolve(self._text, str(name), kind)

    def fetch(self, entry_id: str, into: str | _os.PathLike) -> _Path:
        """Copy or download the entry's first file into the folder ``into``.

        Returns the written path; the size and sha256 the index records are checked.
        """
        if self.find(entry_id) is None:
            raise ValueError(f'no entry {entry_id!r} in {self._source}')
        data, _ = _reached(
            _collection_read, self._sources or ('',), self._text, entry_id, _transport
        )
        target = _Path(into) / _Path(self.find(entry_id)['files'][0]['path']).name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return target

    def download(
        self,
        name: int | str,
        destination: str | _os.PathLike,
        *,
        kind: str = '',
        file_format: str = '',
        overwrite: bool = False,
    ) -> str:
        """Download the entry an id or listing number names into ``destination``.

        A project archive is unpacked into its own folder, whose path is returned; any other file
        is returned as written. A file already there that matches the index is kept unless
        ``overwrite``.
        """
        entry = self.resolve(name, kind)
        folder = str(destination)
        if not overwrite:
            kept = _collection_stored(self._text, entry['id'], folder, file_format)
            if kept is not None:
                return kept
        data, _ = _reached(
            _collection_read, self._sources, self._text, entry['id'], _transport, file_format
        )
        return _collection_store(self._text, entry['id'], folder, data, overwrite, file_format)


def load_collection(source: str | _os.PathLike | None = None) -> Collection:
    """Read a collection's ``index.json`` from a folder, a base URL or the text of an index.

    Without ``source`` the ``EDI_COLLECTION`` environment variable, else EasyDiffraction's
    collection on GitHub, is read.
    """
    if source is None:
        given = _os.environ.get('EDI_COLLECTION')
        sources: tuple[str, ...] = (given,) if given else DEFAULT_SOURCES
    else:
        sources = (str(source),)
    if len(sources) == 1 and sources[0].lstrip().startswith('{'):
        return Collection('', sources[0])
    text, served = _reached(_collection_read_path, list(sources), 'index.json', _transport)
    # The location that answered first stays first for the files, the others remain its fallbacks.
    ordered = (served, *(s for s in sources if s != served))
    return Collection(ordered, text.decode('utf-8'))


def _tutorials(source: str | _os.PathLike | None) -> Collection:
    given = source if source is not None else _os.environ.get('EDI_TUTORIALS', DEFAULT_TUTORIALS)
    return load_collection(given)


def _table(rows: list[tuple[str, ...]], header: tuple[str, ...]) -> None:
    widths = [max(len(header[i]), *(len(row[i]) for row in rows)) for i in range(len(header))]
    for row in (header, *rows):
        print(
            '  '.join(cell.ljust(width) for cell, width in zip(row, widths, strict=True)).rstrip()
        )


def list_data(kind: str = '', *, source: str | _os.PathLike | None = None) -> None:
    """Print the collection's entries, numbered, with their kind, format and name.

    ``kind`` keeps one kind: ``structure``, ``experiment``, ``data`` or ``project``.
    """
    entries = load_collection(source).listing(kind)
    rows = [
        (str(n), e['id'], e['kind'], e['files'][0]['format'], e['name'] or e['description'])
        for n, e in enumerate(entries, 1)
    ]
    _table(rows, ('#', 'id', 'kind', 'format', 'name'))


def download_data(
    name: int | str,
    destination: str | _os.PathLike = 'data',
    *,
    overwrite: bool = False,
    source: str | _os.PathLike | None = None,
) -> str:
    """Download a collection entry by its id, or by its number in ``list_data()``.

    Returns the downloaded file, or for a project archive the folder it was unpacked into. Use the
    id in saved code; a number is the row of a listing. The size and SHA-256 the index records
    are checked, and the mirror is used when GitHub cannot be reached.
    """
    path = load_collection(source).download(name, destination, overwrite=overwrite)
    print(f'Data {name!r} is at {path}')
    return path


def list_tutorials(*, source: str | _os.PathLike | None = None) -> None:
    """Print the published tutorials, numbered, with their titles."""
    entries = _tutorials(source).listing('tutorial')
    _table([(str(n), e['id'], e['name']) for n, e in enumerate(entries, 1)], ('#', 'id', 'title'))


def download_tutorial(
    name: int | str,
    destination: str | _os.PathLike = 'tutorials',
    *,
    file_format: str = 'ipynb',
    overwrite: bool = False,
    source: str | _os.PathLike | None = None,
) -> str:
    """Download a tutorial by id or by its number in ``list_tutorials()``, as ``ipynb`` or ``py``.

    Returns the downloaded file. Run its first cell to get the tutorial's data.
    """
    if file_format not in {'ipynb', 'py'}:
        raise ValueError(f"file_format must be 'ipynb' or 'py', not {file_format!r}")
    path = _tutorials(source).download(
        name, destination, kind='tutorial', file_format=file_format, overwrite=overwrite
    )
    print(f'Tutorial {name!r} is at {path}')
    return path


def download_all_tutorials(
    destination: str | _os.PathLike = 'tutorials',
    *,
    file_format: str = 'ipynb',
    overwrite: bool = False,
    source: str | _os.PathLike | None = None,
) -> list[str]:
    """Download every published tutorial; returns the files in listing order."""
    tutorials = _tutorials(source)
    return [
        tutorials.download(
            entry['id'], destination, kind='tutorial', file_format=file_format, overwrite=overwrite
        )
        for entry in tutorials.listing('tutorial')
    ]


__all__ = [
    'Collection',
    'download_all_tutorials',
    'download_data',
    'download_tutorial',
    'list_data',
    'list_tutorials',
    'load_collection',
]
