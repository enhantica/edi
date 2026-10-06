"""Effective consumers for the owner's committed 2026-10-06 scan adjustments."""

import re
from itertools import starmap

import pytest

from tests.integration.py.test_scan_app_contract import (
    block,
    evaluate,
    item,
    property_value,
    source,
    spans,
)


def button_states(text):
    start, reset = item(text, 'fitting.start'), item(text, 'fitting.reset')
    result = evaluate(
        '[null,{running:false,available:true,continuable:false,canReset:false},'
        '{running:false,available:true,continuable:true,canReset:true},'
        '{running:false,available:false,continuable:false,canReset:true},'
        '{running:true,available:false,continuable:true,canReset:false}].map(fit=>{'
        'group.fit=fit;return ['
        + ','.join(
            starmap(property_value, [(start, 'text'), (start, 'enabled'), (reset, 'enabled')])
        )
        + '];})',
        'const qsTr=s=>s;const group={fit:null};',
    )
    assert result == [
        ['Start fitting', False, False],
        ['Start fitting', True, False],
        ['Continue fitting', True, True],
        ['Start fitting', False, True],
        ['Stop fitting', True, False],
    ], 'Fit buttons: no, partial, complete and running fits determine labels and availability'
    position = text.index('objectName: "fitting.reset"')
    parents = sorted(
        ((a, b) for a, b in spans(text) if a < position < b), key=lambda span: span[1] - span[0]
    )
    row = text[parents[1][0] : parents[1][1]]
    reset_visibility = evaluate(
        '[null,{scan:false},{scan:true}].map(project=>{Session.project=project;'
        'buttons.scan=('
        + property_value(row, 'scan')
        + ');return ('
        + property_value(reset, 'visible')
        + ');})',
        'const Session={project:null},buttons={scan:false};',
    )
    assert reset_visibility == [False, False, True], (
        'Reset fits: the actual row shows its reset action only for a declared scan project'
    )
    calls = evaluate(
        '(()=>{(' + property_value(reset, 'onClicked') + ');return calls;})()',
        'let calls=[];const group={fit:{reset:()=>calls.push("reset")}};',
    )
    assert calls == ['reset'], 'Reset fits: the displayed button clears its own fit model'
    positions = [
        text.index('objectName: "fitting.' + name + '"') for name in ('start', 'reset', 'follow')
    ]
    assert positions == sorted(positions), 'Reset fits: its button sits between Fit and Follow'


def test_fit_and_reset_buttons_follow_effective_fit_state():
    button_states(source('qml/Pages/Analysis/FittingGroup.qml'))


def progress_edge(text):
    area = item(text, 'statusBar.fit')
    progress = item(area, 'statusBar.fit.progress')
    assert property_value(area, 'anchors.right') == 'parent.right', (
        'Status progress: the fit area is anchored at the status bar right edge'
    )
    children = [(a, b) for a, b in spans(area) if a > 0]
    direct = [(a, b) for a, b in children if not any(c < a < b < d for c, d in children)]
    assert direct and area[direct[-1][0] : direct[-1][1]] == progress, (
        'Status progress: the progress bar is the last displayed child of the right-anchored row'
    )


def test_progress_remains_at_the_status_bar_far_right():
    progress_edge(source('qml/Components/StatusBar.qml'))


def steady_marker(text):
    marker = item(text, 'evolution.current')
    observed = evaluate(
        '[17,17,17,18].map((index,i)=>{chart.project.currentExperimentIndex=index;'
        'chart.evolution.count=[162,0,1,162][i];chart.project.calculating=i===1;'
        'const at=('
        + property_value(marker, 'at')
        + ');return [at,('
        + property_value(marker, 'visible')
        + '),('
        + property_value(marker, 'x')
        + ')];})',
        'const chart={project:{currentExperimentIndex:17,calculating:false},'
        'evolution:{count:162,xMode:0,datasetX:index=>137.25+index}};'
        'const axisX={min:120,max:220},plot={width:500};',
    )
    assert observed == [[154.25, True, 171]] * 3 + [[155.25, True, 176]], (
        'Evolution marker: the shown dataset stays visible at its own x while results rebuild; '
        'only a changed selection moves it'
    )


def test_evolution_marker_survives_point_rebuild_and_pending_projection():
    steady_marker(source('qml/Components/EvolutionChart.qml'))


def gesture_results(text):
    pointer = item(text, 'evolution.pointer')
    functions = ''
    for name in ('xAt', 'yAt', 'moved'):
        match = re.search(r'function ' + name + r'\((.*?)\)(?:\s*:\s*\w+)?\s*\{', pointer)
        assert match, 'Evolution gestures: the active pointer resolves its coordinate operations'
        arguments = re.sub(r':\s*\w+', '', match.group(1))
        functions += (
            'function ' + name + '(' + arguments + ')' + block(pointer[match.end() - 1 :], '{')
        )
    context = (
        'const Qt={LeftButton:1,RightButton:2};const width=200,height=100;'
        'const axisX={min:2,max:12},axisY={min:10,max:30};const chart={em:10,zoom:[]};'
        'let pressX=0,pressY=0;' + functions
    )
    return evaluate(
        '(()=>{let results=[];('
        + property_value(pointer, 'onPressed')
        + ')({x:40,y:25});('
        + property_value(pointer, 'onReleased')
        + ')({x:160,y:75,button:1});'
        'results.push([...chart.zoom]);('
        + property_value(pointer, 'onReleased')
        + ')({x:160,y:75,button:2});'
        'results.push([...chart.zoom]);'
        'for(const delta of [120,-120,0]){chart.zoom=[];('
        + property_value(pointer, 'onWheel')
        + ')({x:40,y:25,angleDelta:{y:delta}});'
        'results.push([...chart.zoom]);}return results;})()',
        context,
    )


def zoom_consumers(text):
    assert gesture_results(text) == [
        [4, 10, 15, 25],
        [],
        [2.4, 10.4, 10, 30],
        [1.5, 14, 10, 30],
        [],
    ], (
        'Evolution gestures: box drag zooms both axes, right click resets, and mouse/touchpad '
        'wheel zooms around its pointer as the pattern chart does'
    )
    bindings = []
    for match in re.finditer(r'(?m)^\s*target:\s*axis[XY]\s*$', text):
        a, b = min(
            ((a, b) for a, b in spans(text) if a < match.start() < b),
            key=lambda span: span[1] - span[0],
        )
        bindings.append(text[a:b])
    assert len(bindings) == 4, (
        'Evolution zoom: each displayed axis bound receives the gesture range'
    )
    for binding in bindings:
        target, prop = property_value(binding, 'target'), property_value(binding, 'property')
        index = {
            ('axisX', '"min"'): 0,
            ('axisX', '"max"'): 1,
            ('axisY', '"min"'): 2,
            ('axisY', '"max"'): 3,
        }[target, prop]
        states = evaluate(
            '[[],[4,10,15,25],[-3,17,-0.5,93]].map(zoom=>{chart.zoom=zoom;return [('
            + property_value(binding, 'when')
            + '),('
            + property_value(binding, 'value')
            + ')];})',
            'const chart={zoom:[]};',
        )
        assert not states[0][0] and states[1:] == [
            [True, [4, 10, 15, 25][index]],
            [True, [-3, 17, -0.5, 93][index]],
        ], (
            'Evolution zoom: its effective axis binding follows changing gesture bounds '
            'and releases the data bounds on reset'
        )


def test_evolution_gestures_change_the_displayed_axes_and_reset():
    zoom_consumers(source('qml/Components/EvolutionChart.qml'))


def repeat_buttons(text):
    context = (
        'let selected=[];const row={blockIndex:2,blockActivated:i=>selected.push(i)};'
        'const selector={count:5};'
    )
    step = block(text, 'function step(')
    context += 'row.step=' + step + ';'
    controls = []
    for name in ('up', 'down'):
        position = text.index('id: ' + name)
        a, b = min(
            ((a, b) for a, b in spans(text) if a < position < b),
            key=lambda span: span[1] - span[0],
        )
        controls.append(text[a:b])
    for control, want in zip(controls, (1, 3), strict=True):
        result = evaluate(
            '(()=>{selected=[];('
            + property_value(control, 'onClicked')
            + ');return [selected,('
            + property_value(control, 'autoRepeat')
            + ')];})()',
            context,
        )
        assert result == [[want], True], (
            'Dataset navigation: held previous/next buttons repeat their own '
            'bounded selection step'
        )


def test_previous_and_next_repeat_the_effective_selection_step():
    repeat_buttons(source('qml/Components/BlockSelector.qml'))


def shortened_names(text):
    shown = property_value(text, 'shown')
    limit = property_value(text, 'limit')
    rows = evaluate(
        '[0,3,15,16,162,100000].map(count=>{return (function()' + shown + ')();})',
        'const limit=' + limit + ';',
    )
    assert rows[0] == [] and rows[1] == [0, 1, 2], (
        'Project names: every name in a short list remains displayed in order'
    )
    for count, indices in zip((15, 16, 162, 100000), rows[2:], strict=True):
        assert 10 <= len(indices) <= 20 and indices[0] == 0 and indices[-1] == count - 1, (
            'Project names: a long list displays bounded first and last names'
        )
        if count > 20:
            assert indices.count(-1) == 1, (
                'Project names: the omitted middle has one ellipsis entry'
            )
    repeat = block(text, 'Repeater {')
    assert property_value(repeat, 'model') == 'names.shown', (
        'Project names: the actual displayed list consumes the shortened selection'
    )
    delegate = block(repeat, 'delegate: IconLine {')
    segments = evaluate(
        delegate.split('segments:', 1)[1].rstrip()[:-1].strip(),
        'const entry={modelData:-1};',
    )
    assert segments == [{'text': '…,'}], (
        'Project names: the displayed omitted middle reads as an ellipsis'
    )


def test_project_page_displays_bounded_names_and_the_middle_ellipsis():
    shortened_names(source('qml/Pages/Project/BlockNames.qml'))


@pytest.mark.parametrize(
    'channel',
    ['button', 'reset', 'progress', 'marker', 'wheel', 'drag', 'axis', 'repeat', 'names'],
)
def test_owner_observers_reject_live_disconnected_or_constant_consumers(channel):
    path, observer, old, new = {
        'button': (
            'qml/Pages/Analysis/FittingGroup.qml',
            button_states,
            'group.fit.continuable',
            'false',
        ),
        'reset': (
            'qml/Pages/Analysis/FittingGroup.qml',
            button_states,
            'onClicked: group.fit.reset()',
            'onClicked: 0',
        ),
        'progress': (
            'qml/Components/StatusBar.qml',
            progress_edge,
            'anchors.right: parent.right',
            'anchors.right: parent.left',
        ),
        'marker': (
            'qml/Components/EvolutionChart.qml',
            steady_marker,
            'visible: !isNaN(at)',
            'visible: chart.evolution.count > 0',
        ),
        'wheel': (
            'qml/Components/EvolutionChart.qml',
            zoom_consumers,
            'chart.zoom = [anchor',
            'unused = [anchor',
        ),
        'drag': (
            'qml/Components/EvolutionChart.qml',
            zoom_consumers,
            'else if (moved(mouse))',
            'else if (false)',
        ),
        'axis': (
            'qml/Components/EvolutionChart.qml',
            zoom_consumers,
            'value: chart.zoom.length === 4 ? chart.zoom[0] : 0',
            'value: 4',
        ),
        'repeat': (
            'qml/Components/BlockSelector.qml',
            repeat_buttons,
            'autoRepeat: true',
            'autoRepeat: false',
        ),
        'names': (
            'qml/Pages/Project/BlockNames.qml',
            shortened_names,
            'model: names.shown',
            'model: names.count',
        ),
    }[channel]
    good = source(path)
    observer(good)
    changed = good.replace(old, new)
    assert changed != good, (
        'Owner scan adjustments: each escape changes its actual effective consumer'
    )
    with pytest.raises(AssertionError):
        observer(changed)
