# SPDX-License-Identifier: BSD-3-Clause
"""EasyDiffraction's data collection: structures, experiments, measured data and projects.

A collection is plain files behind one base URL or folder with an ``index.json`` at its root
(ADR-0068). The index is read by the core's parser, the same one the app's Load from web popup
uses, so every interface finds the same entry by id.
"""

from __future__ import annotations

import hashlib
import os as _os
import urllib.request as _request
from pathlib import Path as _Path

from edi._edi import _collection_entries, _collection_find, _collection_search

DEFAULT_SOURCE = 'https://raw.githubusercontent.com/enhantica/edi-data/main'
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

    def __init__(self, source: str, text: str) -> None:
        self._source = source
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
        data = _read(_join(self._source, file['path']))
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
        source = _os.environ.get('EDI_COLLECTION') or DEFAULT_SOURCE
    source = str(source)
    if source.lstrip().startswith('{'):
        return Collection('', source)
    return Collection(source, _read(_join(source, 'index.json')).decode('utf-8'))


__all__ = ['Collection', 'load_collection']
