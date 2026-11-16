"""Capitalisation is checked on actual painted field, group and header text."""

import json
from pathlib import Path

import pytest

from tests.fixtures.captions.contract import caption_problems
from tests.integration.app.native_actor import NativeActor

ROOT = Path(__file__).resolve().parents[3]
CONTEXTS = json.loads((ROOT / 'tests/fixtures/captions/contexts.json').read_text())
TYPE_FIELDS = {
    'experimentType.sampleForm',
    'experimentType.beamMode',
    'experimentType.radiationProbe',
    'experimentType.scatteringType',
    'experimentType.dimensionality',
    'experimentType.polarisation',
}


@pytest.fixture(scope='module')
def actor(request, tmp_path_factory):
    selected = [
        (
            'RenderedCaptions::test_context:' + item.callspec.params['context']
            if item.originalname == 'test_actual_rendered_captions_follow_the_capitalisation_rule'
            else 'RenderedCaptions::test_probe_controls'
        )
        for item in request.session.items
        if getattr(item, 'module', None) is request.module
        and item.originalname
        in {
            'test_actual_rendered_captions_follow_the_capitalisation_rule',
            'test_rendered_probe_reaches_each_runtime_caption_escape',
        }
    ]
    owner = NativeActor(
        tmp_path_factory.mktemp('rendered-captions'),
        'tst_rendered_captions.qml',
        selected,
        timeout=45,
    )
    try:
        yield owner
    finally:
        owner.close()


@pytest.mark.parametrize('context', [row['tag'] for row in CONTEXTS])
def test_actual_rendered_captions_follow_the_capitalisation_rule(actor, context):
    actor.run('RenderedCaptions::test_context:' + context)
    marker = 'RENDERED_CAPTIONS '
    records = [
        json.loads(line.split(marker, 1)[1])
        for line in actor.log_path.read_text(encoding='utf-8').splitlines()
        if marker in line
    ]
    matching = [record for record in records if record['context'] == context]
    assert len(matching) == 1, 'Each native context publishes exactly one actual caption census'
    rows = matching[0]['rows']
    found = {row['owner'] for row in rows if row['kind'] == 'field'}
    if context in {'measured', 'cwl', 'tof', 'single'}:
        assert found >= TYPE_FIELDS, (
            'Every real Experiment type selector, including disabled ones, has a painted title: '
            + repr(TYPE_FIELDS - found)
        )
    if context in {'cwl', 'tof'}:
        assert {'range.minimum', 'range.maximum', 'range.step'} <= found, (
            'The real calculation range exposes every axis-summary field title'
        )
        assert any(row['owner'] == 'group.data_range' for row in rows), (
            'The census reaches the actual Calculation range group title'
        )
    if context == 'analysis-basic':
        assert any(row['kind'] == 'header' for row in rows), (
            'The untitled real parameter group still contributes its rendered table headers'
        )
    problems = caption_problems(rows)
    assert not problems, (
        'Actual painted field labels, group titles and table headers start with a capital '
        'or case-significant notation: ' + repr(problems)
    )


def test_rendered_probe_reaches_each_runtime_caption_escape(actor):
    actor.run('RenderedCaptions::test_probe_controls')
    marker = 'CAPTION_PROBE_CONTROLS '
    records = [
        json.loads(line.split(marker, 1)[1])
        for line in actor.log_path.read_text(encoding='utf-8').splitlines()
        if marker in line
    ]
    assert len(records) == 1, 'The original rendered probe publishes one complete control record'
    frames = {row['name']: row for row in records[0]}
    assert frames.keys() == {
        'positive',
        'dynamic-lowercase',
        'painted-only-lowercase',
        'missing-painted-title',
        'group-lowercase',
        'header-lowercase',
        'missing-painted-header',
        'scientific-symbol',
    }, 'Every runtime caption escape reaches its actual native control before qualification'
    for name, frame in frames.items():
        problems = caption_problems(frame['rows'])
        assert bool(problems) == (name not in {'positive', 'scientific-symbol'}), (
            'Actual painted-control mutations are refused while capital prose and symbols pass: '
            + repr((name, problems))
        )
    assert frames['painted-only-lowercase']['backing'] == 'Future axis', (
        'The probe changes only the painted text, proving metadata alone cannot satisfy the gate'
    )
    assert not any(
        row['text'] == 'lowercase row content' or row['text'] == 'lowercase field value'
        for row in frames['positive']['rows']
    ), 'Row values and editable values are not mistaken for field titles or table headers'
    assert any(
        row['owner'] == 'unlisted.dynamic.selector' and not row['enabled']
        for row in frames['positive']['rows']
    ), 'Disabled and unlisted future descriptors stay in the rendered census'
