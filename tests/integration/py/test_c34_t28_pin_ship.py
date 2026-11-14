"""The one commit pin is independent of publication and changes only on explicit request."""

import importlib.util
from unittest.mock import patch

import pytest

from tests.integration.py.test_c34_t28_pr_artifact import SHA, acquisition, fetch


def pin_module(context):
    path = context['root'] / 'tools/ci/crysta_sdk_pin.py'
    spec = importlib.util.spec_from_file_location('archive_pin', path)
    module = importlib.util.module_from_spec(spec)
    with patch.dict('sys.modules', {'crysta_sdk': context['module']}):
        spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize('platform', ['linux-64', 'osx-arm64'])
def test_explicit_commit_pin_is_checked_then_consumed_without_publication(tmp_path, platform):
    context = acquisition(tmp_path, platform)
    pin = context['root'] / 'pixi.toml'
    pin.write_text(pin.read_text().replace(SHA, 'b8' * 20))
    module = pin_module(context)
    assert SHA in module.pin([SHA], pin)
    before = pin.read_bytes()
    assert SHA in module.pin(['--check'], pin)
    assert pin.read_bytes() == before
    code, output = fetch(context)
    assert code == 0 and 'build-' + SHA in output, output
    assert pin.read_bytes() == before


@pytest.mark.parametrize(
    'args', [[], ['--ship'], ['main'], ['a' * 39], ['A' * 40], ['a' * 40, 'extra']]
)
def test_pin_refuses_legacy_or_malformed_inputs_without_rewriting(tmp_path, args):
    context = acquisition(tmp_path)
    pin = context['root'] / 'pixi.toml'
    before = pin.read_bytes()
    with pytest.raises(context['module'].RefusedError, match='usage:'):
        pin_module(context).pin(args, pin)
    assert pin.read_bytes() == before
