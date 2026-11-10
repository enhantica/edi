"""Existing projects require confirmation, preserve cancellation, and replace atomically."""

import json
import re
import shutil
import stat
from pathlib import Path

import pytest

from tests.integration.app.online_load_host import run_online_host

ROOT = Path(__file__).resolve().parents[3]
VALUES = {
    'name': 'collision',
    'title': 'Replacement title',
    'authors': 'Ada; Bert',
    'description': 'Replacement description kept in the form',
}


@pytest.fixture(scope='module')
def creation_host(tmp_path_factory):
    with run_online_host(
        tmp_path_factory.mktemp('creation-confirmation'),
        failure_entries=False,
        offline_http=True,
        session_type='ProjectCreationSession',
    ) as host:
        yield host


def inputs(host, parent):
    parent.mkdir(parents=True, exist_ok=True)
    (host.mailbox / 'creation-inputs.json').write_text(
        json.dumps({**VALUES, 'parent': parent.as_uri(), 'nativeParent': str(parent)})
    )
    return parent / VALUES['name']


def existing_project(host, parent):
    target = inputs(host, parent)
    shutil.copytree(ROOT / 'docs/user/cli/pd-neut-cwl_lbco-hrpt/project', target)
    metadata = target / 'project.edi'
    text = re.sub(
        r'(?m)^_metadata.name\s+.*$', '_metadata.name ' + VALUES['name'], metadata.read_text()
    )
    text = re.sub(
        r'(?m)^(_metadata\.(?:created|last_modified))\s+.*$',
        r'\1 "01 Jan 2001 00:00:00"',
        text,
    )
    metadata.write_text(text)
    return target


def tree(folder, *, model_only=False):
    def contents(path):
        value = path.read_bytes()
        if model_only and path.relative_to(folder) == Path('project.edi'):
            value = re.sub(
                rb'(?m)^(_metadata\.(?:created|last_modified))\s+.+$',
                rb'\1 CLOCK',
                value,
            )
        return value

    return {
        str(path.relative_to(folder)): contents(path)
        for path in folder.rglob('*')
        if path.is_file()
        and (
            not model_only
            or path.suffix in {'.edi', '.cif', '.xye', '.xy', '.dat', '.int', '.hkl'}
        )
    }


def test_fresh_creation_is_the_independent_overwrite_control(creation_host, tmp_path):
    target = inputs(creation_host, tmp_path / 'fresh')
    creation_host.check('creation_fresh')
    assert (target / 'project.edi').is_file(), (
        'The ordinary fresh-create control writes a real project'
    )


def test_cancel_keeps_old_bytes_and_every_form_value(creation_host, tmp_path):
    target = existing_project(creation_host, tmp_path / 'existing')
    before = tree(target)
    try:
        creation_host.check('creation_cancel')
    finally:
        assert tree(target) == before, 'Cancel preserves every old project byte'


def test_replace_equals_creation_in_an_empty_folder(creation_host, tmp_path):
    fresh = inputs(creation_host, tmp_path / 'fresh')
    creation_host.check('creation_fresh')
    expected = tree(fresh, model_only=True)
    target = existing_project(creation_host, tmp_path / 'existing')
    creation_host.check('creation_replace')
    assert b'01 Jan 2001 00:00:00' not in (target / 'project.edi').read_bytes(), (
        'Replace discards the old project clock metadata as well as its old model'
    )
    assert tree(target, model_only=True) == expected, (
        'Replace produces the same complete persisted project inputs as ordinary fresh creation'
    )


def test_failed_replace_keeps_old_bytes_and_explains_the_reason(creation_host, tmp_path):
    parent = tmp_path / 'existing'
    target = existing_project(creation_host, parent)
    before = tree(target)
    mode = stat.S_IMODE(parent.stat().st_mode)
    try:
        creation_host.check('creation_prepare_failure')
        parent.chmod(0o555)
        creation_host.check('creation_confirm_failure')
    finally:
        parent.chmod(mode)
        assert tree(target) == before, 'A failing Replace preserves every old project byte'
