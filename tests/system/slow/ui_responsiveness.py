"""Require the complete external owner scan in the explicit nightly UI run."""

import pytest

from tests.system.app.test_ui_responsiveness import load_observations
from tests.system.app.test_ui_responsiveness import (
    test_actual_watchdog_and_blocking_control as check_watchdog,
)


@pytest.fixture(scope='module')
def observations():
    return load_observations()


def test_full_owner_scan_and_blocking_control(observations):
    _, manifest = observations
    assert manifest['full_scan'] is True, (
        'The nightly scenario must never substitute the reduced PR input'
    )
    assert (
        manifest['archive_sha256']
        == '8a49c250a70181f32424aea38e87edf9054a12aa2916c8e0d60d85946f9cc305'
    ), 'Nightly observations must come from the checksummed complete owner archive'
    check_watchdog(observations, 'e58-pages')
    check_watchdog(observations, 'e58-tabs')
