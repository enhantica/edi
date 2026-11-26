"""Finished assistant steps between replies occupy a single expandable line."""

import json
import re

from tests.system.py import test_e11_t5_dev_native_integration as native

main_actor = native.main_actor

FIRST_REPLY = 'I will check the saved project and its parameters.'
OBSERVE = (
    '(function(action){'
    'const list=testAppObjects.snapshot().find(x=>x.objectName==="assistant.messages");'
    'if(!list||!list.visible)return null;'
    'const items=[list.contentItem], replies=[], buttons=[];'
    'for(let i=0;i<items.length;++i){'
    'const item=items[i];if(!item.visible)continue;'
    'items.push(...item.children);'
    'const y=item.mapToItem(list,0,item.height/2).y;'
    'if(y<0||y>=list.height||item.width<=0||item.height<=0)continue;'
    'if(typeof item.text==="string"&&typeof item.checked!=="boolean")'
    'replies.push({text:item.text,y});'
    'if(item.enabled&&typeof item.click==="function"'
    '&&(item.checkable===true||item.objectName==="assistant.steps.toggle"))'
    'buttons.push({item,y});'
    '}'
    'const first=replies.find(row=>row.text.includes(FIRST));'
    'const last=replies.find(row=>row.text.includes(LAST));'
    'if(!first||!last)return null;'
    'const steps=buttons.filter(row=>first.y<row.y&&row.y<last.y).sort((a,b)=>a.y-b.y);'
    'if(action&&steps.length===1)steps[0].item.click();'
    'return steps.map(row=>({caption:row.item.text, y:row.y}));'
    '})'
)


def step_rows(actor, *, expand=False):
    expression = OBSERVE.replace('FIRST', json.dumps(FIRST_REPLY)).replace(
        'LAST', json.dumps(native.FINAL)
    )
    return native.qml(actor, expression + ('(true)' if expand else '(false)'))


def test_different_finished_steps_share_one_expandable_row(main_actor, tmp_path):
    actor = main_actor([
        [
            {'message_stream': {'chunk': FIRST_REPLY, 'count': 1}},
            native.tool_call('inspect_project', 'inspect-saved-project'),
            native.tool_call('list_parameters', 'list-saved-parameters'),
        ]
    ])
    root = native.copied_estimate_project(tmp_path, overrides=False)
    assert actor.command('open', path=str(root))['reply']['opened'], (
        'Open a saved project with parameters before observing the finished assistant steps'
    )
    actor.until(lambda row: not row['ui']['project']['calculating'])
    actor.connect()
    actor.request('Inspect this project and list its parameters.')
    actor.until(lambda row: len(actor.responses()) == 2 and row['ui']['state'] == 'idle')
    assert all(row['result']['success'] for row in actor.responses()), (
        'The transcript must contain two different successful steps between the assistant replies'
    )
    rows = step_rows(actor)
    assert rows is not None, 'Both assistant replies must be rendered in the observed transcript'
    assert len(rows) == 1 and re.search(r'\b2\s+steps\b', rows[0]['caption'], re.IGNORECASE), (
        'The two finished steps must share one labelled disclosure row that gives their count'
    )
    step_rows(actor, expand=True)
    actor.until(lambda _: len(step_rows(actor) or ()) == 3)
    rows = step_rows(actor)
    assert [row['caption'] for row in rows[1:]] == [
        'Inspect the current project',
        'Inspect model parameters',
    ], 'Opening the summary must expose both original expandable steps in their execution order'
