"""Observe filesystem permissions and test-library loading without importing the app."""

import errno
import json
import os
import platform
import shutil
import stat
import subprocess
import sys
import tempfile
from functools import partial
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def emit(mechanism, **values):
    print(json.dumps({'mechanism': mechanism, **values}), flush=True)


def attempt(action):
    try:
        action()
    except OSError as error:
        return errno.errorcode.get(error.errno, str(error.errno))
    else:
        return 'success'


def filesystem(root):
    directory = root / 'permissions'
    directory.mkdir()
    for alias in ('hard', 'symbolic'):
        outside = root / ('outside-' + alias)
        outside.write_bytes(b'outside')
        retained = directory / alias
        if alias == 'hard':
            os.link(outside, retained)
        else:
            retained.symlink_to(outside)
        directory.chmod(0o555)
        try:
            emit(
                'directory-0555-' + alias,
                writable=os.access(directory, os.W_OK),
                outside_writable=os.access(outside, os.W_OK),
                unlink=attempt(retained.unlink),
                expected='EACCES for an unprivileged user without a granting ACL',
            )
        finally:
            directory.chmod(0o755)
        retained.unlink(missing_ok=True)
        if alias == 'hard':
            os.link(outside, retained)
        else:
            retained.symlink_to(outside)
        source = directory / 'replacement'
        source.write_bytes(b'replacement')
        emit(
            'replace-' + alias,
            rename=attempt(partial(source.replace, retained)),
            outside_preserved=outside.read_bytes() == b'outside',
            expected='success; outside bytes retained on both platforms',
        )
    source, target = directory / 'source', directory / 'target'
    source.write_bytes(b'new')
    target.write_bytes(b'old')
    source.chmod(0o644)
    directory.chmod(0o555)
    try:
        emit(
            'rename-in-0555',
            rename=attempt(partial(source.replace, target)),
            expected='EACCES for an unprivileged user without a granting ACL',
        )
    finally:
        directory.chmod(0o755)
    target.chmod(0o444)
    with target.open('rb') as opened:
        emit(
            'replace-open-readonly-file',
            rename=attempt(partial(source.replace, target)),
            open_inode_bytes=opened.read().decode(),
            expected='success; open descriptor still reads old on both platforms',
        )
    source.write_bytes(b'new')
    busy = directory / 'nonempty'
    busy.mkdir()
    (busy / 'child').touch()
    emit(
        'replace-file-with-directory',
        rename=attempt(partial(source.replace, busy)),
        expected='EISDIR on both platforms; an open regular file is not this condition',
    )
    if not hasattr(os, 'chflags'):
        emit('uchg', available=False, expected='not a Linux os.chflags mechanism')
        return
    target.write_bytes(b'old')
    try:
        os.chflags(target, stat.UF_IMMUTABLE)
        emit(
            'uchg',
            available=True,
            unlink=attempt(target.unlink),
            rename=attempt(partial(source.replace, target)),
            expected='EPERM on macOS; user immutable is distinct from directory mode',
        )
    finally:
        os.chflags(target, 0)


def command(arguments, *, allow_failure=False, **kwargs):
    result = subprocess.run(
        list(map(str, arguments)),
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
        **kwargs,
    )
    if result.returncode and not allow_failure:
        raise RuntimeError(f'{arguments}: {result.returncode}\n{result.stdout}{result.stderr}')
    return result


def injections(root):
    compiler = shutil.which('cc')
    if not compiler:
        raise RuntimeError('A native C compiler is required for loader observations')
    caller = root / 'platform-call'
    command([compiler, '-O0', HERE / 'platform_call.c', '-o', caller])
    libraries = {}
    for name, source in {
        'temporary': ROOT / 'tests/fixtures/report_storage/temporary_failure.c',
        'publication': ROOT / 'tests/fixtures/report_publication/faults.c',
        'scan': HERE / 'scan_faults.c',
        'staging': HERE / 'staging_faults.c',
    }.items():
        library = root / (name + ('.dylib' if sys.platform == 'darwin' else '.so'))
        command([
            compiler,
            '-shared',
            '-fPIC',
            source,
            HERE / 'platform_loaded.c',
            '-o',
            library,
            *([] if sys.platform == 'darwin' else ['-ldl']),
        ])
        libraries[name] = library
    cases = [
        ('temporary', 'rename', ''),
        ('publication', 'rename', 'settings'),
        ('publication', 'write', 'html'),
        ('publication', 'writev', 'html'),
        ('publication', 'write', 'settings-write'),
        ('publication', 'close', 'settings-close'),
        ('publication', 'fclose', 'settings-close'),
        ('scan', 'rename', ''),
        ('scan', 'unlink', ''),
        ('scan', 'remove', ''),
        ('scan', 'read', ''),
        ('scan', 'fread', ''),
        ('staging', 'link', ''),
    ]
    if sys.platform == 'darwin':
        cases.extend(
            ('temporary', operation, '')
            for operation in ('renameat', 'renamex_np', 'renameatx_np')
        )
    modes = ['baseline', 'insert', *(['flat'] if sys.platform == 'darwin' else [])]
    for library, operation, kind in cases:
        for mode in modes:
            directory = root / f'{library}-{operation}-{kind}-{mode}'
            directory.mkdir()
            source = directory / ('report.edi.tmp' if kind.startswith('settings-') else 'source')
            target = directory / ('report.edi' if kind == 'settings' else 'target')
            source.write_bytes(b'native source bytes\n')
            receipt = root / (directory.name + '.receipt')
            load_stamp = root / (directory.name + '.loaded')
            sentinel = directory / 'sentinel'
            sentinel.write_bytes(b'outside bytes')
            environment = {
                k: v for k, v in os.environ.items() if not k.startswith(('DYLD_', 'LD_PRELOAD'))
            }
            environment.update(
                OUTPUT_PROBE_LOADED=str(load_stamp),
                TEMPORARY_FAILURE_TARGET=str(target),
                TEMPORARY_FAILURE_RECEIPT=str(receipt),
                EDI_REPORT_FAULT_DIR=str(directory),
                EDI_REPORT_FAULT_KIND=kind,
                EDI_REPORT_FAULT_LOG=str(receipt),
                SCAN_FAULT_RENAME_PATH=str(target),
                SCAN_FAULT_REMOVE_PATH=str(source),
                SCAN_FAULT_READ_PATH=str(source),
                SCAN_FAULT_RECEIPT=str(receipt),
                STAGING_LINK_SOURCE=str(source),
                STAGING_LINK_SENTINEL=str(sentinel),
                STAGING_LINK_ALIAS='hard',
                STAGING_LINK_RECEIPT=str(receipt),
            )
            if mode != 'baseline':
                environment[
                    'DYLD_INSERT_LIBRARIES' if sys.platform == 'darwin' else 'LD_PRELOAD'
                ] = str(libraries[library])
            if mode == 'flat':
                environment['DYLD_FORCE_FLAT_NAMESPACE'] = '1'
            try:
                result = command(
                    [caller, operation, source, target], allow_failure=True, env=environment
                )
                emit(
                    f'{library}-{operation}-{kind}',
                    mode=mode,
                    observation=result.stdout.strip(),
                    returncode=result.returncode,
                    stderr=result.stderr,
                    library_loaded=load_stamp.exists(),
                    receipt=receipt.read_text() if receipt.exists() else None,
                    expected=(
                        'baseline succeeds; Linux preload and macOS interposition reach fault'
                    ),
                )
            finally:
                directory.chmod(0o755)


def main():
    emit('host', system=platform.platform(), uid=os.geteuid(), python=sys.executable)
    if os.geteuid() == 0:
        raise RuntimeError('Run as the ordinary runner user; root bypasses mode permissions')
    with tempfile.TemporaryDirectory(prefix='output-platform-') as temporary:
        root = Path(temporary).resolve()
        filesystem(root)
        injections(root)


if __name__ == '__main__':
    main()
