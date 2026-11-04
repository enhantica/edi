"""Exercise online loading through the shared production Qt host."""

import pytest

from tests.integration.app.online_load_host import run_online_host


@pytest.fixture(scope='module')
def online_host(tmp_path_factory):
    with run_online_host(tmp_path_factory.mktemp('online-host')) as host:
        yield host


@pytest.mark.parametrize(
    ('case', 'tag'),
    [
        ('new_experiment_wavelength', ''),
        ('actions_and_formats', 'structure'),
        ('actions_and_formats', 'experiment'),
        ('from_web_opens_source_selector', 'structure'),
        ('from_web_opens_source_selector', 'experiment'),
        ('from_web_opens_source_selector', 'measured'),
    ],
)
def test_online_load_controls(online_host, case, tag):
    online_host.check(case, tag)
