"""Opt-in real Session/VM workflow integration, no fake rows or connection state.

Core-only queue/skill gates remain separate. This component observes public models,
actual signed-offline NativeDependencies and actual recorded HTTP/owned archive.
It has no Composer editor: actual draft/widgets/visual input stay explicit holes.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
from pathlib import Path

import pytest

from tests.fixtures.assistant.response_events import message_complete, message_start, text_fragment
from tests.system.app import test_e11_t5_vm_retention as prior

ROOT = Path(__file__).resolve().parents[3]
_spec = importlib.util.spec_from_file_location(
    'workflow_skill_originals', ROOT / 'tests/system/py/test_e11_t5_skill_context.py'
)
skills = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(skills)
signer = prior.signer
PROJECT = ROOT / 'tests/fixtures/e04_t1/editable-project'


@pytest.fixture
def workflow_vm(monkeypatch):
    binary = Path(os.environ['EDI_ASSISTANT_WORKFLOW_VM_PROBE'])
    assert binary.is_file(), 'I17/FIFO: opt-in target must link the actual Session/VM/native graph'
    monkeypatch.setenv('QT_QPA_PLATFORM', 'offscreen')
    actor = prior.Component(binary)
    actor.command('inspect')
    try:
        yield actor
    finally:
        actor.close()


def connect(vm, signer, *, projectless=False):
    if projectless:
        vm.command('close_project')
    else:
        opened = vm.command('open', path=str(PROJECT))
        assert opened['reply']['opened'], 'I4: original project opens through the real Session'
    prior.authenticate(vm, signer)
    vm.command('select_model', id='gpt-6.1-sol')
    vm.command('select_effort', id='high')
    return vm.last


def acknowledge(vm):
    before = vm.last['vm']['context']
    vm.command('sign_in')  # Existing connected public context-acceptance door.
    assert not vm.last['vm']['context_consent_required'], (
        'I17: actual connected acceptance acknowledges the currently disclosed context'
    )
    assert vm.last['vm']['context'] == before, (
        'I17: acknowledgment does not rewrite the disclosure'
    )


def surface(vm):
    exposed = vm.last['vm']['workflow_surface']
    assert all(exposed.values()), (
        'I17/4507 SETUP: actual read-only constant catalog, notified read-only selection and '
        'public selectSkill method must exist; absent metadata is not a fake admission: '
        + str(exposed)
    )


def user_rows(vm, text):
    return [
        row
        for row in vm.last['vm']['messages']
        if row.get('kind') == 'user' and row.get('text') == text
    ]


def complete_text(vm, index, text):
    return prior.events(
        vm, index, [*message_start(), text_fragment(text), *message_complete(text)]
    )


def wire_context(body):
    # Observe the actual serialized context value without pinning instruction prose
    # or accepting an arbitrary matching nested value in the provider request.
    instruction = body['instructions']
    assert isinstance(instruction, str), 'I17: actual provider instructions are textual'
    decoder = json.JSONDecoder()
    found = []
    for offset, character in enumerate(instruction):
        if character != '{':
            continue
        try:
            value, _ = decoder.raw_decode(instruction, offset)
        except ValueError:
            continue
        if isinstance(value, dict) and value.get('schema') == 'edi.assistant.context/1':
            found.append(value)
    assert len(found) == 1, (
        'I17: actual provider instructions contain one complete context snapshot'
    )
    return found[0]


@pytest.mark.parametrize('projectless', [True, False], ids=['home', 'real-project'])
def test_actual_selected_skill_changes_disclosure_requires_fresh_consent_and_reaches_wire(
    workflow_vm, signer, projectless
):
    vm = workflow_vm
    connect(vm, signer, projectless=projectless)
    surface(vm)
    assert vm.last['vm']['selected_skill'] == 'project-assistance', (
        'I17: actual fresh Session defaults to the reviewed project workflow'
    )
    assert vm.last['vm']['context']['skills'] == [skills.shipped('project-assistance')], (
        'I17: the actual initial disclosure carries exact shipped default content/version/hash'
    )
    catalog = vm.last['vm']['skills']
    assert isinstance(catalog, list) and {row['id'] for row in catalog} == set(skills.IDS), (
        'I17: read-only actual VM catalog exposes the three declared resources'
    )
    acknowledge(vm)
    before = vm.last
    invoked = vm.command('select_skill', id='fullprof-intake')
    assert invoked['reply']['method_present'] and invoked['reply']['invoked'], (
        'I17/4507: public method invocation is observed separately from actual selection'
    )
    assert vm.last['vm']['selected_skill'] == 'fullprof-intake', (
        'I17: explicit user action really selects the initial FullProf resource'
    )
    expected = vm.last['vm']['context']
    assert expected['skills'] == [skills.shipped('fullprof-intake')], (
        'I17: actual selected disclosure contains the exact FullProf resource, never only a URL'
    )
    assert vm.last['vm']['context_consent_required'], (
        'I17: changing actual workflow content invalidates the previous context acknowledgment'
    )
    physical = len(prior.responses(vm))
    rows = vm.last['vm']['messages']
    vm.command('send_text', text='Requires acknowledgment of my changed workflow')
    assert len(prior.responses(vm)) == physical and vm.last['vm']['messages'] == rows, (
        'I17: stale workflow consent cannot physically send or admit a hidden user prompt'
    )
    assert vm.last['vm']['project'] == before['vm']['project'], (
        'I2/I17: selecting guidance and refusing a send cannot mutate scientific state'
    )
    acknowledge(vm)
    index = prior.begin(vm, 'Read my explicitly disclosed FullProf workflow')
    body = json.loads(vm.last['requests'][index]['body'])
    assert wire_context(body) == expected, (
        'I17: actual native request contains the same complete consented workflow/context'
    )
    assert (expected['project'] is None) == projectless, (
        'I17: actual Home and real-project owners retain their declared project identity'
    )


def test_busy_actual_skill_command_preserves_live_request_and_current_selection(
    workflow_vm, signer
):
    vm = workflow_vm
    connect(vm, signer)
    surface(vm)
    acknowledge(vm)
    prior.begin(vm, 'Keep this actual operation active')
    before = vm.last
    invoked = vm.command('select_skill', id='fullprof-intake')
    assert invoked['reply']['invoked'], 'I17: busy test reaches the actual public skill command'
    assert vm.last['vm']['selected_skill'] == before['vm']['selected_skill'], (
        'I17: actual active work cannot change its selected workflow through idle-only selection'
    )
    assert (
        vm.last['vm']['context'] == before['vm']['context']
        and vm.last['requests'] == before['requests']
    ), 'I17: refused busy selection preserves consent scope and actual physical request'
    assert vm.last['vm']['can_cancel'], (
        'FIFO: ordinary Stop remains available after refused selection'
    )


def test_pending_user_row_is_immediate_stable_and_delivered_once_after_original(
    workflow_vm, signer
):
    vm = workflow_vm
    connect(vm, signer)
    acknowledge(vm)
    original = prior.begin(vm, 'FIRST actual active human original')
    before = vm.last
    pending_text = 'SECOND actual pending human — Ångström'
    vm.command('send_text', text=pending_text)
    pending = user_rows(vm, pending_text)
    assert len(pending) == 1 and isinstance(pending[0]['id'], str) and pending[0]['id'], (
        'FIFO: admission immediately exposes exactly one stable original pending user row'
    )
    assert pending[0]['status'] in {'pending', 'queued'}, (
        'FIFO: undispatched actual user row truthfully indicates pending delivery'
    )
    identity = pending[0]['id']
    assert vm.last['requests'] == before['requests'] and vm.last['vm']['can_cancel'], (
        'FIFO: pending human preserves live physical inference and leaves ordinary Stop usable'
    )
    complete_text(vm, original, 'Actual original reply completes before the pending human')
    physical = prior.responses(vm)
    assert len(physical) == 2, (
        'FIFO: one settled original boundary sends one physical continuation'
    )
    after = user_rows(vm, pending_text)
    assert (
        len(after) == 1
        and after[0]['id'] == identity
        and after[0]['status'] in {'sent', 'completed'}
    ), 'FIFO: actual delivery updates the same pending row rather than appending a duplicate'
    body = json.loads(physical[-1][1]['body'])
    humans = [item['content'] for item in body['input'] if item.get('role') == 'user']
    assert humans.count(pending_text) == 1, (
        'FIFO: actual native next wire includes the pending original once'
    )
    assert vm.last['vm']['project'] == before['vm']['project'], (
        'I2/FIFO: admission and successful non-tool conversation change no scientific state'
    )


def test_failed_pending_archive_commit_preserves_prior_row_and_original_operation(
    workflow_vm, signer
):
    vm = workflow_vm
    connect(vm, signer)
    acknowledge(vm)
    prior.begin(vm, 'Original remains live across failed later persistence')
    vm.command('send_text', text='Already admitted pending original')
    assert len(user_rows(vm, 'Already admitted pending original')) == 1, (
        'FIFO: genuine pending admission is a required precondition before storage refusal'
    )
    vm.command('persistence_barrier')
    before = vm.last
    refused_text = 'This attempted pending original must not become hidden history'
    vm.command('send_text', text=refused_text)
    assert (
        not user_rows(vm, refused_text) and vm.last['vm']['messages'] == before['vm']['messages']
    ), 'FIFO: real owned archive refusal cannot publish an ambiguous or hidden admitted user row'
    assert vm.last['requests'] == before['requests'] and vm.last['vm']['can_cancel'], (
        'FIFO: failed pending persistence preserves the actual original operation and Stop'
    )
    assert vm.last['vm']['last_error'], (
        'FIFO: genuine failed persistence remains publicly explained'
    )


@pytest.mark.parametrize(
    'retirement', ['cancel', 'clear_history', 'close_project', 'sign_out', 'destroy']
)
def test_real_owner_retirement_fences_late_original_completion_and_pending_dispatch(
    workflow_vm, signer, retirement
):
    vm = workflow_vm
    connect(vm, signer)
    acknowledge(vm)
    original = prior.begin(vm, 'Original before explicit real-owner retirement')
    text = 'Pending instruction must not inherit retired authority'
    vm.command('send_text', text=text)
    assert len(user_rows(vm, text)) == 1, (
        'FIFO: real queued row must exist before testing retirement'
    )
    physical = len(prior.responses(vm))
    vm.command(retirement)
    if retirement == 'destroy':
        vm.command('recreate')
    before = vm.last
    complete_text(vm, original, 'Retired original callback must not reach a new current owner')
    assert len(prior.responses(vm)) == physical, (
        'FIFO: actual owner retirement revokes pending physical dispatch across every caller'
    )
    assert vm.last['vm']['messages'] == before['vm']['messages'], (
        'FIFO: late actual old callbacks cannot append or deliver over the retired current model'
    )
    if retirement == 'clear_history':
        assert not vm.last['vm']['messages'], (
            'FIFO: explicit Clear removes owned pending conversation evidence'
        )


def test_manual_project_attachment_survives_assistant_context_capacity_and_keeps_catalog(
    workflow_vm, tmp_path
):
    # Actual documented .edi exclusion loop, copied original project, no private VM mutation.
    project = tmp_path / 'large-original-project'
    shutil.copytree(PROJECT, project)
    bank = project / 'experiments/hrpt.edi'
    text = bank.read_text()
    original = '_excluded_region.end\n1 0. 5.\n2 165. 180.'
    assert text.count(original) == 1, (
        'SK4 SETUP: original documented exclusion loop is uniquely identified '
        'before fixture growth'
    )
    originals = [
        {'id': 'owned-' + str(index), 'first': 1.25, 'second': 2.75} for index in range(23000)
    ]
    assert len(json.dumps(originals, separators=(',', ':')).encode()) > 1048576, (
        'SK4 SETUP: independently encoded original exclusion array alone exceeds context_bytes'
    )
    rows = '\n'.join(row['id'] + ' 1.25 2.75' for row in originals)
    bank.write_text(text.replace(original, '_excluded_region.end\n' + rows))
    vm = workflow_vm
    opened = vm.command('open', path=str(project))
    assert opened['reply']['opened'] and opened['vm']['project_present'], (
        'SK4: legitimate assistant-capacity refusal cannot escape real Session project attachment'
    )
    surface(vm)
    assert opened['vm']['context'].get('error'), (
        'SK4: actual large project reaches bounded assistant context refusal, '
        'not a tiny-control pass'
    )
    assert {row['id'] for row in opened['vm']['skills']} == set(skills.IDS), (
        'SK4: immutable bounded catalog remains usable independently of large project context'
    )
    assert not prior.responses(vm) and not opened['vm']['can_cancel'], (
        'SK4: ordinary manual attachment performs no provider work or fabricated busy transition'
    )
    vm.command('close_project')
    assert not vm.last['vm']['project_present'] and not vm.last['vm']['context'].get('error'), (
        'SK4: ordinary detach restores usable projectless disclosure without losing catalog'
    )
