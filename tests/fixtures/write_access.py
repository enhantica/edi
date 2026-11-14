"""Prove that a cache parent cannot create files or directories on the current host."""

import csv
import os
import shutil
import stat
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def unwritable_directory(directory):
    """Retain read access while denying actual creation, then restore the original permissions."""
    directory = Path(directory)
    mode = stat.S_IMODE(directory.stat().st_mode)
    with tempfile.TemporaryDirectory(dir=directory.parent) as scratch:
        if os.name == 'nt':
            system = Path(os.environ['SYSTEMROOT']) / 'System32'
            user = subprocess.run(
                [str(system / 'whoami.exe'), '/user', '/fo', 'csv', '/nh'],
                capture_output=True,
                text=True,
                check=True,
                timeout=5,
            )
            sid = next(csv.reader(user.stdout.splitlines()))[1]
            if not sid.startswith('S-1-'):
                raise RuntimeError(
                    'The cache permission vehicle requires the actual current user SID'
                )
            icacls = str(system / 'icacls.exe')
            saved = str(Path(scratch) / 'original.acl')

            def acl(*args):
                subprocess.run(
                    [icacls, *args],
                    cwd=directory.parent,
                    check=True,
                    capture_output=True,
                    timeout=5,
                )

            acl(directory.name, '/save', saved)
        try:
            if os.name == 'nt':
                acl(directory.name, '/inheritancelevel:r')
                acl(directory.name, '/grant:r', '*' + sid + ':(RX)')
                acl(directory.name, '/deny', '*' + sid + ':(WD,AD,WA,WEA)')
            else:
                directory.chmod(0o555)
            for kind in ['file', 'directory']:
                try:  # noqa: PLW0717 - an allowed create disproves the permission premise
                    if kind == 'file':
                        descriptor, path = tempfile.mkstemp(dir=directory)
                        os.close(descriptor)
                        Path(path).unlink()
                    else:
                        shutil.rmtree(tempfile.mkdtemp(dir=directory))
                except PermissionError:
                    continue
                raise RuntimeError(
                    'The cache permission vehicle must deny actual ' + kind + ' creation'
                )
            yield
        finally:
            if os.name == 'nt':
                acl('.', '/restore', saved)
            else:
                directory.chmod(mode)
