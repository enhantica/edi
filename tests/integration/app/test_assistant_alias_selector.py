"""Visible alias choices use canonical targets and discard unfinished rows."""

import json
import os
import shutil
from pathlib import Path

import pytest

from tests.integration.app.test_assistant_misfit_workflow import replies
from tests.system.py import test_e11_t5_dev_native_integration as native

TARGET = 'structure.atom_sites[B].adp_iso'
ALIAS = 'B_site_B'


def canonical_target(actor):
    offered = native.qml(
        actor,
        '(function(){const p=Session.project,t=p.parameters;'
        'return p.analysis.aliases.parameterNames.map(function(name){'
        'const n=p.parameterNumber(name);return '
        '{name:name,path:n>0&&n<=t.count?t.text(n-1,"path"):null};});})()',
    )
    found = [row['name'] for row in offered if row['path'] == TARGET]
    assert len(found) == 1, (
        'The selector offers exactly one canonical name for site B isotropic displacement'
    )
    return found[0]


def witness(actor, marker):
    return native.qml(
        actor,
        '(function(){const o='
        + native._scene_control_expression(marker)
        + ';o.scan();return o.facts;})()',
    )


def observe(binary, folder, endpoint):
    folder.mkdir()
    actor = native.MainActor(
        binary,
        folder,
        {
            'turns': [
                [
                    native.tool_call(
                        'add_relations',
                        'atom-adp-alias',
                        aliases=[{'id': ALIAS, 'path': TARGET}],
                        constraints=[],
                    )
                ]
            ]
        },
        True,
    )
    try:
        project = folder / 'project'
        shutil.copytree(native.ROOT / 'tests/fixtures/fit_quality/uncertainty', project)
        assert actor.command('open', path=str(project))['reply']['opened'], (
            'The visible alias replay loads the unchanged site A and B reference project'
        )
        actor.until(lambda row: not row['ui']['project']['calculating'])
        if native._unique_input_control(actor.last, 'home.start') is not None:
            actor.command('click', name='home.start')
        # The connection prelude uses the public sign-in operation and the offline peer.
        actor.command('accept_context')
        actor.until(lambda row: row['ui']['connected'])
        before = actor.command('inspect')['ui']['project']
        name = canonical_target(actor)
        assert actor.last['ui']['show_actions'], (
            'The native alias request runs with Show actions enabled'
        )
        marker = 'alias-selector-choices'
        native._watch_original_offered_choices(actor, marker)
        actor.request('Add an alias for site B isotropic displacement using the shown controls.')
        pending = None
        if endpoint == 'stop':
            actor.until(
                lambda row: (
                    row['ui']['can_cancel']
                    and len(row['ui']['project']['aliases']) == len(before['aliases']) + 1
                    and row['ui']['project']['aliases'][-1]['parameter'] != name
                ),
                visible_progress=True,
            )
            pending = actor.last['ui']['project']['aliases']
            actor.command('cancel')
        actor.until(
            lambda row: (
                not row['ui']['can_cancel'] and row['ui']['state'] in {'idle', 'interrupted'}
            ),
            visible_progress=True,
        )
        after = actor.command('inspect')['ui']['project']
        facts = witness(actor, marker)
        wire = replies(actor)
        events = list(map(json.loads, actor.trace.read_text().splitlines()))
        receipt = {
            'target': TARGET,
            'canonical_name': name,
            'before': before['aliases'],
            'pending': pending,
            'after': after['aliases'],
            'wire': wire,
            'choices': facts,
            'interrupts': [e for e in events if e.get('method') == 'turn/interrupt'],
        }
        (actor.folder / 'alias-selector.json').write_text(json.dumps(receipt, indent=2) + '\n')
        receipt['constraints_before'] = before['constraints']
        receipt['constraints_after'] = after['constraints']
        receipt['show_actions'] = actor.last['ui']['show_actions']
        receipt['selector'] = None
        if endpoint == 'choose' and wire.get('atom-adp-alias', {}).get('success'):
            control = 'alias.parameter.' + str(len(before['aliases']))
            receipt['selector'] = native.qml(
                actor,
                '(function(){const b='
                + native._scene_control_expression(control)
                + ';return {names:b.names,shown:b.model,index:b.currentIndex};})()',
            )
        (actor.folder / 'alias-selector.json').write_text(json.dumps(receipt, indent=2) + '\n')
        return receipt
    finally:
        actor.close()


@pytest.fixture(scope='module')
def evidence(tmp_path_factory):
    root = tmp_path_factory.mktemp('shown-alias-selector')
    source = Path(
        os.environ.get(
            'EDI_ASSISTANT_UI_PROBE',
            native.ROOT / 'build/app/assistant-ui-probe/assistant_real_owner_probe',
        )
    )
    binary, identity = native._frozen_main_probe(source, root)
    (root / 'selected-probe.json').write_text(json.dumps(identity, indent=2) + '\n')
    return {
        endpoint: observe(binary, root / endpoint, endpoint) for endpoint in ('choose', 'stop')
    }


@pytest.mark.parametrize('endpoint', ['choose', 'stop'])
def test_shown_alias_targets_atom_adp_and_discards_unfinished_row(evidence, endpoint):
    record = evidence[endpoint]
    assert record['show_actions'], 'Both native relation calls retain Show actions enabled'
    assert record['constraints_after'] == record['constraints_before'], (
        'Adding or stopping an alias preserves all existing constraints'
    )
    if endpoint == 'stop':
        assert record['pending'][-1]['parameter'] != record['canonical_name'], (
            'Stop reaches a genuinely appended alias before the requested parameter is chosen'
        )
        assert len(record['interrupts']) == 1, (
            'Stop interrupts exactly one actual native provider turn'
        )
        assert record['after'] == record['before'], (
            'Stop before parameter choice removes the unfinished alias and preserves existing rows'
        )
        return
    assert record['wire']['atom-adp-alias']['success'], (
        'The shown native add_relations call chooses an atom-site adp_iso '
        'without control_unavailable'
    )
    assert record['after'] == [
        *record['before'],
        {'id': ALIAS, 'parameter': record['canonical_name']},
    ], 'The added alias targets the selector canonical atom-site name rather than its default'
    selector = record['selector']
    index = selector['names'].index(record['canonical_name'])
    assert selector['index'] == index and selector['shown'][index] != record['canonical_name'], (
        'The exercised selector separates canonical names from its displayed parameter labels'
    )
    control = 'alias.parameter.' + str(len(record['before']))
    pressed = [
        f
        for f in record['choices']
        if f['kind'] == 'real_delegate_pressed' and f['control'] == control
    ]
    activated = [
        f
        for f in record['choices']
        if f['kind'] == 'original_choice_activated' and f['control'] == control
    ]
    assert len(pressed) == len(activated) == 1, (
        'One real popup delegate press and activation choose the requested alias parameter once'
    )
    assert (
        pressed[0]['ownerCurrent']
        and pressed[0]['sameWindow']
        and pressed[0]['popupOpened']
        and pressed[0]['rowVisible']
        and activated[0]['index'] == index
        and activated[0]['offered'] == selector['shown'][index]
    ), 'The native tool physically chooses the actual offered display row for the canonical target'
