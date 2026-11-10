"""The real Minimizer selector exposes only retained descents and the new default."""

from tests.integration.app import native_actor

streamed_actor = native_actor.streamed_actor
NATIVE_FILE = 'tst_selector_callers.qml'
NATIVE_SELECTORS = {
    'test_real_gui_retains_only_supported_descents': (
        'SelectorCallers::test_retained_descent_options'
    )
}


def test_real_gui_retains_only_supported_descents(streamed_actor):
    streamed_actor.run('SelectorCallers::test_retained_descent_options')
