"""Ordinary pointer input releases one complete undoable slider operation."""

import pytest

from tests.integration.app.online_load_host import run_online_host


@pytest.fixture(scope='module')
def pointer_host(tmp_path_factory):
    with run_online_host(
        tmp_path_factory.mktemp('slider-pointer'),
        failure_entries=False,
        offline_http=False,
        session_type='SliderReleaseSession',
        request_timeout=50,
    ) as host:
        host.check('prepare_real_slider')
        yield host


def test_real_analysis_slider_has_one_release_and_one_undo(pointer_host):
    pointer_host.check('real_slider')
