"""Observe rendering detection, defaults and saved overrides through the actual app."""

import os
from pathlib import Path

import pytest

from tests.fixtures.fast_chart_redraws.rendering import ROOT, actor, capture, qt_reference


def passed(status, output, case):
    assert status == 0 and 'Totals:' in output, (
        'The rendering-setup actor must complete normally: ' + output
    )
    assert f'PASS   : edi_app::RenderingSetup::{case}()' in output, (
        'The actual renderer contract must execute without being skipped: ' + output
    )
    assert '::RenderingSetup::cleanupTestCase()' in output, (
        'The renderer actor must reach cleanup after observing its real window: ' + output
    )


@pytest.fixture(scope='module')
def renderer_states(request, tmp_path_factory):
    status, output = actor('test_qt_reference')
    passed(status, output, 'test_qt_reference')
    selected = [
        item.callspec.params
        for item in request.session.items
        if item.module is request.module and hasattr(item, 'callspec')
    ]
    cases = {entry['case'] for entry in selected if 'case' in entry}
    choices = {entry['choice'] for entry in selected if 'choice' in entry}
    result = {
        'qt': qt_reference(output),
        'cases': {case: actor(case) for case in sorted(cases)},
        'overrides': {},
    }
    root = tmp_path_factory.mktemp('renderer-machines')
    for choice in sorted(choices):
        store = root / choice / 'EasyScience/EasyDiffraction.ini'
        store.parent.mkdir(parents=True)
        env = dict(
            os.environ, EDI_RENDER_ACCEPTANCE_STORE=str(store), EDI_RENDER_ACCEPTANCE_CHOICE=choice
        )
        captures = []
        for phase in ('write', 'read'):
            env['EDI_RENDER_ACCEPTANCE_PHASE'] = phase
            captures.append(actor('test_override_roundtrip', env=env))
        result['overrides'][choice] = store, captures
    return result


def test_actual_qt_renderer_reference_is_available(renderer_states):
    observed_qt = renderer_states['qt']
    assert observed_qt['api'] != 'Unknown', 'The independent renderer reference must name a Qt API'
    if observed_qt['api'] == 'OpenGL':
        assert observed_qt['renderer'], 'OpenGL must expose its actual GL_RENDERER string'


def test_normal_app_reports_its_actual_rendering_setup_at_startup(renderer_states, tmp_path):
    observed_qt = renderer_states['qt']
    env = dict(os.environ)
    env.pop('QSG_INFO', None)
    env.pop('QT_LOGGING_RULES', None)
    binary = Path(os.environ.get('EDI_APP_BINARY', ROOT / 'build/app/app/edi_app'))
    status, output = capture(
        [
            binary,
            '--demo',
            tmp_path / 'startup',
            '--demo-only',
            '01-home',
        ],
        env=env,
    )
    assert status == 0, 'The normal app must complete its bounded startup capture: ' + output
    assert observed_qt['api'].lower() in output.lower(), (
        'The app reports its actual graphics backend at startup without forced Qt debug logging'
    )
    if observed_qt['api'] == 'OpenGL':
        assert observed_qt['renderer'] in output, (
            'The app reports the actual OpenGL renderer string at startup'
        )


@pytest.mark.parametrize(
    'case', ['test_develop_reports_detection', 'test_default_uses_detected_renderer']
)
def test_detected_rendering_setup_in_the_app(renderer_states, case):
    status, output = renderer_states['cases'][case]
    passed(status, output, case)


@pytest.mark.parametrize('choice', ['software', 'gpu'])
def test_user_override_controls_the_renderer_after_a_complete_restart(renderer_states, choice):
    store, captures = renderer_states['overrides'][choice]
    for status, output in captures:
        passed(status, output, 'test_override_roundtrip')
    assert store.is_file(), (
        'The renderer override must survive through the actual machine settings file'
    )
