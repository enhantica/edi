"""Shared UI acceptance through the production Qt host, without network access."""

import os
import re
import subprocess

import pytest

from tests.integration.app import native_actor
from tests.integration.app.native_actor import (
    ROOT,
    require_pointer_driver,
)

CASES = [
    ('tst_shared_tooltips.qml', 'SharedTooltips', 'defaults'),
    ('tst_shared_tooltips.qml', 'SharedTooltips', 'persistence'),
    ('tst_shared_tooltips.qml', 'SharedTooltips', 'delay_clock'),
    ('tst_shared_tooltips.qml', 'SharedTooltips', 'disabled_app_control'),
    ('tst_shared_tooltips.qml', 'SharedTooltips', 'help_controls'),
    ('tst_shared_tooltips.qml', 'SharedTooltips', 'group_boundary'),
    ('tst_shared_tooltips.qml', 'SharedTooltips', 'app_bar'),
    ('tst_shared_tooltips.qml', 'SharedTooltips', 'button_clicks'),
]
CASES.extend(
    ('tst_shared_tooltips.qml', 'SharedTooltips', f'{name}:{tag}')
    for name, tags in {
        'migration': ['false', 'true'],
        'disabled_slider_reason': ['unbound-alias', 'empty-alias', 'value-alias'],
        'selector_popup_owner': ['Off', 'Important', 'All'],
        'experiment_selector_owners': ['powder', 'single crystal'],
    }.items()
    for tag in tags
)

CASES.extend(
    ('tst_shared_tooltips.qml', 'SharedTooltips', f'levels:{level}-{self_explanatory}-{enabled}')
    for level in ('Off', 'Important', 'All')
    for self_explanatory in ('false', 'true')
    for enabled in ('false', 'true')
)

CASES.sort(key=lambda row: row[2].partition(':')[0])
streamed_actor = native_actor.streamed_actor

NATIVE_FILE = 'tst_shared_tooltips.qml'
NATIVE_SELECTORS = {
    f'test_shared_control_contract[{case}]': f'{suite}::test_{case}' for _, suite, case in CASES
}


@pytest.mark.parametrize(('file', 'suite', 'case'), CASES, ids=[case for _, _, case in CASES])
def test_shared_control_contract(file, suite, case, streamed_actor):
    assert file == NATIVE_FILE, 'ADR-0076: every shared row uses its declared native actor'
    streamed_actor.run(f'{suite}::test_{case}')


def test_every_registered_native_case_has_a_python_witness():
    runner = ROOT / 'build/app/app/edi_app_tests'
    require_pointer_driver(runner)
    result = subprocess.run(
        [str(runner), '-input', str(ROOT / 'tests/unit/app' / NATIVE_FILE), '-functions'],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
        env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen', 'QT_QUICK_BACKEND': 'software'},
    )
    assert result.returncode == 0, (
        'ADR-0076: the original Qt host must register the complete shared-control actor'
    )
    actual = set(re.findall(r'SharedTooltips::test_(\w+)\(\)', result.stdout + result.stderr))
    selected = {case.partition(':')[0] for _, _, case in CASES}
    assert actual == selected | {'supported_only_selectors'}, (
        'ADR-0076: every registered shared native case has its own Python witness, '
        'including the supported-only selector witness in its separate module'
    )
