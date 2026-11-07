# SPDX-License-Identifier: BSD-3-Clause
"""EasyDiffraction's data collection: structures, experiments, measured data and projects.

A collection is plain files behind one base URL or folder with an ``index.json`` at its root
(ADR-0068). The index is read by the core's parser, the same one the app's Load from web popup
uses, so every interface finds the same entry by id.
"""

from __future__ import annotations

import hashlib
import os as _os
import urllib.error as _error
import urllib.request as _request
from pathlib import Path as _Path

from edi._edi import _collection_entries, _collection_find, _collection_search

# EasyDiffraction's collection: one source, two locations in order; a request uses the first and
# falls back to the next only when it cannot be reached (ADR-0068).
DEFAULT_SOURCES = (
    'https://raw.githubusercontent.com/enhantica/edi-data/main',
    'https://data.easydiffraction.org',
)
DEFAULT_SOURCE = DEFAULT_SOURCES[0]
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


def _read(url: str) -> bytes:
    if url.startswith(('http://', 'https://')):
        with _request.urlopen(url, timeout=30) as answer:  # noqa: S310 - http(s) only
            return answer.read()
    return _Path(url.removeprefix('file://')).read_bytes()


def _unavailable(problem: BaseException) -> bool:
    """Whether a read failed because the location could not be reached, not because it answered.

    A server error (5xx), a transport failure or a missing local folder is an outage; a 404 or a
    refusal is an answer, and the next location is not tried for it.
    """
    if isinstance(problem, _error.HTTPError):
        return problem.code >= 500
    return isinstance(problem, (_error.URLError, TimeoutError, FileNotFoundError, ConnectionError))


def _read_from(sources: tuple[str, ...] | list[str], path: str) -> tuple[bytes, str]:
    """The file at ``path`` from the first location that serves it, with that location.

    The next location is tried only when the one before was unavailable; the last failure is
    raised.
    """
    failure: BaseException | None = None
    for source in sources:
        try:
            return _read(_join(source, path)), source
        except Exception as problem:
            failure = problem
            if not _unavailable(problem):
                raise
    if failure is None:
        raise ValueError('no location to read from')
    raise failure


def _join(base: str, path: str) -> str:
    if base.startswith(('http://', 'https://', 'file://')):
        return base.rstrip('/') + '/' + path
    return str(_Path(base) / path)


class Collection:
    """The entries of one collection, read from its ``index.json``.

    ``source`` is the folder or base URL the index came from. ``entries`` lists every entry as a
    dict with ``id``, ``kind`` (``structure``, ``experiment``, ``data`` or ``project``), ``name``,
    ``description``, ``formula``, ``elements``, ``space_group``, ``cell``, ``radiation``,
    ``technique``, ``instrument``, ``facility``, ``source`` and ``files`` (each with ``path``,
    ``format``, ``sha256`` and ``bytes``).
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

    def fetch(self, entry_id: str, into: str | _os.PathLike) -> _Path:
        """Copy or download the entry's first file into the folder ``into``.

        Returns the written path; the size and sha256 the index records are checked.
        """
        entry = self.find(entry_id)
        if entry is None:
            raise ValueError(f'no entry {entry_id!r} in {self._source}')
        file = entry['files'][0]
        data, _ = _read_from(self._sources or ('',), file['path'])
        if file.get('bytes') is not None and len(data) != file['bytes']:
            raise ValueError(
                f'{file["path"]} has {len(data)} bytes, not the {file["bytes"]} the index records'
            )
        if file.get('sha256') and hashlib.sha256(data).hexdigest() != file['sha256'].lower():
            raise ValueError(f'{file["path"]} does not match its recorded sha256')
        target = _Path(into) / _Path(file['path']).name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return target


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
    text, served = _read_from(sources, 'index.json')
    # The location that answered first stays first for the files, the others remain its fallbacks.
    ordered = (served, *(s for s in sources if s != served))
    return Collection(ordered, text.decode('utf-8'))


__all__ = ['Collection', 'load_collection']
