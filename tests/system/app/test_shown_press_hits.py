"""Run Qt's own input hit test beside each shown native press path."""

import pytest

from tests.integration.app.native_actor import NativeActor

CASES = sorted(
    f'{route}-{cover}'
    for route in ('navigate', 'context', 'row', 'search')
    for cover in ('cover', 'decoration')
)
NATIVE_SELECTORS = {
    f'test_shown_press[{case}]': 'ShownPressHits::test_native_hit:' + case for case in CASES
}


@pytest.fixture(scope='module')
def actor(request, tmp_path_factory):
    names = {item.name for item in request.session.items if item.module is request.module}
    native = NativeActor(
        tmp_path_factory.mktemp('shown-press'),
        'tst_shown_press_hits.qml',
        [selector for node, selector in NATIVE_SELECTORS.items() if node in names],
        timeout=25,
    )
    try:
        yield native
    finally:
        native.close()


@pytest.mark.parametrize('case', CASES)
def test_shown_press(actor, case):
    actor.run('ShownPressHits::test_native_hit:' + case)
