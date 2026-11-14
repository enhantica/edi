""": engine comparisons follow the loaded artifact and reject a stale CLI."""

import subprocess
import sys
from pathlib import Path

import pytest

from conftest import crysta_reference_prefix, crysta_reference_source, crysta_source_identity
from tools.testing import fit_policy

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize('configuration', ['ci', 'ci-consumer'])
def test_reference_prefix_matches_loaded_artifact_and_rejects_stale_cli(
    monkeypatch, configuration
):
    prefix_name = 'crysta-prefix' if configuration == 'ci' else 'crysta-consumer-prefix'
    artifact = ROOT / 'build' / configuration
    prefix = ROOT / 'build' / prefix_name
    monkeypatch.setattr(sys.modules['edi._edi'], '__file__', str(artifact / 'python/edi/_edi.so'))
    original = Path.read_text
    stale = False

    def read_text(path, *args, **kwargs):
        if path == artifact / '.crysta-linked-sha':
            return 'a' * 40
        if path == prefix / '.crysta-sha':
            return ('b' if stale else 'a') * 40
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, 'read_text', read_text)
    assert crysta_reference_prefix() == prefix, (
        ' parity must use the CLI corresponding to the loaded edi artifact'
    )
    stale = True
    with pytest.raises(AssertionError, match='different crysta'):
        crysta_reference_prefix()


def test_fit_policy_uses_the_same_corpus_as_the_loaded_engine(monkeypatch):
    expected = crysta_reference_source() / 'tests/fitting'
    monkeypatch.delenv('EDI_CRYSTA_CORPUS_ROOT', raising=False)
    assert fit_policy._corpus_root() == expected, (
        ' the production fit-policy sentinel must select the loaded engine corpus '
        'under CRYSTA_CONSUMER_SRC, without requiring a second override'
    )


def test_exported_source_never_borrows_the_enclosing_repository_identity(tmp_path):
    subprocess.run(['git', 'init', str(tmp_path)], check=True, capture_output=True)
    source = tmp_path / 'exported'
    source.mkdir()
    with pytest.raises(AssertionError, match='own source identity record'):
        crysta_source_identity(source)
    record = source / 'CRYSTA_SOURCE_SHA'
    record.write_text('a7' * 20 + '\n')
    assert crysta_source_identity(source) == 'a7' * 20, (
        'Exported source never borrows the enclosing repository identity.'
    )
    record.write_text('short-or-invalid')
    with pytest.raises(AssertionError, match='full commit'):
        crysta_source_identity(source)


def test_real_checkout_uses_git_and_refuses_a_broken_git_identity(tmp_path):
    subprocess.run(['git', 'init', str(tmp_path)], check=True, capture_output=True)
    (tmp_path / 'CRYSTA_SOURCE_SHA').write_text('a7' * 20)
    # A stale record must not rescue a checkout with unproved Git identity.
    with pytest.raises(subprocess.CalledProcessError):
        crysta_source_identity(tmp_path)
    subprocess.run(
        ['git', '-C', str(tmp_path), 'add', 'CRYSTA_SOURCE_SHA'], check=True, capture_output=True
    )
    subprocess.run(
        [
            'git',
            '-C',
            str(tmp_path),
            '-c',
            'user.name=Fixture',
            '-c',
            'user.email=fixture@example.invalid',
            'commit',
            '-m',
            'Owned source',
        ],
        check=True,
        capture_output=True,
    )
    head = subprocess.check_output(
        ['git', '-C', str(tmp_path), 'rev-parse', 'HEAD'], text=True
    ).strip()
    assert crysta_source_identity(tmp_path) == head, (
        'Real checkout uses git and refuses a broken git identity.'
    )
    assert head != 'a7' * 20, 'Real checkout uses git and refuses a broken git identity.'
