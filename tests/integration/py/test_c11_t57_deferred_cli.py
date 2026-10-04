"""Owner 2026-09-26: retain the projects, but do not run or check their fits.

Before: removal was required by the verification-only decision. After: the
three projects remain documented and explicitly non-executing. No scale pin
is read here; the execution witness uses deliberately invalid expectations.
"""

import importlib.util
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
PROJECTS = (
    'pd-neut-cwl_lab6-echidna_fcj-asymmetry',
    'pd-neut-cwl_pbso4_beba-asymmetry',
    'pd-neut-tof_fe_pseudo-voigt',
)
ACTIVE = 'pd-neut-cwl_control_active'


def checker():
    spec = importlib.util.spec_from_file_location(
        'c11_t57_deferred_cli', ROOT / 'tools/checks/cli_projects.py'
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def nav_paths(value):
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [path for child in value.values() for path in nav_paths(child)]
    if isinstance(value, list):
        return [path for child in value for path in nav_paths(child)]
    return []


@pytest.mark.parametrize('project_id', PROJECTS)
def test_projects_remain_registered_nonexecuting_and_documented(project_id):
    rows = checker().registry(ROOT)
    matching = [row for row in rows if row['id'] == project_id]
    assert len(matching) == 1 and matching[0]['executing'] is False, (
        ' each retained CLI project must be registered executing: false'
    )
    directory = ROOT / 'docs/user/cli' / project_id
    assert (directory / 'project/project.edi').is_file(), (
        ' each non-executing project must retain its authored project'
    )
    assert (directory / 'index.md').is_file(), (
        ' each non-executing project must retain its documentation'
    )
    nav = yaml.load((ROOT / 'mkdocs.yml').read_text(), Loader=yaml.BaseLoader)['nav']
    assert f'user/cli/{project_id}/index.md' in nav_paths(nav), (
        ' each non-executing project must remain in the docs nav'
    )


def exercise_dispatch(tmp_path, monkeypatch, *, escape=False, explicit=None):
    module = checker()
    cli = tmp_path / 'docs/user/cli'
    cli.mkdir(parents=True)
    rows = [{'id': name, 'executing': False} for name in PROJECTS]
    rows.append({'id': ACTIVE, 'executing': True})
    (cli / 'projects.yml').write_text(yaml.safe_dump({'schema': 1, 'projects': rows}))
    for name in PROJECTS:
        directory = cli / name
        directory.mkdir()
        (directory / 'expected.json').write_text('invalid deferred expectations')
    reads = Path.read_text

    def guarded_read(path, *args, **kwargs):
        assert not (path.name == 'expected.json' and path.parent.name in PROJECTS), (
            ' CI must not check a non-executing project expectation'
        )
        return reads(path, *args, **kwargs)

    calls = []

    def run_project(_root, project_id):
        assert project_id == ACTIVE, ' CI must not execute a non-executing project'
        calls.append(project_id)
        return []

    monkeypatch.setattr(Path, 'read_text', guarded_read)
    monkeypatch.setattr(module, 'run_project', run_project)
    if escape:
        monkeypatch.setattr(
            module, 'ci_projects', lambda projects: [row['id'] for row in projects]
        )
    args = ['--root', str(tmp_path)]
    if explicit:
        args += ['--project', explicit]
    result = module.main(args)
    assert result == (1 if explicit else 0), (
        ' the CLI runner must refuse explicit deferred selection and accept normal CI'
    )
    assert calls == ([] if explicit else [ACTIVE]), (
        ' CI must execute the active control while excluding every deferred project'
    )


def test_ci_skips_deferred_expectations_and_executes_active_control(tmp_path, monkeypatch):
    exercise_dispatch(tmp_path, monkeypatch)


@pytest.mark.parametrize('project_id', PROJECTS)
def test_explicit_selection_cannot_execute_a_deferred_project(tmp_path, monkeypatch, project_id):
    exercise_dispatch(tmp_path, monkeypatch, explicit=project_id)


def test_ci_execution_escape_is_rejected(tmp_path, monkeypatch):
    with pytest.raises(AssertionError, match='CI must not execute a non-executing project'):
        exercise_dispatch(tmp_path, monkeypatch, escape=True)
