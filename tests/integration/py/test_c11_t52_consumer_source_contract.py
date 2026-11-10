""": build source paths cannot silently select a stale runtime artifact."""

from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from edi import verification

ROOT = Path(__file__).resolve().parents[3]
SELECTOR = 'EDI_USE_CONSUMER_BUILD'


def _extension() -> Path:
    spec = importlib.util.find_spec('edi._edi')
    assert spec is not None and spec.origin is not None, (
        ' import controls require the extension selected by this verification run'
    )
    return Path(spec.origin)


def _source_import_fixture(tmp_path: Path, configuration: str) -> Path:
    checkout = tmp_path / f'{configuration}-source'
    package = checkout / 'lib/edi'
    shutil.copytree(ROOT / 'lib/edi', package)
    (checkout / 'pyproject.toml').write_text('[project]\nname = "fixture"\n', encoding='utf-8')
    extension_dir = checkout / f'build/{configuration}/python/edi'
    extension_dir.mkdir(parents=True)
    (extension_dir / _extension().name).symlink_to(_extension())
    return checkout


def _import_from(
    checkout: Path,
    extra: dict[str, str],
    script: str = 'import edi; print(edi.__build_commit__)',
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    for name in ('CRYSTA_CONSUMER_SRC', 'EDI_EXTENSION_DIR', SELECTOR):
        env.pop(name, None)
    env.update(extra)
    env['PYTHONPATH'] = os.fspath(checkout / 'lib')
    return subprocess.run(
        [sys.executable, '-c', script],
        cwd=checkout,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )


def _commit_source(source: Path, label: str) -> str:
    (source / 'CMakeLists.txt').write_text(f'# {label}\n', encoding='utf-8')
    subprocess.run(['git', '-C', str(source), 'add', 'CMakeLists.txt'], check=True)
    subprocess.run(
        [
            'git',
            '-C',
            str(source),
            '-c',
            'user.name= Fixture',
            '-c',
            'user.email=fixture@example.invalid',
            'commit',
            '-qm',
            label,
        ],
        check=True,
    )
    return subprocess.check_output(
        ['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True
    ).strip()


def test_non_tree_consumer_source_cannot_select_a_stale_runtime_extension(
    tmp_path: Path,
) -> None:
    checkout = _source_import_fixture(tmp_path, 'ci')
    result = _import_from(checkout, {'CRYSTA_CONSUMER_SRC': '-not-a-source-tree'})
    assert result.returncode == 0, (
        ' CRYSTA_CONSUMER_SRC is a build-time source path, not a truthy runtime selector; '
        'a non-tree value must not redirect import to a possibly stale ci-consumer artifact:\n'
        + result.stderr
    )


def test_literal_hidden_control_uses_the_explicit_consumer_artifact_selector(
    tmp_path: Path,
) -> None:
    checkout = _source_import_fixture(tmp_path, 'ci-consumer')
    result = _import_from(checkout, {SELECTOR: 'hidden-surface-control'})
    assert result.returncode == 0, (
        ' must retain the deliberate literal hidden-control selection through the '
        f'explicit {SELECTOR} contract:\n{result.stderr}'
    )


def test_changed_live_source_cannot_select_a_stale_consumer_extension(tmp_path: Path) -> None:
    checkout = _source_import_fixture(tmp_path, 'ci')
    consumer_extension = checkout / 'build/ci-consumer/python/edi'
    consumer_extension.mkdir(parents=True)
    (consumer_extension / _extension().name).symlink_to(_extension())

    source = tmp_path / 'crysta-source'
    source.mkdir()
    subprocess.run(['git', '-C', str(source), 'init', '-q'], check=True)
    ordinary_sha = _commit_source(source, 'source A')
    consumer_sha = _commit_source(source, 'source B')
    live_sha = _commit_source(source, 'source C')
    records = {
        'build/crysta-src/CRYSTA_SOURCE_SHA': ordinary_sha,
        'build/crysta-prefix/.crysta-sha': ordinary_sha,
        'build/ci/.crysta-linked-sha': ordinary_sha,
        'build/crysta-consumer-prefix/.crysta-sha': consumer_sha,
        'build/ci-consumer/.crysta-linked-sha': consumer_sha,
    }
    for relative, sha in records.items():
        record = checkout / relative
        record.parent.mkdir(parents=True, exist_ok=True)
        record.write_text(sha + '\n', encoding='utf-8')

    result = _import_from(
        checkout,
        {'CRYSTA_CONSUMER_SRC': str(source)},
        'import edi._edi as extension; print(extension.__file__)',
    )
    if result.returncode != 0:
        diagnostic = result.stdout + result.stderr
        assert consumer_sha[:7] in diagnostic and live_sha[:7] in diagnostic, (
            ' a refusal must name the stale consumer artifact and changed live source: '
            + diagnostic
        )
        return
    assert '/build/ci/python/edi/' in result.stdout.replace('\\', '/'), (
        ' CRYSTA_CONSUMER_SRC changed after the consumer artifact was built, yet import '
        'silently selected that stale artifact instead of the explicit ordinary contract: '
        + result.stdout
    )


def _checker_module():
    path = ROOT / 'tools/checks/python_surface_superset.py'
    spec = importlib.util.spec_from_file_location('c11_t52_surface_checker', path)
    assert spec is not None and spec.loader is not None, (
        ' surface-selector control requires the shipped checker module'
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize('consumer', [False, True], ids=['ordinary', 'explicit-consumer'])
def test_runtime_provenance_and_surface_checker_share_the_explicit_selector(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    consumer: bool,
) -> None:
    checker = _checker_module()
    monkeypatch.setattr(verification, '_repo_root', lambda: tmp_path)
    monkeypatch.delenv('EDI_EXTENSION_DIR', raising=False)
    monkeypatch.setenv('CRYSTA_CONSUMER_SRC', '-not-a-source-tree')
    monkeypatch.delenv(SELECTOR, raising=False)
    environ = {'CRYSTA_CONSUMER_SRC': '-not-a-source-tree'}
    prefix = 'crysta-prefix'
    provenance = tmp_path / 'build/crysta-src/CRYSTA_SOURCE_SHA'
    if consumer:
        monkeypatch.delenv('CRYSTA_CONSUMER_SRC')
        environ.pop('CRYSTA_CONSUMER_SRC')
        monkeypatch.setenv(SELECTOR, 'hidden-surface-control')
        environ[SELECTOR] = 'hidden-surface-control'
        prefix = 'crysta-consumer-prefix'
        provenance = tmp_path / 'build/ci-consumer/.crysta-linked-sha'
    assert verification._crysta_provenance_path() == provenance, (
        ' verification labels must identify the explicitly selected artifact, never infer '
        'consumer selection from a source-path string'
    )
    assert checker.resolve_prefix(tmp_path, environ) == tmp_path / 'build' / prefix, (
        ' the Python-surface gate must use the same explicit runtime selector as import'
    )
