"""Current palette expectations bind approved release bytes, preserving old captures."""

import hashlib
import importlib.util
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
HERE = ROOT / 'tests/fixtures/chart_controls'


@pytest.fixture
def generator():
    spec = importlib.util.spec_from_file_location(
        'current_bragg_reference', HERE / 'generate_bragg.py'
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_current_and_historical_bragg_fixtures_reproduce_their_own_approved_sources(
    generator, tmp_path, monkeypatch
):
    monkeypatch.setattr(generator, '__file__', str(tmp_path / 'generate_bragg.py'))
    monkeypatch.setattr(generator.sys, 'argv', ['generate_bragg.py', '--current'])
    generator.main()
    current = (tmp_path / 'bragg-current.hpp').read_bytes()
    assert current == (HERE / 'bragg-current.hpp').read_bytes()
    assert generator.PUBLISHED_SHA256.encode() in current
    assert current.count(b'{"main",') == current.count(b'{"colourBlindSafe",') == 18
    (tmp_path / 'owner.json').write_bytes((HERE / 'owner.json').read_bytes())
    monkeypatch.setattr(generator.sys, 'argv', ['generate_bragg.py'])
    generator.main()
    assert (tmp_path / 'bragg.hpp').read_bytes() == (HERE / 'bragg.hpp').read_bytes()


@pytest.mark.parametrize('damage', ['colour', 'provenance'])
def test_changed_release_reference_cannot_silently_regenerate_expectations(
    generator, monkeypatch, damage
):
    raw = subprocess.check_output([
        'git',
        '-C',
        str(ROOT),
        'show',
        generator.PUBLISHED + ':' + generator.PUBLISHED_SOURCE,
    ])
    assert hashlib.sha256(raw).hexdigest() == generator.PUBLISHED_SHA256
    changed = raw.replace(b'#618EC8', b'#618EC9') if damage == 'colour' else raw + b'\n'
    assert changed != raw
    monkeypatch.setattr(generator.subprocess, 'check_output', lambda *_a, **_k: changed)
    with pytest.raises(ValueError, match='published palette reference changed'):
        generator.published_palettes()
