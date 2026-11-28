"""Every bank consumer must project the same active phase set."""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from tests.fixtures.disabled_projection.project import ALIASES, PHASES, materialize
from tests.integration.app.test_assistant_misfit_workflow import replies
from tests.system.py import test_e11_t5_dev_native_integration as native

ROOT = Path(__file__).resolve().parents[3]
ACTIVE = 'obsidian'


def assistant_observations(binary, tmp_path, project):
    folder = tmp_path / 'actor'
    folder.mkdir()
    source = folder / 'project'
    shutil.copytree(project, source)
    make = native.tool_call
    calls = [
        make('inspect_project', 'context'),
        make('list_parameters', 'parameters'),
        make(
            'edit_relation',
            'rename',
            id='zz_unused',
            operation='alias_rename',
            value='zz_unused_edited',
        ),
        make(
            'edit_relation',
            'constraint',
            id='zz_visible_rule',
            operation='constraint_rename',
            value='zz_visible_rule_edited',
        ),
        make(
            'add_relations',
            'append',
            aliases=[{'id': 'visible_width', 'path': 'experiment.peak.broad_gauss_u'}],
            constraints=[],
        ),
        make('edit_relation', 'remove', id='zz_drop', operation='alias_remove'),
        make(
            'edit_relation',
            'remove_constraint',
            id='zy_drop_rule',
            operation='constraint_remove',
        ),
        make(
            'edit_relation',
            'hidden_target',
            id=ALIASES['saffron'],
            operation='alias_rename',
            value='escaped_hidden_row',
        ),
    ]
    actor = native.MainActor(binary, folder, {'turns': [calls]}, True)
    try:
        assert actor.command('open', path=str(source))['reply']['opened'], (
            'The native assistant opens the same independently authored projection input'
        )
        actor.until(lambda row: not row['ui']['project']['calculating'])

        def declarations():
            return native.qml(actor, 'Session.project.analysis.text.text')

        before = declarations()
        actor.connect()
        assert actor.last['ui']['show_actions'], 'The assistant runs through shown controls'
        native._watch_original_offered_choices(actor, 'disabled-phase-projection-choices')
        actor.request()
        actor.until(
            lambda row: len(actor.responses()) == len(calls) and row['ui']['state'] == 'idle',
            visible_progress=True,
        )
        after = actor.command('inspect')['ui']['project']
        wire = replies(actor)
        choices = native.qml(
            actor,
            '(function(){const o='
            + native._scene_control_expression('disabled-phase-projection-choices')
            + ';o.scan();return o.facts;})()',
        )
        return before, declarations(), {'wire': wire, 'rows': after, 'choices': choices}
    finally:
        actor.close()


def leaks(payload, active):
    text = json.dumps(payload).lower()
    return [phase for phase in PHASES if phase != active and phase in text]


def assistant_violations(before, after, receipt):
    violations = []
    for key in ('context', 'parameters'):
        reply = receipt['wire'].get(key, {})
        if not reply.get('success'):
            violations.append(f'Assistant {key} never returned its science payload')
            continue
        value = reply['value']
        scientific = (
            value
            if key == 'parameters'
            else {
                name: value.get(name)
                for name in ('structures', 'datasets', 'relations', 'parameters')
            }
        )
        if ACTIVE not in json.dumps(scientific):
            violations.append(f'Assistant {key} lost its active-phase positive control')
        if leaks(scientific, ACTIVE):
            violations.append(f'Assistant {key} exposes {leaks(scientific, ACTIVE)}')
    for key, model, added, removed in [
        ('rename', 'aliases', 'zz_unused_edited', 'zz_unused'),
        ('constraint', 'constraints', 'zz_visible_rule_edited', 'zz_visible_rule'),
        ('append', 'aliases', 'visible_width', None),
        ('remove', 'aliases', None, 'zz_drop'),
        ('remove_constraint', 'constraints', None, 'zy_drop_rule'),
    ]:
        visible = {row['id'] for row in receipt['rows'][model]}
        ok = receipt['wire'].get(key, {}).get('success') and (
            (added is None or added in visible) and (removed is None or removed not in visible)
        )
        if not ok:
            violations.append(f'Assistant {key} missed its visible row after hidden predecessors')
    hidden_receipt = receipt['wire'].get('hidden_target', {})
    if not hidden_receipt or hidden_receipt.get('success'):
        violations.append('Assistant editing accepted a disabled relation identity')
    if any(leaks(row.get('offered'), ACTIVE) for row in receipt['choices']):
        violations.append('A live assistant offer displayed a disabled phase')
    if receipt['wire'].get('append', {}).get('success'):
        chosen = [row for row in receipt['choices'] if row['kind'] == 'original_choice_activated']
        visible_width = next(
            (row for row in receipt['rows']['aliases'] if row['id'] == 'visible_width'), {}
        )
        if not chosen or visible_width.get('parameter') != 'd20.peak.broad_gauss_u':
            violations.append(
                'Assistant Append did not use the real selector for the requested target'
            )
    hidden = [ALIASES[phase] for phase in PHASES if phase != ACTIVE]
    hidden += ['aa_saffron_rule', 'bb_hidden_input']
    rows = {line.split()[0]: line for line in before.splitlines() if line.split()}
    assert all(
        key in rows for key in [*hidden, 'zz_unused', 'zz_drop', 'zz_visible_rule', 'zy_drop_rule']
    ), 'The saved witness contains hidden predecessors and each visible edit target'
    positions = list(rows)
    assert positions.index('aa_saffron') < positions.index('zz_unused') and positions.index(
        'aa_saffron_rule'
    ) < positions.index('zy_drop_rule'), (
        'Both editable relation tables exercise indices shifted by preceding hidden rows'
    )
    stored = set(after.splitlines())
    violations.extend(
        f'Assistant operations changed the stored hidden relation {key}'
        for key in hidden
        if rows[key] not in stored
    )
    return violations


@pytest.fixture(scope='module')
def projection_evidence(tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp('disabled-phase-projection')
    project = materialize(tmp_path / 'projection')
    materialize(tmp_path / 'additions', active='azure', additions=True)
    materialize(tmp_path / 'broken', active='azure', additions=True, broken=True)
    materialize(tmp_path / 'sequential', sequential=True)
    runner = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assistant = Path(
        os.environ.get(
            'EDI_ASSISTANT_UI_PROBE',
            ROOT / 'build/app/assistant-ui-probe/assistant_real_owner_probe',
        )
    )
    assert runner.is_file() and assistant.is_file(), (
        'The phase projection gate requires both compiled production hosts'
    )
    qt_failures = []
    for surface in ('consumers', 'sequential', 'healthy_add', 'unresolved_add'):
        result = subprocess.run(
            [
                'bash',
                str(ROOT / 'tests/fixtures/scan_views/run.sh'),
                str(runner),
                '-input',
                str(ROOT / 'tests/unit/app/tst_disabled_phase_projection.qml'),
                f'DisabledPhaseProjection::test_{surface}',
            ],
            cwd=ROOT,
            env={**os.environ, 'EDI_ACCEPTANCE_REFERENCE': str(tmp_path)},
            capture_output=True,
            text=True,
            check=False,
            timeout=110,
        )
        output = result.stdout + result.stderr
        (tmp_path / f'native-{surface}.log').write_text(output)
        if result.returncode != 0 or '0 skipped' not in output:
            qt_failures.append(output)
    probe, identity = native._frozen_main_probe(assistant, tmp_path)
    (tmp_path / 'selected-probe.json').write_text(json.dumps(identity, indent=2) + '\n')
    before, after, receipt = assistant_observations(probe, tmp_path, project)
    (tmp_path / 'assistant-projection.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return qt_failures, before, after, receipt


def test_active_phase_projection_reaches_every_scientific_consumer(projection_evidence):
    qt_failures, before, after, receipt = projection_evidence
    violations = assistant_violations(before, after, receipt)
    assert not qt_failures and not violations, (
        'The active phase is the sole scientific participant across all real consumers. '
        + json.dumps(violations)
        + '\n'
        + '\n'.join(qt_failures)
    )
