"""F04: effective platform membership governs every semantic pin consumer.

Accident: an activation-table edit moves or duplicates a still canonical pin
line, or a neighbouring TOML edit leaves the document unparsable.
"""

from __future__ import annotations

import re
import subprocess
import sys
from functools import partial

import pytest

from tests.integration.py.test_e09_t75_sdk_consumer import consumer
from tests.system.py.test_e09_t75_native_execution import restore
from tests.system.py.test_e09_t75_sdk_update import update


def declaration(text, accident):
    if accident == 'wrong-table':
        return text.replace('.activation.env]', '.metadata]')
    if accident == 'extra-table':
        line = re.search(r'^CRYSTA_SDK_TAG\s*=.*$', text, re.MULTILINE).group()
        return text + '\n[metadata]\n' + line + '\n'
    if accident == 'invalid-toml':
        return text + '\n[unfinished table\n'
    return text


@pytest.mark.parametrize('reader', ['acquire', 'pairing', 'native', 'updater'])
@pytest.mark.parametrize('accident', ['canonical', 'wrong-table', 'extra-table', 'invalid-toml'])
def test_effective_pin_admission_agrees_through_each_public_consumer(
    tmp_path, reader, accident, request
):
    if reader == 'native':
        request.getfixturevalue('private_native_workflow')
    transform = partial(declaration, accident=accident)
    if reader == 'updater':
        runs, *_ = update(tmp_path, 'pin-currentness', pin_transform=transform)
        result = runs[-1]
    elif reader == 'native':
        result = restore(tmp_path, 'core', 'linux-64', pin_transform=transform)[0][-1]
    else:
        env, repo, _ = consumer(tmp_path, platform='linux-64', download=True, prepare_only=True)
        path = repo / 'pixi.toml'
        path.write_text(transform(path.read_text()))
        args = (
            ['bash', 'tools/ci/crysta-source.sh']
            if reader == 'pairing'
            else [sys.executable, 'tools/ci/crysta_sdk.py', 'fetch', '--platform', 'linux-64']
        )
        result = subprocess.run(
            args, cwd=repo, env=env, capture_output=True, text=True, check=False, timeout=3
        )
    if accident == 'canonical':
        assert result.returncode == 0, (
            f' F04 canonical effective platform pin must admit at {reader}: {result.stderr}'
        )
        if reader == 'pairing':
            assert result.stderr.count('crysta: pinned SDK build-') == 1, (
                ' F04 pairing must emit exactly one effective-pin CI observation'
            )
    else:
        assert result.returncode != 0, (
            f' F04 {reader} cannot credit a pin outside the effective platform declaration'
        )
