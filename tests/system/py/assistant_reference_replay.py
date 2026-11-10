# SPDX-License-Identifier: BSD-3-Clause
"""Compare delegated publication with the ordinary Save of its fitted state."""

import importlib.util
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DRIVER_PATHS = list((ROOT / 'tests/system/py').glob('test_*_dev_native_integration.py'))
assert len(DRIVER_PATHS) == 1, 'Recorded native replay requires one unambiguous offline driver'
DRIVER_PATH = DRIVER_PATHS[0]
SPEC = importlib.util.spec_from_file_location('recorded_app_driver', DRIVER_PATH)
DRIVER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DRIVER)


def science_files(folder):
    return {
        p.relative_to(folder).as_posix(): p.read_bytes()
        for directory in ['structures', 'experiments', 'analysis']
        for p in (folder / directory).rglob('*.edi')
    }


def saved_state(tmp_path, monkeypatch, shown):
    sources = ROOT / 'tests/fixtures/online_sources'
    monkeypatch.setenv(
        'EDI_ONLINE_SOURCES',
        f'cod={(sources / "cod").as_uri()}/;'
        f'easydiffraction={(sources / "easydiffraction").as_uri()}/',
    )
    project = tmp_path / 'working'
    shutil.copytree(ROOT / 'docs/user/cli/pd-neut-cwl_lbco-hrpt/project', project)
    binary = ROOT / 'build/app/assistant-ui-probe/assistant_real_owner_probe'
    actor = DRIVER.MainActor(binary, tmp_path, {'turns': [[]]}, shown)
    try:
        assert actor.command('open', path=str(project))['reply']['opened'], (
            'The independent LBCO project must open before the recorded turn'
        )
        actor.until(lambda row: not row['ui']['project']['calculating'])
        parameters = actor.last['ui']['project']['parameters']
        coefficient = next(p['path'] for p in parameters if p['category'] == 'peak')
        calls = [
            DRIVER.tool_call(
                'set_free', 'fix-coefficient', flags=[{'path': coefficient, 'free': False}]
            ),
            DRIVER.tool_call(
                'set_free', 'free-coefficient', flags=[{'path': coefficient, 'free': True}]
            ),
            DRIVER.tool_call('run_fit', 'fit-current-project'),
            DRIVER.tool_call('save_project', 'save-fitted-state', destination='current'),
        ]
        actor.configure_turns([calls])
        actor.connect()
        actor.until(lambda _row: DRIVER.qml(actor, 'Session.assistant.draftAdmissionReady'))
        actor.command(
            'evaluate',
            expression='Session.assistant.send("Fit the current project and save the result.")',
        )
        actor.until(
            lambda row: len(actor.responses()) == len(calls) and row['ui']['state'] == 'idle',
            seconds=30,
            visible_progress=shown,
        )
        replies = [DRIVER.native_result(reply) for reply in actor.responses()]
        delegated = science_files(project)
        ordinary = tmp_path / 'ordinary'
        saved = actor.command('save_project_as', path=str(ordinary), zip=False, copy=True)['reply']
        return {
            'replies': replies,
            'free': next(
                p for p in actor.last['ui']['project']['parameters'] if p['path'] == coefficient
            )['free'],
            'delegated': delegated,
            'ordinary': science_files(ordinary),
            'manual_saved': saved['saved'],
        }
    finally:
        actor.close()


def relation_state(tmp_path, monkeypatch, shown):
    sources = ROOT / 'tests/fixtures/online_sources'
    monkeypatch.setenv(
        'EDI_ONLINE_SOURCES',
        f'cod={(sources / "cod").as_uri()}/;'
        f'easydiffraction={(sources / "easydiffraction").as_uri()}/',
    )
    project = tmp_path / 'working'
    shutil.copytree(ROOT / 'docs/user/cli/pd-neut-cwl_lbco-hrpt/project', project)
    binary = ROOT / 'build/app/assistant-ui-probe/assistant_real_owner_probe'
    actor = DRIVER.MainActor(binary, tmp_path, {'turns': [[]]}, shown)
    try:
        assert actor.command('open', path=str(project))['reply']['opened'], (
            'The shared-site reference project must open'
        )
        actor.until(lambda row: not row['ui']['project']['calculating'])
        actor.connect()
        expression = 'biso_La = biso_Ba'
        seed = r"""(function() {
            const rows = Session.project.analysis.constraints;
            while (rows.count) rows.remove(0);
            const table = Session.project.parameters;
            const values = {};
            for (let row = 0; row < table.count; ++row) {
                const parameter = table.item(row, "parameter");
                if (!parameter || !parameter.path.endsWith(".adp_iso")) continue;
                if (parameter.rowLabel === "La" || parameter.rowLabel === "Ba") {
                    parameter.free = false;
                    parameter.value = parameter.rowLabel === "La" ? 1.25 : 2.75;
                    values[parameter.rowLabel] = parameter.value;
                }
            }
            return values;
        })()"""
        initial = DRIVER.qml(actor, seed)
        actor.until(lambda row: not row['ui']['project']['calculating'])
        manual = DRIVER.qml(
            actor,
            """(function() {
            const rows = Session.project.analysis.constraints;
            while (rows.count) rows.remove(0);
            rows.append();
            return rows.setText(0, "id", "shared_site") &&
                   rows.setText(0, "expression", "biso_La = biso_Ba");
        })()""",
        )
        assert manual, 'The ordinary Relations controls must accept the reference equality'
        DRIVER.qml(
            actor,
            r"""(function() {
            const table = Session.project.parameters;
            for (let row = 0; row < table.count; ++row) {
                const parameter = table.item(row, "parameter");
                if (parameter && parameter.rowLabel === "Ba" &&
                    parameter.path.endsWith(".adp_iso")) {
                    parameter.value = 2.75;
                    return parameter.value;
                }
            }
            return null;
        })()""",
        )
        DRIVER.qml(actor, '(function(){Session.project.fit.start();return true;})()')
        actor.until(
            lambda row: (
                not row['ui']['project']['calculating']
                and not DRIVER.qml(actor, 'Session.project.fit.running')
            )
        )
        manual_fit = DRIVER.qml(actor, 'Session.project.fit.canUndo')
        reference = actor.last['ui']['project']['constraints']
        manual_values = {
            p['row_label']: p['value']
            for p in actor.last['ui']['project']['parameters']
            if p['field'] == 'adp_iso'
        }
        DRIVER.qml(actor, seed)
        actor.until(lambda row: not row['ui']['project']['calculating'])
        actor.configure_turns([
            [
                DRIVER.tool_call(
                    'add_relations',
                    'share-site',
                    aliases=[],
                    constraints=[{'id': 'shared_site', 'expression': expression, 'enabled': True}],
                ),
                DRIVER.tool_call('run_fit', 'fit-shared-site'),
            ]
        ])
        actor.connect()
        actor.until(lambda _row: DRIVER.qml(actor, 'Session.assistant.draftAdmissionReady'))
        actor.command(
            'evaluate',
            expression='Session.assistant.send("Tie the shared-site displacements and fit.")',
        )
        actor.until(
            lambda row: len(actor.responses()) == 2 and row['ui']['state'] == 'idle',
            seconds=30,
            visible_progress=shown,
        )
        replies = [DRIVER.native_result(reply) for reply in actor.responses()]
        state = actor.last['ui']['project']
        values = {
            p['row_label']: p['value'] for p in state['parameters'] if p['field'] == 'adp_iso'
        }
        return {
            'replies': replies,
            'manual': reference,
            'initial': initial,
            'manual_values': manual_values,
            'manual_fit': manual_fit,
            'actual': state['constraints'],
            'values': values,
        }
    finally:
        actor.close()


FIND_ITEM = """function find(item, name) {
    if (item.objectName === name) return item;
    for (let child of item.children || []) {
        const hit = find(child, name); if (hit) return hit;
    }
    return null;
}"""


def recorder(actor, expression):
    return DRIVER.qml(
        actor,
        '(function() {'
        + FIND_ITEM
        + 'const rec = find(contentItem, "referenceIndicatorRecorder");'
        + expression
        + '})()',
    )


def working_state(tmp_path, monkeypatch, *, intermediate_fault=False, completion_fault=False):
    sources = ROOT / 'tests/fixtures/online_sources'
    monkeypatch.setenv(
        'EDI_ONLINE_SOURCES',
        f'cod={(sources / "cod").as_uri()}/;'
        f'easydiffraction={(sources / "easydiffraction").as_uri()}/',
    )
    project = tmp_path / 'working'
    shutil.copytree(ROOT / 'docs/user/cli/pd-neut-cwl_lbco-hrpt/project', project)
    binary = ROOT / 'build/app/assistant-ui-probe/assistant_real_owner_probe'
    finish = tmp_path / 'finish-turn'
    complete = tmp_path / 'complete-turn'
    gates = [tmp_path / ('call-' + str(index)) for index in range(3)]
    actor = DRIVER.MainActor(
        binary,
        tmp_path,
        {
            'turns': [[]],
            'final_gate': str(finish),
            'completion_gate': str(complete),
            'call_gates': list(map(str, gates)),
        },
        True,
    )
    try:
        assert actor.command('open', path=str(project))['reply']['opened'], (
            'The indicator turn must begin with the independent project fixture'
        )
        actor.until(lambda row: not row['ui']['project']['calculating'])
        coefficient = next(
            p['path'] for p in actor.last['ui']['project']['parameters'] if p['category'] == 'peak'
        )
        actor.configure_turns([
            [
                DRIVER.tool_call(
                    'set_free', 'indicator-action', flags=[{'path': coefficient, 'free': True}]
                ),
                DRIVER.tool_call('run_fit', 'indicator-native-fit'),
                DRIVER.tool_call('inspect_project', 'indicator-after-adoption'),
            ]
        ])
        source = (ROOT / 'tests/fixtures/assistant_reference/indicator.qml').read_text(
            encoding='utf-8'
        )
        installed = DRIVER.qml(
            actor,
            '(function() {'
            + FIND_ITEM
            + 'const rec=Qt.createQmlObject('
            + json.dumps(source)
            + ', contentItem, "indicator-reference");'
            + 'rec.indicator=find(contentItem,"statusBar.assistant.working");'
            + 'return Boolean(rec.indicator);})()',
        )
        assert installed, 'The temporal recorder must bind the actual rendered status indicator'
        actor.connect()
        actor.request('Free the selected coefficient, fit, then inspect the adopted project.')
        for index, phase in enumerate((
            'before-action',
            'between-action-and-fit',
            'after-adoption',
        )):
            actor.until(
                lambda _row, gate=gates[index]: Path(str(gate) + '.ready').exists(),
                seconds=30,
                visible_progress=True,
            )
            if intermediate_fault and index == 1:
                recorder(actor, 'rec.indicator.visible=false; return true;')
            recorder(actor, 'rec.sample(' + json.dumps(phase) + '); return true;')
            if intermediate_fault and index == 1:
                recorder(actor, 'rec.indicator.visible=true; return true;')
            gates[index].touch()
            actor.command('refresh_usage')
        actor.until(lambda _row: len(actor.responses()) == 3, seconds=30, visible_progress=True)
        recorder(actor, 'rec.sample("final-held"); return true;')
        adopted = DRIVER.native_result(actor.responses()[1]).get('adopted')
        finish.touch()
        actor.command('refresh_usage')
        actor.until(
            lambda row: (
                Path(str(complete) + '.ready').exists() and row['ui']['state'] == 'agent_active'
            )
        )
        if completion_fault:
            recorder(actor, 'rec.indicator.visible=false; return true;')
        recorder(actor, 'rec.sample("completion-held"); return true;')
        complete.touch()
        actor.command('refresh_usage')
        actor.until(lambda row: row['ui']['state'] == 'idle')
        recorder(actor, 'rec.sample("completion"); return true;')
        result = {
            'samples': recorder(actor, 'return rec.samples;'),
            'adopted': adopted,
            'overflow': recorder(actor, 'return rec.overflow;'),
            'settled': actor.last['ui']['state'] == 'idle',
        }
        (tmp_path / 'indicator-observations.json').write_text(json.dumps(result), encoding='utf-8')
        return result
    finally:
        actor.close()


def skill_reference():
    spec = importlib.util.spec_from_file_location(
        'authored_skill_routes', ROOT / 'tests/fixtures/assistant_reference/skills.py'
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def guide_item(actor, name, expression):
    return DRIVER.qml(
        actor,
        '(function(){const matches=testAppObjects.snapshot().filter(item => '
        'item.objectName==='
        + json.dumps(name)
        + ' && item.visible === true);'
        + 'const item=matches.length===1 ? matches[0] : null;return item ? ('
        + expression
        + ') : null;})()',
    )


def guide_click(actor, name, receipts):
    try:
        actor.until(
            lambda row: any(
                c['name'] == name and c['visible'] and c['enabled'] and c['input_reachable']
                for c in row['ui']['controls']
            ),
            seconds=3,
        )
    except AssertionError as error:
        receipts.append({'target': name, 'reachable': False})
        raise AssertionError('The documented skill step is not reachable: ' + name) from error
    before = guide_item(actor, name, '({visible:item.visible, enabled:item.enabled})')
    result = actor.command('click', name=name)
    assert result.get('ok', True), (
        'The reachable skill action must accept actual GUI input: ' + name
    )
    receipts.append({'target': name, 'reachable': True, 'before': before})


def skill_route_step(actor, position, target, receipts, *, disabled):
    if disabled and target == 'experiments.create':
        assert guide_item(actor, target, 'item.enabled') is True, (
            'The disabled-target control must begin with a real enabled object'
        )
        actor.command('ui_property', name=target, property='enabled', value=False)
        assert guide_item(actor, target, 'item.enabled') is False, (
            'The disabled-target control must disable the actual existing GUI object'
        )
    if position == 10:
        actor.until(lambda _row: guide_item(actor, target, 'item.visible && item.opened'))
        assert guide_item(actor, target, 'item.visible && item.opened'), (
            'The documented web route must open its actual source popup'
        )
        receipts.append({'target': target, 'reachable': True, 'opened': True})
    elif position == 13:
        actor.until(lambda _row: (guide_item(actor, target, 'item.count') or 0) > 0)
        assert guide_item(actor, target, 'item.visible && item.enabled'), (
            'The documented search must expose actual result rows'
        )
        receipts.append({
            'target': target,
            'reachable': True,
            'results': guide_item(actor, target, 'item.count'),
        })
    else:
        before = actor.command('inspect')['ui']['project']
        guide_click(actor, target, receipts)
        if position in {0, 6}:
            key = 'backgrounds' if position == 0 else 'structure_rows'
            actor.until(lambda row: len(row['ui']['project'][key]) > len(before[key]))
            receipts[-1]['created'] = key
        if position == 11:
            actor.command('manual_key', key='escape')


def skill_file_result(actor, kind, path):
    answered = actor.command('file_answer', path=str(path), physical=True)['reply']
    assert (
        answered.get('physical')
        and answered['answered']
        and (answered['selected_file'] == path.as_uri())
    ), 'The skill file route must physically accept the authored file in the ordinary chooser'
    if kind == 'structure':
        actor.until(lambda row: len(row['ui']['project']['structure_rows']) == 1)
        assert actor.last['ui']['project']['structure_rows'][0]['sites'] == 1, (
            'The structure-file skill step must load the authored single-site CIF'
        )
    else:
        actor.until(
            lambda row: any(
                bank['input_count'] == 3 for bank in row['ui']['project']['backgrounds']
            )
        )
        assert any(
            bank['input_first'][0] == [17.5, 31.25, 0.75]
            for bank in actor.last['ui']['project']['backgrounds']
        ), 'The file skill step must load the independently authored measured rows'


def skill_route(actor, plan, route, inputs, receipts, *, disabled):
    assert actor.command('create', name='Guide reference')['reply']['created'], (
        'Each skill route must start without objects from another route'
    )
    tab, positions, selected_input = skill_reference().ROUTES[route]
    if tab == 'experiment':
        # The current GUI requires a structure before it enables the Experiment page.
        # Seed that prerequisite through ordinary controls; leave experiments empty.
        guide_click(actor, 'appBar.tab.structure', receipts)
        guide_click(actor, 'structures.create', receipts)
        actor.until(lambda row: len(row['ui']['project']['structure_rows']) == 1)
    guide_click(actor, 'appBar.tab.' + tab, receipts)
    targets = [plan['targets'][position] for position in positions]
    for position, target in zip(positions, targets, strict=True):
        skill_route_step(actor, position, target, receipts, disabled=disabled)
    if selected_input:
        skill_file_result(actor, selected_input, inputs[selected_input])
    elif route.endswith('-web'):
        actor.command('manual_key', key='escape')
    return {'name': route, 'completed': True, 'targets': targets}


def skill_state(tmp_path, monkeypatch, *, guides=None, only_guide=None, disabled=False):
    reference = skill_reference()
    inventory = reference.inventory(guides or ROOT / 'data/assistant/skills')
    collection = tmp_path / 'collection'
    inputs = reference.build(collection)
    address = collection.as_uri() + '/'
    monkeypatch.setenv('EDI_ONLINE_SOURCES', 'cod=' + address + ';easydiffraction=' + address)
    binary = ROOT / 'build/app/assistant-ui-probe/assistant_real_owner_probe'
    results = {}
    for name, plan in inventory.items():
        if only_guide and name != only_guide:
            continue
        folder = tmp_path / name
        folder.mkdir()
        actor = DRIVER.MainActor(binary, folder, {'turns': [[]]}, False)
        receipts, workflows = [], []
        try:
            assert actor.command('create', name='Guide reference')['reply']['created'], (
                'Every skill GUI replay must start from an ordinary empty project'
            )
            if DRIVER._unique_input_control(actor.last, 'home.start') is not None:
                guide_click(actor, 'home.start', receipts)
                actor.until(lambda row: DRIVER._unique_input_control(row, 'home.start') is None)
            if DRIVER.qml(actor, 'assistantPanelShown'):
                guide_click(actor, 'assistant.toggle', receipts)
            guide_click(actor, 'assistant.toggle', receipts)
            actor.until(lambda _row, actor=actor: DRIVER.qml(actor, 'assistantPanelVisible'))
            assert guide_item(actor, 'assistant.popup', 'item.visible && item.opened'), (
                'The documented Show Assistant step must open its actual sidebar'
            )
            workflows.append({'name': 'show-assistant-before-asking', 'completed': True})
            guide_click(actor, 'assistant.toggle', receipts)
            actor.until(lambda _row, actor=actor: not DRIVER.qml(actor, 'assistantPanelVisible'))
            workflows.extend(
                skill_route(actor, plan, route, inputs, receipts, disabled=disabled)
                for route in plan['routes']
            )
            assert set(plan['targets']) <= {row['target'] for row in receipts}, (
                'Every annotated skill target must be reached in its documented ordered route'
            )
            results[name] = {'workflows': workflows, 'steps': receipts, 'source': plan['source']}
        finally:
            (folder / 'skill-step-observations.json').write_text(
                json.dumps({'skill': name, 'workflows': workflows, 'steps': receipts}),
                encoding='utf-8',
            )
            actor.close()
    assert results and (only_guide or set(results) == set(inventory)), (
        'Every discovered skill must complete a nonempty per-skill GUI replay'
    )
    return results
