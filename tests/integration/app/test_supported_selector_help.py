"""Supported-only selectors explain their restriction through the shared popup."""

from tests.integration.app import native_actor

streamed_actor = native_actor.streamed_actor

NATIVE_FILE = 'tst_shared_tooltips.qml'
NATIVE_SELECTORS = {
    'test_supported_only_selectors_are_disabled_and_explain_the_reason': (
        'SharedTooltips::test_supported_only_selectors'
    )
}


def test_supported_only_selectors_are_disabled_and_explain_the_reason(streamed_actor):
    streamed_actor.run('SharedTooltips::test_supported_only_selectors')
