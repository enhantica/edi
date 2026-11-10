"""Replay every case-owned tutorial and the auxiliary Interface tour on the real app."""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from tests.fixtures.tutorial_cases.contract import ROOT, cases_for
from tests.fixtures.tutorial_cases.manual_simulation import model_errors
from tests.fixtures.tutorial_cases.notebook_fit import local_collection
from tests.system.py.test_tutorial_case_ownership import simulation_construction_errors

AUXILIARY = {'interface': 'Interface tour'}
APP_CASES = cases_for('app')
REQUIRED = [*AUXILIARY, *APP_CASES]
INPUT = ROOT / 'tests/unit/app/tst_tutorial_navigation.qml'
FAULTS = ['missing-step', 'renamed-element', 'late-missing-step']


@pytest.fixture(scope='module')
def replay_receipts(tmp_path_factory, request):
    entries = json.loads((ROOT / 'app/tutorials/manifest.json').read_text())['tutorials']
    indexed = {
        identity: [entry for entry in entries if entry['id'] == identity] for identity in REQUIRED
    }
    binaries = [Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))]
    binaries.append(ROOT / 'build/app/edi_app_tests')
    runner = next((path for path in binaries if path.is_file()), None)
    receipts = {'entries': indexed, 'runner': runner, 'run': None}
    selected = [item for item in request.session.items if item.path == request.node.path]
    wanted = {
        item.callspec.params['tutorial']
        for item in selected
        if hasattr(item, 'callspec') and 'tutorial' in item.callspec.params
    }
    census = any(
        item.originalname == 'test_live_target_census_cannot_accept_a_missing_or_renamed_element'
        for item in selected
    )
    kinds = {
        item.callspec.params['kind']
        for item in selected
        if hasattr(item, 'callspec') and 'kind' in item.callspec.params
    }
    inventory = any(
        item.originalname == 'test_live_dialog_lists_each_case_and_the_interface_tour'
        for item in selected
    )
    faults = {
        item.callspec.params['fault']
        for item in selected
        if hasattr(item, 'callspec') and 'fault' in item.callspec.params
    }
    functions = [
        'TutorialNavigation::test_required_tutorial_replays_to_its_last_step:' + identity
        for identity, values in indexed.items()
        if identity in wanted and len(values) == 1
    ]
    functions.extend(additional_contract_functions(selected))
    if inventory:
        functions.append(
            'TutorialNavigation::test_required_dialog_lists_every_case_and_the_interface_tour'
        )
    if census or faults:
        functions.append(
            'TutorialNavigation::test_required_target_census_refuses_missing_and_renamed_elements'
        )
    functions.extend(
        'TutorialNavigation::test_task_filters_have_five_equal_selectors_and_square_reset:' + kind
        for kind in sorted(kinds)
    )
    if runner is not None and functions:
        folder = tmp_path_factory.mktemp('required-tutorial-replays')
        collection = local_collection(folder / 'collection')
        env = {
            **os.environ,
            'QT_QPA_PLATFORM': 'offscreen',
            'QT_QUICK_BACKEND': 'software',
            'EDI_ONLINE_SOURCES': 'easydiffraction=' + collection.as_uri(),
            'OMP_NUM_THREADS': '1',
            'OPENBLAS_NUM_THREADS': '1',
        }
        receipts['run'] = recorded_run(
            native_command(runner, INPUT, functions),
            env,
            folder / 'replay.log',
            7200,
        )
        receipts['damaged'] = {}
        for fault in sorted(faults):
            receipts['damaged'][fault] = mutated_run(runner, folder, fault, env)
    return receipts


@pytest.mark.parametrize(
    'tutorial', REQUIRED, ids=[AUXILIARY.get(name, name) for name in REQUIRED]
)
def test_each_required_tutorial_replays_to_the_end_and_resolves_every_current_target(
    tutorial, replay_receipts
):
    entries = replay_receipts['entries'][tutorial]
    assert len(entries) == 1, (
        'Gate 4: every required case has one replayable built-in tutorial: ' + tutorial
    )
    if tutorial in AUXILIARY:
        assert entries[0]['title'] == AUXILIARY[tutorial], (
            'Gate 4: the auxiliary Interface tour remains named explicitly'
        )
    assert replay_receipts['runner'] is not None, (
        'Gate 4 prerequisite: build the current real Qt app test host'
    )
    run = replay_receipts['run']
    outcome = '::test_required_tutorial_replays_to_its_last_step(' + tutorial + ')'
    assert any(
        'PASS' in line and outcome in line for line in (run.stdout + run.stderr).splitlines()
    ), 'Gate 4: the app walk completes every step with its actual current target: ' + tutorial
    steps = markers(run, 'TUTORIAL_REPLAY_STEP ', tutorial)
    endings = markers(run, 'TUTORIAL_REPLAY_END ', tutorial)
    assert len(endings) == 1 and endings[0]['atEnd'], (
        'Gate 4: every replay supplies one actual controller completion receipt'
    )
    assert [row['step'] for row in steps] == list(range(1, endings[0]['steps'] + 1)), (
        'Gate 4: the replay visits every written step in order without jumps or omissions'
    )


def test_live_target_census_cannot_accept_a_missing_or_renamed_element(replay_receipts):
    assert replay_receipts['runner'] is not None, (
        'Gate 4 prerequisite: current Qt host for the locator escape exercise'
    )

    run = replay_receipts['run']
    assert any(
        'PASS' in line
        and '::test_required_target_census_refuses_missing_and_renamed_elements()' in line
        for line in (run.stdout + run.stderr).splitlines()
    ), 'Gate 4: the real census reaches its valid target and refuses missing and renamed elements'


@pytest.mark.parametrize('kind', ['examples', 'tutorials'])
def test_app_lists_share_the_five_selector_search_and_square_reset_layout(kind, replay_receipts):
    assert replay_receipts['runner'] is not None, (
        'Gate 4 prerequisite: current Qt host for actual filter geometry'
    )
    run = replay_receipts['run']
    outcome = '::test_task_filters_have_five_equal_selectors_and_square_reset(' + kind + ')'
    assert any(
        'PASS' in line and outcome in line for line in (run.stdout + run.stderr).splitlines()
    ), 'Gate 4: both app lists have five equal selectors in two columns, search and square reset'


def markers(run, label, tutorial):
    context = '::test_required_tutorial_replays_to_its_last_step(' + tutorial + ')'
    return context_markers(run, label, context, tutorial)


def context_markers(run, label, context, identity=None):
    return [
        record
        for line in (run.stdout + run.stderr).splitlines()
        if context in line and label in line
        for record in [json.loads(line.partition(label)[2])]
        if identity is None or record.get('id') == identity
    ]


def test_dialog_inventory_reference_matches_the_declared_app_cases():
    reference = json.loads((ROOT / 'tests/fixtures/tutorial_cases/app-tutorials.json').read_text())
    assert reference['required'] == ['interface', *APP_CASES], (
        'Gate 4: live dialog expectations follow exactly the closed cases declaring app tutorials'
    )
    assert reference['auxiliary'] == AUXILIARY, (
        'Gate 4: Only the auxiliary tour is outside the case-owned replay inventory'
    )


def test_live_dialog_lists_each_case_and_the_interface_tour(replay_receipts):
    run = replay_receipts['run']
    assert run is not None and any(
        'PASS' in line
        and '::test_required_dialog_lists_every_case_and_the_interface_tour()' in line
        for line in (run.stdout + run.stderr).splitlines()
    ), (
        'Gate 4: the current real Tutorials dialog lists one tutorial for every case '
        'and the Interface tour'
    )


def damaged_replay(source, fault):
    anchor = (
        '    function test_required_tutorial_replays_to_its_last_step(data) {\n'
        '        start(data.tutorial);'
    )
    assert source.count(anchor) == 1, (
        'Gate 4: missing-element controls alter the exact same real sequential replay'
    )
    injection = """
        finishPages();
        const originalTarget = panel.steps[0].target;
        const originalItem = target(originalTarget);
"""
    if fault == 'renamed-element':
        injection += '        originalItem.objectName = originalTarget + ".renamed";\n'
    else:
        index = 1 if fault == 'late-missing-step' else 0
        injection += (
            '        const malformed = JSON.parse(JSON.stringify(panel.tutorial));\n'
            f'        malformed.steps[{index}].target = "missing.tutorial.element";\n'
            '        panel.tutorial = malformed;\n'
            '        panel.show();\n'
            '        settleTour();\n'
        )
    target = 'originalTarget' if fault == 'renamed-element' else '"missing.tutorial.element"'
    injection += (
        '        console.info("TUTORIAL_MUTATION_ARMED " + JSON.stringify({'
        f'fault: "{fault}", target: {target}' + '}));\n'
    )
    # Only an intentionally absent target gets a shorter wait; the real census stays identical.
    timeout = '}, 15000, "The actual step names exactly one rendered current GUI element: "'
    assert source.count(timeout) == 1, 'Gate 4: the damaged replay uses the original target census'
    return source.replace(anchor, anchor + injection).replace(
        timeout, timeout.replace('15000', '100')
    )


@pytest.mark.parametrize('fault', FAULTS)
def test_the_actual_sequential_replay_refuses_a_missing_or_renamed_element(fault, replay_receipts):
    assert replay_receipts['run'] is not None, (
        'Gate 4: mutation controls require the actual app host'
    )
    assert any(
        'PASS' in line
        and '::test_required_target_census_refuses_missing_and_renamed_elements()' in line
        for line in (replay_receipts['run'].stdout + replay_receipts['run'].stderr).splitlines()
    ), 'Gate 4: the real first target passes before malformed tutorial steps are exercised'
    result = replay_receipts['damaged'][fault]
    output = result.stdout + result.stderr
    armed = [
        json.loads(line.partition('TUTORIAL_MUTATION_ARMED ')[2])
        for line in output.splitlines()
        if 'TUTORIAL_MUTATION_ARMED ' in line
    ]
    assert result.returncode != 0 and len(armed) == 1 and armed[0]['fault'] == fault, (
        'Gate 4: the malformed real tutorial executes and is refused, never skipped'
    )
    expected = 'The actual step names exactly one rendered current GUI element: interface / '
    assert any(
        'FAIL!' in line
        and 'test_required_tutorial_replays_to_its_last_step(interface)' in line
        and expected + armed[0]['target'] in line
        for line in output.splitlines()
    ), 'Gate 4: the same sequential assertion refuses exactly the deliberately broken target'
    visited = markers(result, 'TUTORIAL_REPLAY_STEP ', 'interface')
    assert [row['step'] for row in visited] == ([1] if fault == 'late-missing-step' else []), (
        'Gate 4: each malformed replay refuses at its intended step after all valid predecessors'
    )
    if fault == 'late-missing-step':
        assert 'app: click tutorial.next' in output, (
            'Gate 4: the second-step escape exercise advances through the real Next control'
        )
    assert not markers(result, 'TUTORIAL_REPLAY_END ', 'interface'), (
        'Gate 4: no malformed tutorial can publish a completed replay'
    )


def mutated_run(runner, folder, fault, env):
    scratch = folder / fault
    scratch.mkdir()
    for script in INPUT.parent.glob('*.js'):
        shutil.copy2(script, scratch / script.name)
    altered = scratch / INPUT.name
    altered.write_text(damaged_replay(INPUT.read_text(), fault))
    result = subprocess.run(
        native_command(
            runner,
            altered,
            ['TutorialNavigation::test_required_tutorial_replays_to_its_last_step:interface'],
        ),
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    (scratch / 'replay.log').write_text(result.stdout + result.stderr)
    return result


def additional_contract_functions(selected):
    functions = []
    if any(
        item.originalname == 'test_fit_step_guard_scales_with_actual_dataset_work'
        for item in selected
    ):
        functions.append('TutorialNavigation::test_required_fit_guard_tracks_dataset_work')
    if any(
        item.originalname == 'test_replay_logging_preserves_receipts_after_many_messages'
        for item in selected
    ):
        functions.append(
            'TutorialNavigation::test_required_replay_keeps_receipts_after_many_messages'
        )
    functions.extend([
        'TutorialNavigation::test_required_async_next_waits_for_the_real_state:' + operation
        for operation in sorted({
            item.callspec.params['operation']
            for item in selected
            if hasattr(item, 'callspec') and 'operation' in item.callspec.params
        })
    ])
    if any(
        item.originalname == 'test_semantic_parameter_target_resolves_the_real_current_cell'
        for item in selected
    ):
        functions.append(
            'TutorialNavigation::test_required_symbolic_parameter_target_is_a_real_named_cell'
        )
    return functions


@pytest.mark.parametrize('operation', ['example', 'structure', 'data', 'fit'])
def test_next_waits_for_the_declared_async_state_without_an_external_action_hook(
    operation, replay_receipts
):
    run = replay_receipts['run']
    succeeded = run is not None and any(
        'PASS' in line
        and '::test_required_async_next_waits_for_the_real_state(' + operation + ')' in line
        for line in (run.stdout + run.stderr).splitlines()
    )
    assert succeeded, (
        'Gate 4: real Next completes each declared asynchronous action before leaving its step'
    )
    wanted = (
        'example:'
        if operation == 'example'
        else 'fitted'
        if operation == 'fit'
        else 'download:' + operation + ':'
    )
    marker = 'TUTORIAL_FIT_COMPLETE ' if operation == 'fit' else 'TUTORIAL_ASYNC_COMPLETE '
    records = [
        record
        for record in context_markers(
            run, marker, '::test_required_async_next_waits_for_the_real_state(' + operation + ')'
        )
        if record['check'].startswith(wanted)
    ]
    assert records and all(row['state'] and row['to'] == row['from'] + 1 for row in records), (
        'Gate 4: async completion records actual model state and one step transition'
    )


def test_semantic_parameter_target_resolves_the_real_current_cell(replay_receipts):
    run = replay_receipts['run']
    succeeded = run is not None and any(
        'PASS' in line
        and '::test_required_symbolic_parameter_target_is_a_real_named_cell()' in line
        for line in (run.stdout + run.stderr).splitlines()
    )
    assert succeeded, (
        'Gate 4: semantic parameter paths resolve actual cells and refuse missing or renamed cells'
    )


def recorded_run(command, env, log, timeout):
    with log.open('w') as output:
        run = subprocess.run(
            command,
            env=env,
            stdout=output,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
            timeout=timeout,
        )
    return subprocess.CompletedProcess(run.args, run.returncode, stdout=log.read_text(), stderr='')


def context_message(function, identity, label, record):
    return (
        'QINFO : edi_app::TutorialNavigation::'
        + function
        + '('
        + identity
        + ') qml: '
        + label
        + json.dumps(record)
        + '\n'
    )


@pytest.mark.parametrize(
    'identity', ['pd-neut-cwl_lbco_simulation', 'pd-neut-cwl_hs-hrpt', 'pd-neut-cwl_lbco-hrpt']
)
def test_step_receipts_belong_to_the_full_replay_context(identity):
    full = 'test_required_tutorial_replays_to_its_last_step'
    prefix = 'test_required_async_next_waits_for_the_real_state'
    text = ''.join(
        context_message(prefix, 'data', 'TUTORIAL_REPLAY_STEP ', {'id': identity, 'step': step})
        for step in [1, 2]
    )
    text += ''.join(
        context_message(full, identity, 'TUTORIAL_REPLAY_STEP ', {'id': identity, 'step': step})
        for step in [1, 2, 3]
    )
    text += context_message(
        prefix, 'data', 'TUTORIAL_REPLAY_END ', {'id': identity, 'steps': 2, 'atEnd': True}
    )
    text += context_message(
        full, identity, 'TUTORIAL_REPLAY_END ', {'id': identity, 'steps': 3, 'atEnd': True}
    )
    run = subprocess.CompletedProcess([], 0, stdout=text, stderr='')
    assert [row['step'] for row in markers(run, 'TUTORIAL_REPLAY_STEP ', identity)] == [1, 2, 3], (
        'Full replay order excludes the same identity from an async-prefix test'
    )
    assert markers(run, 'TUTORIAL_REPLAY_END ', identity) == [
        {'id': identity, 'steps': 3, 'atEnd': True}
    ], 'Only the full replay context may supply its controller-end receipt'


@pytest.mark.parametrize('written', [[1, 3], [1, 2, 2, 3]])
def test_context_filter_preserves_missing_or_duplicate_steps(written):
    identity = 'same-case'
    text = context_message(
        'test_required_async_next_waits_for_the_real_state',
        'data',
        'TUTORIAL_REPLAY_STEP ',
        {'id': identity, 'step': 1},
    )
    text += ''.join(
        context_message(
            'test_required_tutorial_replays_to_its_last_step',
            identity,
            'TUTORIAL_REPLAY_STEP ',
            {'id': identity, 'step': step},
        )
        for step in written
    )
    run = subprocess.CompletedProcess([], 0, stdout=text, stderr='')
    observed = [row['step'] for row in markers(run, 'TUTORIAL_REPLAY_STEP ', identity)]
    assert observed == written, (
        'Context filtering retains each in-context receipt without sorting or deduplication'
    )
    assert observed != [1, 2, 3], (
        'Missing or duplicate full-replay steps remain distinct from a complete ordered walk'
    )


def test_replay_logging_preserves_receipts_after_many_messages(replay_receipts):
    run = replay_receipts['run']
    assert run is not None, 'The logging-boundary control runs on the actual Qt test host'
    output = run.stdout + run.stderr
    values = [
        int(line.partition('TUTORIAL_LOG_CONTINUITY ')[2])
        for line in output.splitlines()
        if 'TUTORIAL_LOG_CONTINUITY ' in line
    ]
    complete = values == list(range(2001))
    assert complete, (
        'The native replay preserves all 2001 control messages past the default Qt message cap'
    )
    assert 'TUTORIAL_LOG_CONTINUITY_END' in output, (
        'The final native receipt survives after every control message'
    )
    assert any(
        'PASS' in line and '::test_required_replay_keeps_receipts_after_many_messages()' in line
        for line in output.splitlines()
    ), 'The real Qt logging control completes rather than being silently truncated'


def native_command(runner, script, functions):
    return [str(runner), '-input', str(script), '-o', '-,txt', '-maxwarnings', '0', *functions]


def test_fit_step_guard_scales_with_actual_dataset_work(replay_receipts):
    run = replay_receipts['run']
    succeeded = run is not None and any(
        'PASS' in line and '::test_required_fit_guard_tracks_dataset_work()' in line
        for line in (run.stdout + run.stderr).splitlines()
    )
    assert succeeded, (
        'Fit guards retain the ordinary floor and scale finitely with actual dataset work'
    )


@pytest.mark.parametrize('operation', ['example', 'structure', 'data', 'fit'])
def test_async_completion_cannot_borrow_a_full_replay_receipt(operation):
    identity = 'same-case'
    marker = 'TUTORIAL_FIT_COMPLETE ' if operation == 'fit' else 'TUTORIAL_ASYNC_COMPLETE '
    check = (
        'fitted'
        if operation == 'fit'
        else 'example:case'
        if operation == 'example'
        else 'download:' + operation + ':entry=block'
    )
    record = {'id': identity, 'check': check, 'from': 1, 'to': 2, 'state': True}
    prefix = 'test_required_async_next_waits_for_the_real_state'
    passed = 'PASS : edi_app::TutorialNavigation::' + prefix + '(' + operation + ')\n'
    foreign = context_message(
        'test_required_tutorial_replays_to_its_last_step', identity, marker, record
    )
    run = subprocess.CompletedProcess([], 0, stdout=passed + foreign, stderr='')
    with pytest.raises(AssertionError, match='async completion records actual model state'):
        test_next_waits_for_the_declared_async_state_without_an_external_action_hook(
            operation, {'run': run}
        )
    own = context_message(prefix, operation, marker, record)
    bad_foreign = context_message(
        'test_required_tutorial_replays_to_its_last_step',
        identity,
        marker,
        {**record, 'state': False},
    )
    run = subprocess.CompletedProcess([], 0, stdout=passed + own + bad_foreign, stderr='')
    test_next_waits_for_the_declared_async_state_without_an_external_action_hook(
        operation, {'run': run}
    )


@pytest.mark.parametrize('tutorial', ['pd-neut-cwl_lbco_simulation'])
def test_hand_built_simulation_has_its_independent_case_structure(tutorial, replay_receipts):
    run = replay_receipts['run']
    records = markers(run, 'TUTORIAL_SIMULATION_MODEL ', tutorial)
    assert len(records) == 1, 'The completed simulation supplies one real scientific-state record'
    steps = markers(run, 'TUTORIAL_REPLAY_STEP ', tutorial)
    assert not simulation_construction_errors(steps), (
        'The actual walk constructs the model through the required manual controls'
    )
    reference = ROOT / 'docs/user/cli' / tutorial / 'project/structures/lbco.edi'
    assert not model_errors(records[0], reference), (
        'The hand-built simulation keeps the saved case cell, group, sites, links and data-free '
        'calculated pattern: ' + repr(model_errors(records[0], reference))
    )
