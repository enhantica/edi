"""The declared commit, never a paired branch or ambient context, selects the SDK."""

import pytest

from tests.integration.py.test_c34_t28_pr_artifact import SHA, acquisition, fetch


@pytest.mark.parametrize('platform', ['linux-64', 'osx-arm64'])
@pytest.mark.parametrize('event', ['pull_request', 'workflow_dispatch', 'push'])
def test_intermediate_build_keeps_the_explicit_pin_despite_foreign_branch_context(
    tmp_path, platform, event
):
    context = acquisition(tmp_path, platform)
    context['env'].update(
        GITHUB_EVENT_NAME=event,
        GITHUB_SHA='b8' * 20,
        GITHUB_HEAD_REF='paired-topic',
        CRYSTA_CONTEXT_REF='paired-topic',
        CRYSTA_SRC=str(tmp_path / 'unrelated-sibling'),
    )
    before = (context['root'] / 'pixi.toml').read_bytes()
    code, output = fetch(context)
    assert code == 0 and 'build-' + SHA in output, output
    assert (context['root'] / 'pixi.toml').read_bytes() == before
