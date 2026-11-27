# SPDX-License-Identifier: BSD-3-Clause
"""Record each file under $EDI_READ_AUDIT_ROOT this Python process opens or imports.

On PYTHONPATH in crysta's `edi verification` job, whose last step checks the record
(tools/ci/crysta_read_audit.py). Each path goes to $EDI_READ_AUDIT_LOG once per process, relative
to the root; a module loaded from its cached bytecode counts as its source. Without both variables
it does nothing.
"""

import contextlib
import os
import sys
from importlib.util import source_from_cache

# os.path rather than pathlib: this runs on every open, and resolving links would hide a path.


def _install() -> None:
    log, root = os.environ.get('EDI_READ_AUDIT_LOG'), os.environ.get('EDI_READ_AUDIT_ROOT')
    if not log or not root:
        return
    roots = {os.path.abspath(root) + os.sep, os.path.realpath(root) + os.sep}  # noqa: PTH100
    # One unbuffered append a path keeps lines whole across processes and forks.
    descriptor = os.open(log, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
    seen = set()

    def record(opened: object) -> None:
        path = os.path.abspath(os.fsdecode(opened))  # noqa: PTH100
        if path.endswith('.pyc'):
            with contextlib.suppress(ValueError):
                path = source_from_cache(path)
        prefix = next((prefix for prefix in roots if path.startswith(prefix)), None)
        if prefix and path not in seen:
            seen.add(path)
            name = path[len(prefix) :].replace(os.sep, '/')
            os.write(descriptor, f'{name}\n'.encode('utf-8', 'surrogateescape'))

    def hook(event: str, args: tuple) -> None:
        # A hook that raises would fail the open itself.
        if event == 'open' and not isinstance(args[0], int):
            with contextlib.suppress(Exception):
                record(args[0])

    sys.addaudithook(hook)


_install()
