"""Seq44: a killed CI job must not strand currency clones or SDK downloads."""

from __future__ import annotations

import sys

import pytest

from tests.fixtures.e09_t75_scratch import directories, exercise, observe_tool
from tests.integration.py.test_e09_t75_sdk_consumer import consumer
from tests.system.py.test_e09_t75_pin_currency import currency_world


@pytest.mark.parametrize('ending', ['finish', 'fail', 'term', 'kill'])
def test_currency_clone_lifetime_crosses_the_public_check(tmp_path, ending):
    build, _ = currency_world(tmp_path, 'unpaired-ancestor')
    directories(tmp_path, build.env)
    git = tmp_path / 'bin/git'
    git.write_text('#!/bin/sh\nexec ' + build.git + ' "$@"\n')
    git.chmod(0o755)
    observe_tool(git, "'clone' in a")
    exercise(['bash', 'tools/ci/crysta-source.sh', '--currency'], build.edi, build.env, ending)


@pytest.mark.parametrize('ending', ['finish', 'fail', 'term', 'kill'])
def test_download_staging_lifetime_crosses_the_public_sdk_entry(tmp_path, ending):
    env, repo, _ = consumer(tmp_path, platform='linux-64', download=True, prepare_only=True)
    directories(tmp_path, env)
    observe_tool(
        tmp_path / 'bin/curl',
        "'https://api.github.com/repos/enhantica/crysta/releases/assets/1001' in a",
    )
    exercise(
        [sys.executable, 'tools/ci/crysta_sdk.py', 'fetch', '--platform', 'linux-64'],
        repo,
        env,
        ending,
    )
