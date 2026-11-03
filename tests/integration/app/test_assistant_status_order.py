"""The actual hidden-chat status bar places native items, Fit, then AI."""

import json
import os
from pathlib import Path

import pytest

from tests.system.py import test_e11_t5_dev_native_integration as base

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope='module')
def status_geometry(tmp_path_factory):
    folder = tmp_path_factory.mktemp('original-status-order')
    binary = Path(
        os.environ.get(
            'EDI_ASSISTANT_UI_PROBE',
            ROOT / 'build/app/assistant-ui-probe/assistant_real_owner_probe',
        )
    )
    actor = base.MainActor(
        binary,
        folder,
        {
            'turns': [
                [
                    {
                        'research': {'query': 'Public reference', 'action': None, 'results': None},
                        'call_id': 'working-layout-reference',
                    }
                ]
            ],
            'final_gate': str(folder / 'release-final'),
        },
        False,
    )
    try:
        project = base.copied_estimate_project(folder)
        assert actor.command('open', path=str(project))['reply']['opened'], (
            'Status layout reaches the real ordinary project and existing Fit controls'
        )
        base.wait_positive_tab(actor, 'appBar.tab.project')
        actor.command('click', name='appBar.tab.project')
        actor.connect()
        actor.request('Read the public reference without changing science.')
        actor.until(lambda value: value['ui']['can_cancel'])
        actor.command('click', name='assistant.toggle')
        working = base.control_expression('statusBar.assistant.working')
        fit = base.control_expression('statusBar.fit')
        info = base.qml(
            actor,
            '(function(){const w='
            + working
            + ',f='
            + fit
            + ';if(!w||!f)return null;const a=w.parent,ap=a.mapToItem(contentItem,0,0),'
            'fp=f.mapToItem(contentItem,0,0);'
            'return {assistant:{x:ap.x,y:ap.y,width:a.width,height:a.height,visible:a.visible},'
            'fit:{x:fp.x,y:fp.y,width:f.width,height:f.height,visible:f.visible},'
            'items:testAppObjects.snapshot().filter(x=>Qt.isQtObject(x)&&x.visible&&'
            'typeof x.keyText==="string"&&x.Window.window===window&&'
            '/^statusBar\\.[^.]+$/.test(x.objectName)).map(x=>{'
            'const p=x.mapToItem(contentItem,0,0);return {id:x.objectName,x:p.x,width:x.width};}),'
            'sameParent:a.parent===f.parent};})()',
        )
        (actor.folder / 'statusbar-working-fit-geometry.json').write_text(
            json.dumps(info, indent=2) + '\n', encoding='utf-8'
        )
        return info
    finally:
        if actor.last['ui']['can_cancel']:
            actor.command('click', name='assistant.stopVisibleAction')
            actor.until(lambda value: not value['ui']['can_cancel'])
        actor.close()


def test_original_status_items_then_fit_then_ai_do_not_overlap(status_geometry):
    info = status_geometry
    assert (
        info and info['sameParent'] and info['assistant']['visible'] and info['fit']['visible']
    ), 'Working and original Fit groups are both actually visible in the same real status bar'
    assert info['items'] and all(
        item['x'] + item['width'] <= info['fit']['x'] for item in info['items']
    ), 'Every shown original status item precedes the Fit group without overlap'
    assert info['fit']['x'] + info['fit']['width'] <= info['assistant']['x'], (
        'The original Fit group precedes the AI working and Stop group without overlap'
    )
