"""Held adjustments calculate live and publish derived project work once at release."""

import pytest

from tests.integration.app.online_load_host import run_online_host


@pytest.fixture(scope='module')
def drag_host(tmp_path_factory):
    with run_online_host(
        tmp_path_factory.mktemp('slider-release'),
        failure_entries=False,
        offline_http=True,
        session_type='SliderReleaseSession',
        request_timeout=50,
    ) as host:
        yield host


@pytest.mark.parametrize('category', ['cell', 'wavelength', 'profile'])
def test_held_adjustment_defers_text_context_and_one_undo(drag_host, category):
    drag_host.check('deferred', category)


def test_real_analysis_slider_has_one_release_and_one_undo(drag_host):
    drag_host.check('real_slider')
