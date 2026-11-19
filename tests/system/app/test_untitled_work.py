"""Untitled work, first Save and purpose-specific creation fields."""

import pytest

from tests.integration.app.native_actor import NativeActor

CASES = sorted([
    'a_structure_and_experiment_before_create',
    'b_first_save_names_and_preserves_work',
    'c_cancel_first_save_keeps_work',
    'd_quit_cancel_and_discard',
    'd2_quit_save_names_and_closes',
    'e_dialog_labels',
    *[
        f'f_dialog_hints:{field}'
        for field in ('name', 'title', 'authors', 'description', 'location')
    ],
])
NATIVE_FILE = 'tst_untitled_work.qml'
NATIVE_SELECTORS = {f'test_untitled_work[{case}]': 'UntitledWork::test_' + case for case in CASES}


@pytest.fixture(scope='module')
def actor(request, tmp_path_factory):
    selected = [item.name for item in request.session.items if item.module is request.module]
    assert selected == [name for name in NATIVE_SELECTORS if name in selected], (
        'Untitled actors preserve the declared native execution order'
    )
    native = NativeActor(
        tmp_path_factory.mktemp('untitled-owner'),
        NATIVE_FILE,
        [NATIVE_SELECTORS[name] for name in selected],
        timeout=40,
    )
    try:
        yield native
    finally:
        native.close()


@pytest.mark.parametrize('case', CASES)
def test_untitled_work(case, actor):
    actor.run('UntitledWork::test_' + case)
