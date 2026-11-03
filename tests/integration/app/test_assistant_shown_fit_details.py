"""A shown real fit retains its enrichment on the actual model-facing reply."""

import json

import pytest

from tests.integration.app.test_assistant_misfit_workflow import actor_in, replies, send
from tests.system.py import test_e11_t5_dev_native_integration as base


@pytest.fixture(scope='module')
def shown_fit(tmp_path_factory):
    actor = actor_in(
        tmp_path_factory.mktemp('shown-fit-details') / 'actor',
        [[base.tool_call('run_fit', 'shown-fit-reply')]],
        show_actions=True,
    )
    try:
        assert actor.last['ui']['show_actions'] is True, (
            'The actual assistant controller must have Show actions enabled before the fit'
        )
        fit_state = (
            '(function(){const f=Session.project.fit;return '
            '{rows:f.results.count,undo:f.canUndo,running:f.running};})()'
        )
        before = base.qml(actor, fit_state)
        assert before['rows'] == 0 and before['undo'] is False, (
            'The shown-fit positive starts without an earlier native result or fit Undo record'
        )
        send(actor, 1)
        reply = replies(actor)['shown-fit-reply']
        reply['native_before'] = before
        reply['native_after'] = base.qml(actor, fit_state)
        (actor.folder / 'actual-model-facing-shown-fit.json').write_text(
            json.dumps(reply, indent=2) + '\n', encoding='utf-8'
        )
        return reply
    finally:
        actor.close()


def test_shown_real_fit_keeps_model_facing_details_or_explicit_unavailability(shown_fit):
    result = shown_fit['value']
    assert shown_fit['success'] and result.get('adopted') is True, (
        'The Show actions positive must complete and adopt a real native fit before '
        'its model-facing details are judged'
    )
    native = shown_fit['native_after']
    assert (
        native['rows'] > shown_fit['native_before']['rows']
        and native['undo']
        and not native['running']
    ), (
        'The ordinary native fit records a settled result and its real Undo start state, '
        'independently of the model-facing result envelope'
    )
    required = {'misfit', 'diagnostics', 'parameters', 'fit_correlations'}
    assert required <= result.keys() or result.get('fit_details_unavailable') is True, (
        'Every shown adopted-fit reply reaching the model carries all four detail '
        'documents or explicitly marks that details could not be attached'
    )
    if required <= result.keys():
        assert result['misfit'] and isinstance(result['fit_correlations'], dict), (
            'Attached fit details contain actual powder summaries and the declared '
            'correlation document, even when its pairs or implicated parameters are empty'
        )
