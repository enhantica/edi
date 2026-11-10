"""Owner 87b1447a8: ordinary callers must use the effective public pin result.

A caller already parsing pixi.toml may accidentally hand pin_tag a selected
raw environment table. Public API misuse is in scope; private access is not.
"""

from __future__ import annotations

import importlib.util
import sys
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SHA = 'a1' * 20


def sdk_module():
    path = ROOT / 'tools/ci/crysta_sdk.py'
    spec = importlib.util.spec_from_file_location('public_sdk_pin_gate', path)
    assert spec is not None and spec.loader is not None, (
        ' owner 87b1447a8 the real public SDK module must be loadable'
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize('source', ['parsed-table', 'copied-table'])
def test_pin_tag_accepts_effective_results_and_refuses_caller_selected_raw_tables(source):
    sdk = sdk_module()
    text = '\n'.join(
        f'[target.{p}.activation.env]\nCRYSTA_SDK_TAG = "build-{SHA}"\n'
        f'CRYSTA_SDK_SHA256 = "{"8" * 64}"\n'
        for p in ('linux-64', 'osx-arm64')
    )
    fields = sdk.pin_fields(text, 'linux-64')
    assert sdk.pin_tag(fields) == 'build-' + SHA, (
        ' owner 87b1447a8 a real effective pin result must remain usable'
    )
    raw = tomllib.loads(text)['target']['linux-64']['activation']['env']
    if source == 'copied-table':
        raw = dict(raw)
    with pytest.raises((sdk.RefusedError, TypeError, ValueError, KeyError)):
        sdk.pin_tag(raw)
