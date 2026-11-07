# SPDX-License-Identifier: BSD-3-Clause
"""Compare delegated publication with the ordinary Save of its fitted state."""

import importlib.util
import re
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


def working_state(tmp_path, monkeypatch):
    sources = ROOT / 'tests/fixtures/online_sources'
    monkeypatch.setenv(
        'EDI_ONLINE_SOURCES',
        f'cod={(sources / "cod").as_uri()}/;'
        f'easydiffraction={(sources / "easydiffraction").as_uri()}/',
    )
    binary = ROOT / 'build/app/assistant-ui-probe/assistant_real_owner_probe'
    gate = tmp_path / 'finish-turn'
    actor = DRIVER.MainActor(binary, tmp_path, {'turns': [[]], 'final_gate': str(gate)}, True)
    try:
        actor.connect()
        actor.request('Inspect the current interface.')
        actor.until(lambda row: row['ui']['state'] == 'agent_active')
        samples = []
        for _ in range(3):
            state = DRIVER.qml(
                actor,
                """(function() {
                const items = contentItem.children;
                function find(item, name) {
                    if (item.objectName === name) return item;
                    for (let child of item.children || []) {
                        const hit = find(child, name); if (hit) return hit;
                    }
                    return null;
                }
                const indicator = find(contentItem, "statusBar.assistant.working");
                return indicator && indicator.visible && indicator.working &&
                       indicator.animating &&
                       indicator.text.length > 0;
            })()""",
            )
            samples.append(state)
        gate.touch()
        actor.command('refresh_usage')
        actor.until(lambda row: row['ui']['state'] == 'idle')
        return {'samples': samples, 'settled': actor.last['ui']['state'] == 'idle'}
    finally:
        actor.close()


def skill_state(tmp_path, monkeypatch):
    sources = ROOT / 'tests/fixtures/online_sources'
    monkeypatch.setenv(
        'EDI_ONLINE_SOURCES',
        f'cod={(sources / "cod").as_uri()}/;'
        f'easydiffraction={(sources / "easydiffraction").as_uri()}/',
    )
    targets = {
        target
        for guide in (ROOT / 'data/assistant/skills').glob('*/SKILL.md')
        for target in re.findall(r'\bui:([A-Za-z0-9_.-]+)', guide.read_text())
    }
    binary = ROOT / 'build/app/assistant-ui-probe/assistant_real_owner_probe'
    actor = DRIVER.MainActor(binary, tmp_path, {'turns': [[]]}, False)
    found = set()
    try:
        project = tmp_path / 'working'
        shutil.copytree(ROOT / 'docs/user/cli/pd-neut-cwl_lbco-hrpt/project', project)
        assert actor.command('open', path=str(project))['reply']['opened'], (
            'The GUI target replay must open an ordinary project with a structure'
        )
        actor.until(lambda row: not row['ui']['project']['calculating'])
        if DRIVER.qml(actor, 'assistantPanelShown'):
            actor.command('click', name='assistant.toggle')
        for tab, menu, web in [
            ('structure', 'structures.load', 'structures.load.web'),
            ('experiment', 'experiments.load', 'experiments.load.experimentWeb'),
        ]:
            actor.until(
                lambda row, tab=tab: any(
                    c['name'] == 'appBar.tab.' + tab
                    and c['visible']
                    and c['enabled']
                    and c['input_reachable']
                    for c in row['ui']['controls']
                ),
                seconds=5,
            )
            actor.command('click', name='appBar.tab.' + tab)
            if DRIVER.qml(actor, 'assistantPanelShown'):
                actor.command('click', name='assistant.toggle')
                actor.until(lambda _row: not DRIVER.qml(actor, 'assistantPanelVisible'))
            actor.until(
                lambda row, menu=menu: any(
                    c['name'] == menu and c['visible'] and c['enabled'] and c['input_reachable']
                    for c in row['ui']['controls']
                ),
                seconds=5,
            )
            actor.command('click', name=menu)
            found.update(c['name'] for c in actor.last['ui']['controls'])
            actor.until(
                lambda row, web=web: any(
                    c['name'] == web and c['visible'] and c['enabled'] and c['input_reachable']
                    for c in row['ui']['controls']
                ),
                seconds=5,
            )
            actor.command('click', name=web)
            found.update(c['name'] for c in actor.last['ui']['controls'])
            names = actor.command('object_names')['reply']['names']
            found.update(names)

            actor.command('manual_key', key='escape')
        return {'targets': targets, 'found': found}
    finally:
        actor.close()
