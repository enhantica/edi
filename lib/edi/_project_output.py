# SPDX-License-Identifier: BSD-3-Clause
"""Project output (edi ADR-0039): every file edi's Python writes under a project folder.

The rules are the engine's for project output, which the native writers keep too: a folder written
into is the project's own (a link on the way to it is first replaced by a folder linking each entry
of the folder it named); a temporary file is created new and exclusively, never through what stood
at its name; a file is replaced by renaming its complete temporary over it, which replaces a link
there rather than following it.
"""

from __future__ import annotations

import os
from pathlib import Path


def _within(inner: Path, outer: Path) -> bool:
    try:
        inner.relative_to(outer)
    except ValueError:
        return False
    return inner != outer


def own_folder(folder: Path, root: Path) -> None:
    """Make ``folder``, inside ``root``, the project's own, creating it when missing.

    Every link from ``root`` down to it is replaced by a folder linking each entry of the folder
    it named, relatively when that folder is inside ``root``. Raises OSError when a step is not a
    folder.
    """
    step = root
    for part in folder.relative_to(root).parts:
        step /= part
        if step.is_symlink():
            target = step.resolve()
            entries = sorted(target.iterdir()) if target.is_dir() else []
            step.unlink()
            step.mkdir()
            inside = _within(target, root.resolve())
            for entry in entries:
                link = os.path.relpath(entry, step.resolve()) if inside else entry
                (step / entry.name).symlink_to(link, target_is_directory=entry.is_dir())
        elif not step.exists():
            step.mkdir()
        elif not step.is_dir():
            raise NotADirectoryError(f'cannot write into {step}: it is not a folder')


def _through_link(folder: Path, root: Path) -> bool:
    step = root
    for part in folder.relative_to(root).parts:
        step /= part
        if step.is_symlink():
            return True
        if not step.exists():
            return False
    return False


def write_new(path: Path, text: str) -> None:
    """Write ``text`` to a new file at ``path``.

    Whatever stands at the name is removed first, never written through.
    """
    path.unlink(missing_ok=True)
    with path.open('x', encoding='utf-8') as out:
        out.write(text)


def write_project_file(root: Path, path: Path, text: str) -> None:
    """Replace ``path``, inside the project folder ``root``, with ``text`` whole.

    The text is written first as a new temporary beside the file or, when a folder on the way is
    a link, in ``root``, so a failed write leaves the project and whatever a link names as they
    were; then the file's folder is made the project's own and the temporary renamed over the
    file.
    """
    root, path = Path(root), Path(path)
    linked = _through_link(path.parent, root)
    temporary = root / f'.{path.name}.tmp' if linked else path.with_name(f'{path.name}.tmp')
    if not linked:
        own_folder(path.parent, root)
    try:
        write_new(temporary, text)
        own_folder(path.parent, root)
        temporary.replace(path)
    except BaseException:
        if not temporary.is_dir():
            temporary.unlink(missing_ok=True)
        raise
