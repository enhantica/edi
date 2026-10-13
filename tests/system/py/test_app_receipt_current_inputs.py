"""Actual compiled app receipts refuse stale production and selected SDK inputs."""

import hashlib
import json
import os
from pathlib import Path

import pytest

from tests.conftest import crysta_reference_prefix, crysta_reference_source
from tests.fixtures.app_environment.closure import validate_bundle, validate_dependencies
from tests.fixtures.app_environment.observations import Observations
from tests.fixtures.scan_app.build_probe import validate_current_inputs, validate_fixture
from tests.fixtures.scan_app.receipt_controls import stale_reuse
from tests.fixtures.scan_screen import harness as screen_harness
from tests.fixtures.thread_selector import harness as selector_harness

HOSTS = {'selector': selector_harness, 'screen': screen_harness}


@pytest.fixture(scope='module')
def compiled_hosts(tmp_path_factory):
    scratch = tmp_path_factory.mktemp('compiled-app-receipts')

    def observe(key):
        kind, backend = key
        harness = HOSTS[kind]
        prefix = 'EDI_THREAD_SELECTOR_' if kind == 'selector' else 'EDI_SCAN_SCREEN_'
        path = os.environ.get(prefix + backend.upper() + '_RECEIPT')
        if path:
            receipt = json.loads(Path(path).read_text(encoding='utf-8'))
            validate_dependencies(receipt, kind, harness.ROOT)
            validate_bundle(receipt)
            validate_current_inputs(
                receipt, harness.ROOT, crysta_reference_prefix(), crysta_reference_source()
            )
            validate_fixture(receipt, Path(harness.__file__).parent)
            assert receipt['backend'] == backend, (
                'Compiled app receipts retain their actual selected host backend'
            )
            assert receipt['production'] == receipt['compiled_inputs']['production'], (
                'Compiled app receipts agree with their validated current production inputs'
            )
            binary = hashlib.sha256(Path(receipt['executable']).read_bytes()).hexdigest()
            assert binary == receipt['binary'], (
                'Compiled app receipts retain their actual built host executable'
            )
        else:
            receipt = harness.observation(backend, scratch / kind / backend)['receipt']
        return receipt

    return Observations(observe)


@pytest.mark.parametrize('kind', HOSTS)
@pytest.mark.parametrize('backend', ['desktop', 'browser'])
@pytest.mark.parametrize('seam', ['entry', 'sdk-header', 'sdk-source', 'sdk-library'])
def test_real_host_receipt_refuses_stale_compiled_inputs(
    compiled_hosts, kind, backend, seam, tmp_path, monkeypatch
):
    stale_reuse(HOSTS[kind], compiled_hosts[kind, backend], backend, seam, tmp_path, monkeypatch)
