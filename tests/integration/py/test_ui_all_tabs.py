"""Exercise complete declared-tab coverage and the existing GUI timing bound."""

import copy
import json
import operator
import os
import shlex
import shutil
import subprocess
import sys

import pytest

from tests.fixtures.ui_responsiveness.tab_inventory import (
    ROOT,
    SCENARIO,
    array,
    declared_tabs,
    scenario_steps,
    source,
    tab_targets,
)
from tests.integration.py.ui_responsiveness_oracle import timing
from tests.integration.py.ui_tab_witnesses import tab_actions

INVENTORY = declared_tabs()
TARGETS = tab_targets(INVENTORY)
STEPS = [target['name'] for target in TARGETS]


def tab_trace(inventory=INVENTORY, *, blocked=False, excluded=False):
    targets = tab_targets(inventory)
    end = len(targets) * 10 + 210
    trace = [
        {
            'event': 'clock',
            't_ms': -2,
            'clock': 'monotonic',
            'unit': 'ms',
            'tick_ms': 10,
            'gui_thread': 'gui',
        },
        {'event': 'input', 't_ms': -1, 'identity': 'independent-scan'},
        {
            'event': 'tab-inventory',
            't_ms': -1,
            'pages': copy.deepcopy(inventory),
            'witness': 'qml-tab-bars',
            'thread': 'gui',
        },
        {'event': 'begin', 't_ms': 0, 'scenario': SCENARIO},
        {'event': 'complete', 't_ms': end, 'scenario': SCENARIO},
    ]
    chosen = {}
    for index, target in enumerate(targets):
        page = target['page']
        if page not in chosen:
            chosen[page] = {
                field: inventory[page][area][0]['key'] if inventory[page][area] else ''
                for area, field in [('main', 'tab'), ('sidebar', 'sidebar_tab')]
            }
        selected_object = ''
        if target['area'] != 'page':
            field = 'tab' if target['area'] == 'main' else 'sidebar_tab'
            chosen[page][field] = target['key']
            selected_object = target['object']
        t = index * 10
        token = 'native-' + str(index)
        state = {
            'event': 'state',
            't_ms': t + 2,
            'request': index,
            'page': page,
            'input': 'independent-scan',
            'transition': token,
            'thread': 'gui',
            'selected_object': selected_object,
            **chosen[page],
        }
        trace += [
            {
                'event': 'action',
                't_ms': t + 1,
                'request': index,
                'name': target['name'],
                'thread': 'gui',
            },
            state,
            {'event': 'step', 't_ms': t + 5, 'request': index, 'name': target['name']},
            {
                'event': 'transition-publication',
                't_ms': t + 3,
                'transition': token,
                'input': 'independent-scan',
                'frame': index,
            },
            {
                'event': 'render',
                't_ms': t + 4,
                'frame': index,
                'transitions': [token],
                'displayed': dict(state),
            },
        ]
    if blocked or excluded:
        first, last = len(targets) * 10 + 10, end
        trace += [
            {'event': 'tick', 't_ms': t, 'thread': 'gui'}
            for t in range(0, end + 1, 10)
            if t <= first or t >= last
        ]
        start, stop = first + 1, last - 1
        if blocked:
            trace += [
                {'event': 'block-begin', 't_ms': start, 'thread': 'gui'},
                {'event': 'block-end', 't_ms': stop, 'thread': 'gui'},
            ]
        else:
            for event in ('tool-begin', 'measurement-enter', 'measurement-leave', 'tool-end'):
                trace.append({
                    'event': event,
                    't_ms': start if event.endswith(('begin', 'enter')) else stop,
                    'id': 'capture',
                    'callback': 'QQuickWindow::grabWindow',
                    'thread': 'gui',
                })
    else:
        trace += [{'event': 'tick', 't_ms': t, 'thread': 'gui'} for t in range(0, end + 1, 10)]
    return sorted(trace, key=operator.itemgetter('t_ms'))


def test_declared_inventory_includes_every_owner_page_and_both_tab_areas():
    assert {
        'home',
        'project',
        'structure',
        'experiment',
        'analysis',
        'report',
    } <= INVENTORY.keys(), 'The owner requires all six workflow pages, including tabless Home'
    assert scenario_steps()[SCENARIO] == STEPS, (
        'The runner must derive its tab steps from the same complete app declarations'
    )
    trace = tab_trace()
    tab_actions(trace, INVENTORY)
    timing(trace, SCENARIO, STEPS)
    requests = {
        r['request']
        for r in trace
        if r['event'] == 'action' and r['name'] in {'page-project', 'tab-main-project-description'}
    }
    states = [r for r in trace if r['event'] == 'state' and r['request'] in requests]
    publications = [
        r
        for r in trace
        if r['event'] == 'transition-publication'
        and r['transition'] in {state['transition'] for state in states}
    ]
    early, later = publications
    old_frame = early['frame']
    early['frame'] = later['frame']
    rendered = next(r for r in trace if r['event'] == 'render' and r['frame'] == later['frame'])
    rendered['transitions'].append(early['transition'])
    trace = [r for r in trace if not (r['event'] == 'render' and r['frame'] == old_frame)]
    tab_actions(trace, INVENTORY)


@pytest.mark.parametrize('target', TARGETS, ids=[target['name'] for target in TARGETS])
def test_no_declared_page_main_tab_or_sidebar_tab_can_be_skipped(target):
    trace = tab_trace()
    request = next(
        r['request'] for r in trace if r['event'] == 'action' and r['name'] == target['name']
    )
    trace = [r for r in trace if r.get('request') != request]
    with pytest.raises(AssertionError, match='every requested action'):
        tab_actions(trace, INVENTORY)


@pytest.mark.parametrize('area', ['main', 'sidebar'])
@pytest.mark.parametrize(
    'escape',
    [
        'wrong-selection',
        'wrong-page',
        'wrong-object',
        'wrong-render',
        'late-render',
        'early-action',
    ],
)
def test_tab_labels_require_actual_selected_and_rendered_native_state(area, escape):
    trace = tab_trace()
    target = next(t for t in TARGETS if t['area'] == area and t['page'] == 'analysis')
    action = next(r for r in trace if r['event'] == 'action' and r['name'] == target['name'])
    state = next(r for r in trace if r['event'] == 'state' and r['request'] == action['request'])
    frame = next(r for r in trace if r['event'] == 'render' and r['frame'] == action['request'])
    field = 'tab' if area == 'main' else 'sidebar_tab'
    if escape == 'wrong-selection':
        state[field] = 'unselected'
        frame['displayed'][field] = 'unselected'
    elif escape == 'wrong-page':
        state['page'] = frame['displayed']['page'] = 'experiment'
    elif escape == 'wrong-object':
        state['selected_object'] = frame['displayed']['selected_object'] = 'another-button'
    elif escape == 'wrong-render':
        frame['displayed'][field] = 'another-tab'
    elif escape == 'late-render':
        frame['t_ms'] = 99999
    else:
        action['t_ms'] = -10
    with pytest.raises(AssertionError):
        tab_actions(trace, INVENTORY)


@pytest.mark.parametrize('escape', ['missing', 'subset', 'foreign', 'label-only', 'worker'])
def test_runtime_inventory_cannot_replace_or_shrink_the_declaration_reference(escape):
    trace = tab_trace()
    inventory = next(r for r in trace if r['event'] == 'tab-inventory')
    if escape == 'missing':
        trace.remove(inventory)
    elif escape == 'subset':
        inventory['pages']['analysis']['sidebar'].pop()
    elif escape == 'foreign':
        inventory['pages']['analysis']['main'].append({'key': 'fake', 'object': 'fake'})
    elif escape == 'label-only':
        inventory['witness'] = 'driver-labels'
    else:
        inventory['thread'] = 'worker'
    with pytest.raises(AssertionError):
        tab_actions(trace, INVENTORY)


def qml_copy(destination):
    for relative in ['Main.qml', 'Components/MainView.qml', 'Components/WorkflowPage.qml']:
        target = destination / 'app/qml' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / 'app/qml' / relative, target)
    shutil.copytree(ROOT / 'app/qml/Pages', destination / 'app/qml/Pages')
    return destination


def append_literal(path, name, entry):
    text = source(path)
    literal = array(text, name)
    path.write_text(text.replace(literal, literal[:-1] + ', ' + entry + ']', 1))


@pytest.mark.parametrize('addition', ['main', 'sidebar', 'page'])
def test_new_declarations_are_picked_up_and_invalidate_old_coverage(tmp_path, addition):
    root = qml_copy(tmp_path)
    qml = root / 'app/qml'
    if addition == 'main':
        append_literal(qml / 'Components/MainView.qml', 'allKeys', '"newview"')
        append_literal(
            qml / 'Components/MainView.qml',
            'tabs',
            'IconTabButton { objectName: "mainArea.tab.newview" }',
        )
        append_literal(qml / 'Pages/Analysis/AnalysisPage.qml', 'tabKeys', '"newview"')
        expected = 'tab-main-analysis-newview'
    elif addition == 'sidebar':
        append_literal(
            qml / 'Components/WorkflowPage.qml',
            'tabs',
            'EaElements.TabButton { objectName: "sideBar.tab.newside" }',
        )
        expected = 'tab-sidebar-report-newside'
    else:
        append_literal(qml / 'Main.qml', 'contentArea', 'New {}')
        (qml / 'Pages/New').mkdir()
        (qml / 'Pages/New/New.qml').write_text(
            'WorkflowPage { pageName: "new"; mainTabs: ['
            'IconTabButton { objectName: "mainArea.new.tab.summary" } ] }'
        )
        expected = 'tab-sidebar-new-settings'
    inventory = declared_tabs(root)
    assert expected in [target['name'] for target in tab_targets(inventory)], (
        'A newly declared page or tab must enter the watchdog action inventory automatically'
    )
    with pytest.raises(AssertionError, match='every source declaration'):
        tab_actions(tab_trace(), inventory)
    tab_actions(tab_trace(inventory), inventory)


@pytest.mark.parametrize('escape', ['indirect', 'duplicate', 'unnamed', 'unassigned', 'local-bar'])
def test_unreadable_or_ambiguous_tab_declarations_fail_closed(tmp_path, escape):
    root = qml_copy(tmp_path)
    path = root / 'app/qml/Components/WorkflowPage.qml'
    if escape == 'indirect':
        text = source(path)
        path.write_text(text.replace(array(text, 'tabs'), 'someOtherTabs', 1))
    elif escape == 'duplicate':
        append_literal(path, 'tabs', 'TabButton { objectName: "sideBar.tab.basic" }')
    elif escape == 'unnamed':
        append_literal(path, 'tabs', 'TabButton { text: "Future" }')
    elif escape == 'unassigned':
        shared = root / 'app/qml/Components/MainView.qml'
        append_literal(shared, 'allKeys', '"unassigned"')
        append_literal(shared, 'tabs', 'TabButton { objectName: "mainArea.tab.unassigned" }')
    else:
        page = root / 'app/qml/Pages/Project/ProjectPage.qml'
        page.write_text(page.read_text() + '\nSideBar { tabs: [] }')
    with pytest.raises(ValueError, match=r'array|Duplicate|stable native|mounted page|adapter'):
        declared_tabs(root)


def test_tab_scenario_keeps_measurement_exclusions_and_refuses_a_real_gui_block():
    captured = tab_trace(excluded=True)
    tab_actions(captured, INVENTORY)
    timing(captured, SCENARIO, STEPS)
    blocked = tab_trace(blocked=True)
    tab_actions(blocked, INVENTORY)
    with pytest.raises(AssertionError, match='U8 permits no counted gap'):
        timing(blocked, SCENARIO, STEPS, control=True)


@pytest.mark.parametrize('blocked', [False, True], ids=['within-bound', 'blocking-control'])
def test_production_checker_judges_the_complete_declared_tab_scenario(tmp_path, blocked):
    trace = tmp_path / 'trace.jsonl'
    trace.write_text(''.join(json.dumps(row) + '\n' for row in tab_trace(blocked=blocked)))
    command = [
        sys.executable,
        str(ROOT / 'tools/ci/gui_watchdog.py'),
        '--trace',
        str(trace),
        '--scenario',
        SCENARIO,
    ]
    if blocked:
        command.append('--control')
    result = subprocess.run(command, capture_output=True, text=True, timeout=5, check=False)
    assert result.returncode == (1 if blocked else 0), (
        'The production checker must judge every declared-tab action using the existing bound'
    )
    if blocked:
        assert (
            f'gui_watchdog: {SCENARIO}: the control block was seen' in result.stdout.splitlines()
        ), 'A parser refusal cannot substitute for observing the deliberate GUI block'


@pytest.mark.parametrize('nightly', [False, True], ids=['reduced-pr', 'full-nightly'])
def test_ci_watchdog_judges_every_produced_tab_run_and_control(tmp_path, nightly):
    root = qml_copy(tmp_path)
    scripts = root / 'tools/ci'
    scripts.mkdir(parents=True)
    shutil.copyfile(ROOT / 'tools/ci/app-watchdog.sh', scripts / 'app-watchdog.sh')
    (scripts / 'app-platform.sh').write_text('app_capture_platform() { :; }\n')
    (scripts / 'gui_watchdog.py').write_text(
        'import json, pathlib, sys\n'
        'args=sys.argv[1:]; scenario=args[args.index("--scenario")+1]\n'
        'control="--control" in args\n'
        'with pathlib.Path("judged.jsonl").open("a") as out: '
        'out.write(json.dumps([scenario, control])+"\\n")\n'
        'if control: print(f"gui_watchdog: {scenario}: the control block was seen")\n'
        'sys.exit(1 if control else 0)\n'
    )
    binary = root / 'build/app/app/edi_app'
    binary.parent.mkdir(parents=True)
    binary.write_text('#!/bin/sh\nexit 0\n')
    binary.chmod(0o755)
    fixtures = root / 'tests/fixtures'
    (fixtures / 'ui_responsiveness').mkdir(parents=True)
    (fixtures / 'joint_series').mkdir()
    for folder in [
        root / 'tests',
        fixtures,
        fixtures / 'ui_responsiveness',
        fixtures / 'joint_series',
    ]:
        (folder / '__init__.py').touch()
    for name in ('tab_inventory.py', 'contract.json'):
        shutil.copyfile(
            ROOT / 'tests/fixtures/ui_responsiveness' / name, fixtures / 'ui_responsiveness' / name
        )
    (fixtures / 'ui_responsiveness/generate.py').write_text('print("independent-input")\n')
    (fixtures / 'joint_series/ncaf.py').write_text('def prepare(*args, **kwargs): pass\n')
    (fixtures / 'ui_responsiveness/run.py').write_text(
        'import json, pathlib, sys\n'
        'from tests.fixtures.ui_responsiveness.tab_inventory import scenario_steps\n'
        'output=pathlib.Path(sys.argv[sys.argv.index("--output")+1]); output.mkdir(parents=True)\n'
        'runs={}\n'
        'for scenario in scenario_steps():\n'
        ' for suffix in ("", "-control"):\n'
        '  key=scenario+suffix; folder=output/key; folder.mkdir()\n'
        '  (folder/"trace.jsonl").write_text("orchestration stub\\n")\n'
        '  runs[key]={"path": key+"/trace.jsonl"}\n'
        '(output/"manifest.json").write_text(json.dumps({"runs": runs}))\n'
    )
    executable = root / 'bin/python'
    executable.parent.mkdir()
    executable.write_text('#!/bin/sh\nexec ' + shlex.quote(sys.executable) + ' "$@"\n')
    executable.chmod(0o755)
    environment = {
        **os.environ,
        'PATH': str(executable.parent) + os.pathsep + os.environ['PATH'],
        'PYTHONPATH': str(root),
    }
    environment.pop('EDI_WATCHDOG_REPORT', None)
    environment.pop('EDI_WATCHDOG_ARCHIVE', None)
    if nightly:
        environment['EDI_WATCHDOG_ARCHIVE'] = str(root / 'external-owner.zip')
    result = subprocess.run(
        ['bash', str(scripts / 'app-watchdog.sh')],
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, (
        'The watchdog orchestration stub must complete before checking scenario coverage: '
        + result.stderr
    )
    judged = [tuple(json.loads(line)) for line in (root / 'judged.jsonl').read_text().splitlines()]
    expected = {(name, control) for name in scenario_steps() for control in (False, True)}
    assert set(judged) == expected and len(judged) == len(expected), (
        'PR and nightly CI must actually judge every produced scenario and blocking control'
    )
