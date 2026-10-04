""": engine comparisons follow the loaded artifact and reject a stale CLI."""

import sys
from pathlib import Path

import pytest

from conftest import crysta_reference_prefix, crysta_reference_source
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
