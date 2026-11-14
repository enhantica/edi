"""ADR-0083 replaces Crysta PR/release discovery with Edi-owned qualified archives.

The synthetic SDK bytes and ABI locks are independently authored fixtures. They
exercise the real local reader; cloud producer evidence belongs to actual CI.
"""

import contextlib
import importlib.util
import io
import os
from unittest.mock import patch

import pytest

from tests.integration.py.test_e09_t75_sdk_consumer import SHA, consumer


def acquisition(tmp_path, platform='osx-arm64', defect=None):
    env, root, sdk = consumer(tmp_path, defect, platform, download=True, prepare_only=True)
    spec = importlib.util.spec_from_file_location(
        'archive_reader', root / 'tools/ci/crysta_sdk.py'
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return {'env': env, 'root': root, 'sdk': sdk, 'module': module, 'platform': platform}


def fetch(context):
    output = io.StringIO()
    with (
        patch.dict(os.environ, context['env'], clear=True),
        contextlib.redirect_stdout(output),
        contextlib.redirect_stderr(output),
    ):
        code = context['module'].main(['fetch', '--platform', context['platform']])
    assert not (context['root'].parent / 'commands').exists(), (
        'SDK consumption cannot invoke Git, network, authentication or compiler executables'
    )
    assert not (context['root'].parent / 'downloads').exists(), (
        'SDK consumption cannot fall back to a retired Crysta release or PR download'
    )
    return code, output.getvalue()


@pytest.mark.parametrize('platform', ['linux-64', 'osx-arm64'])
def test_edi_owned_archive_installs_exact_qualified_bytes_without_network(tmp_path, platform):
    context = acquisition(tmp_path, platform)
    before = (context['root'] / 'pixi.toml').read_bytes()
    code, output = fetch(context)
    assert code == 0, output
    home = context['root'] / 'build/crysta-sdk' / f'{SHA}-{platform}'
    assert (home / 'lib/libcrysta_core.a').read_bytes() == (
        context['sdk'] / 'lib/libcrysta_core.a'
    ).read_bytes(), 'The consumer unpacks the independently qualified exact library'
    assert (context['root'] / 'pixi.toml').read_bytes() == before
    assert 'sha256 ' in output and 'platform ' + platform in output


@pytest.mark.parametrize('platform', ['linux-64', 'osx-arm64'])
@pytest.mark.parametrize(
    'defect',
    [
        'archive-source',
        'archive-platform',
        'archive-library',
        'archive-missing',
        'archive-truncated',
        'version',
        'build',
        'package',
    ],
)
def test_qualified_archive_reader_refuses_substitution_without_fallback(
    tmp_path, platform, defect
):
    context = acquisition(tmp_path, platform, defect)
    code, output = fetch(context)
    assert code != 0 and 'REFUSED' in output, output
    assert not (context['root'] / 'build/crysta-prefix').exists()
