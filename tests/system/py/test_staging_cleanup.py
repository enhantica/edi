"A failed staging cleanup cannot overwrite an outside inode or the prior project."

import importlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tests.fixtures import phase_scan
from tests.fixtures.constraint_expressions.project import materialize

ROOT = Path(__file__).resolve().parents[3]
ENGINE = 'edi'
pytestmark = pytest.mark.skipif(os.name == 'nt', reason='POSIX directory permission witness')


def inventory(root):
    return {
        str(path.relative_to(root)): ('link', str(path.readlink()))
        if path.is_symlink()
        else ('bytes', path.read_bytes())
        for path in root.rglob('*')
        if path.is_file() or path.is_symlink()
    }


def unlock(*roots):
    for root in roots:
        for path in [root, *root.rglob('*')]:
            if path.is_dir() and not path.is_symlink():
                path.chmod(0o755)


@pytest.fixture(scope='module')
def native_save(tmp_path_factory):
    root = tmp_path_factory.mktemp('staging-native')
    binary = root / 'save'
    environment = Path(sys.executable).resolve().parent.parent
    compiler = shutil.which('clang++')
    assert compiler, 'The staging witness requires the pinned native compiler'
    if ENGINE == 'crysta':
        producer_command = importlib.import_module(
            'tests.system.py.c34_t26_native_support'
        ).producer_command

        flags, library = producer_command()
        flags[0] = compiler
        flags = [flag for flag in flags if flag != '-fopenmp' and not flag.startswith('-W')]
        libraries = [str(library)]
    else:
        wiring = importlib.import_module('tests.conftest')
        crysta_reference_prefix = wiring.crysta_reference_prefix
        crysta_reference_source = wiring.crysta_reference_source

        prefix, source = crysta_reference_prefix(), crysta_reference_source()
        artifact = Path(sys.modules['edi._edi'].__file__).resolve().parents[2]
        flags = [
            compiler,
            '-std=c++20',
            '-DEDI_OBSERVER',
            '-I' + str(prefix / 'include'),
            '-I' + str(source / 'src'),
            '-I' + str(ROOT / 'core/include'),
            '-I' + str(environment / 'include/eigen3'),
        ]
        libraries = [str(artifact / 'core/libedi_core.a'), str(prefix / 'lib/libcrysta_core.a')]
    result = subprocess.run(
        [
            *flags,
            '-O0',
            '-pthread',
            '-fdelayed-template-parsing',
            *(['-fuse-ld=gold'] if sys.platform == 'linux' and shutil.which('ld.gold') else []),
            str(ROOT / 'tests/fixtures/project_output/staging_probe.cpp'),
            *libraries,
            '-lgomp' if sys.platform == 'linux' else '-lomp',
            '-L' + str(environment / 'lib'),
            '-Wl,-rpath,' + str(environment / 'lib'),
            '-lsleef',
            '-o',
            str(binary),
        ],
        text=True,
        capture_output=True,
        check=False,
        timeout=25,
    )
    assert result.returncode == 0, (
        'The staging witness links the actual producer and adapter: ' + result.stderr
    )
    build_link_failure(root)
    return binary


def build_link_failure(root):
    binary = root / 'failure.so'
    compiler = shutil.which('cc')
    assert compiler, 'The fallback observer requires the pinned C compiler'
    result = subprocess.run(
        [
            compiler,
            '-shared',
            '-fPIC',
            str(ROOT / 'tests/fixtures/project_output/staging_faults.c'),
            '-o',
            str(binary),
            *([] if sys.platform == 'darwin' else ['-ldl']),
        ],
        text=True,
        capture_output=True,
        check=False,
        timeout=20,
    )
    assert result.returncode == 0, (
        'The fallback observer must compile before its result counts: ' + result.stderr
    )
    return binary


@pytest.fixture
def link_failure(native_save):
    return native_save.with_name('failure.so')


def invoke(caller, native_save, action, source, target, environment=None):
    arguments = (
        [str(native_save), action, str(source), str(target)]
        if caller == 'core'
        else [
            sys.executable,
            str(ROOT / 'tests/fixtures/project_output/save_worker.py'),
            ENGINE,
            action,
            str(source),
            str(target),
        ]
    )
    result = subprocess.run(
        arguments, env=environment, capture_output=True, text=True, check=False, timeout=10
    )
    assert result.returncode == 0, (
        'The staging witness must enter the delivered save or fallback without an observer error: '
        + result.stderr
    )
    assert 'entered' in result.stdout, 'The observer enters the delivered save or fallback'
    return result.stdout


@pytest.mark.parametrize('caller', ['api', 'core'])
@pytest.mark.parametrize('action', ['save', 'save-as'])
@pytest.mark.parametrize('layout', ['single', 'scan'])
@pytest.mark.parametrize('alias', ['hard', 'symbolic'])
@pytest.mark.parametrize('cleanup', ['blocked', 'clear'])
def test_failed_staging_removal_preserves_outside_and_prior_project(
    tmp_path, native_save, caller, action, layout, alias, cleanup
):
    source = (
        materialize(tmp_path / 'source')
        if layout == 'single'
        else phase_scan.materialize(tmp_path / 'source')
    )
    relative = Path('carried/note.bin') if layout == 'single' else Path('experiments/scan/01.xy')
    item = source / relative
    item.parent.mkdir(parents=True, exist_ok=True)
    if layout == 'single':
        item.write_bytes(b'carried source bytes\x00different\n')
    carried = item.read_bytes()
    target = source if action == 'save' else materialize(tmp_path / 'destination')
    (target / 'prior-project-marker').write_bytes(b'prior published project\n')
    stage = target.with_name(target.name + '.edi-save-staging')
    retained = stage / relative
    retained.parent.mkdir(parents=True)
    sentinel = tmp_path / 'outside'
    sentinel.write_bytes(b'independent outside sentinel\x00\xff\n')
    if alias == 'hard':
        os.link(sentinel, retained)
    else:
        retained.symlink_to(sentinel)
    before_source, before_target, outside = (
        inventory(source),
        inventory(target),
        sentinel.read_bytes(),
    )
    if cleanup == 'blocked':
        retained.parent.chmod(0o555)
        assert not os.access(retained.parent, os.W_OK), (
            'The witness requires a real directory removal refusal'
        )
        assert os.access(sentinel, os.W_OK), (
            'The retained inode remains writable to expose overwrite after failed removal'
        )
    try:
        outcome = invoke(caller, native_save, action, source, target)
        assert sentinel.read_bytes() == outside, (
            'A failed or successful staging cleanup never overwrites an outside alias'
        )
        if cleanup == 'blocked':
            assert 'refused' in outcome, (
                'A failed removal of an old staging subtree refuses before seeding it'
            )
            assert inventory(source) == before_source, (
                'A refused save preserves all source bytes and links'
            )
            assert inventory(target) == before_target, 'A refused save preserves the prior project'
        else:
            assert 'published' in outcome, (
                'Successful removal of stale staging permits the ordinary save'
            )
            assert (target / relative).read_bytes() == carried, (
                'A successful save carries ordinary and scan data bytes'
            )
    finally:
        unlock(stage, target)


@pytest.mark.parametrize('caller', ['api', 'core'])
@pytest.mark.parametrize('alias', ['hard', 'symbolic'])
def test_link_copy_fallback_refuses_failed_cleanup_before_reusing_entries(
    tmp_path, native_save, link_failure, caller, alias
):
    source = phase_scan.materialize(tmp_path / 'source')
    selected = source / 'experiments/scan/01.xy'
    target = materialize(tmp_path / 'destination')
    sentinel = tmp_path / 'outside'
    sentinel.write_bytes(b'outside fallback sentinel\x00retained\n')
    before_source, before_target, outside = (
        inventory(source),
        inventory(target),
        sentinel.read_bytes(),
    )
    stage = target.with_name(target.name + '.edi-save-staging')
    receipt = tmp_path / 'reached'
    environment = dict(os.environ)
    environment['DYLD_INSERT_LIBRARIES' if sys.platform == 'darwin' else 'LD_PRELOAD'] = str(
        link_failure
    )
    environment.update(
        STAGING_LINK_SOURCE=str(selected),
        STAGING_LINK_SENTINEL=str(sentinel),
        STAGING_LINK_ALIAS=alias,
        STAGING_LINK_RECEIPT=str(receipt),
    )
    try:
        outcome = invoke(caller, native_save, 'save-as', source, target, environment)
        assert receipt.is_file(), 'The witness reaches the actual hard-link failure'
        assert 'link-fallback' in receipt.read_text(), (
            'The failure plants a retained 0555 destination'
        )
        assert 'removal-denied' in receipt.read_text(), (
            'The planted alias really refuses removal before fallback cleanup'
        )
        assert sentinel.read_bytes() == outside, (
            'The hard-link-to-copy fallback cannot overwrite a retained outside alias'
        )
        assert 'refused' in outcome, 'Failed fallback-tree removal refuses before the seeding copy'
        assert inventory(source) == before_source, (
            'A refused fallback preserves the source project'
        )
        assert inventory(target) == before_target, (
            'A refused fallback preserves the prior destination'
        )
    finally:
        unlock(stage, target)
