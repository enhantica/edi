"""Data-heavy assistant work exports one readable copy of each actual reply."""

import base64
import json
import shutil
from operator import itemgetter

import pytest

from tests.system.py import test_e11_t5_dev_native_integration as native

SCENARIOS = json.loads(
    (native.ROOT / 'tests/fixtures/work_report_export/reference.json').read_text()
)['scenarios']


@pytest.fixture(scope='module')
def report_observations(tmp_path_factory):
    folder = tmp_path_factory.mktemp('work-report-exports')
    lifetime = native.main_actor.__wrapped__(folder)
    create = next(lifetime)
    try:
        yield {scenario['id']: observe_report(create, folder, scenario) for scenario in SCENARIOS}
    finally:
        next(lifetime, None)


def observe_report(create, tmp_path, scenario):
    # The two reported sessions contain nine and fourteen inspect_data calls.
    # Replay that repetition with public raw slices that fit the attachment limit.
    actor = create([[]])
    reads = scenario['inspection_calls']
    project = tmp_path / scenario['id']
    shutil.copytree(native.ROOT / 'tests/fixtures/background_estimate/projects/hrpt', project)
    assert actor.command('open', path=str(project))['reply']['opened'], (
        'The report-size scenario opens the unchanged public diffraction project'
    )
    actor.until(lambda row: not row['ui']['project']['calculating'])
    if native._unique_input_control(actor.last, 'home.start') is not None:
        actor.command('click', name='home.start')
    actor.command('accept_context')
    actor.until(lambda row: row['ui']['connected'])
    dataset = json.loads(actor.last['ui']['context'])['datasets'][0]
    calls = [
        native.tool_call(
            'inspect_data',
            f'full-inspection-{index}',
            dataset_id=dataset['id'],
            start=0,
            count=min(512, dataset['axis']['count']),
        )
        for index in range(reads)
    ]
    calls.append(
        native.tool_call(
            'inspect_data', 'missing-dataset', dataset_id='missing-dataset', start=0, count=17
        )
    )
    actor.configure_turns([calls])
    actor.request('Inspect the full observations repeatedly, then report the missing dataset.')
    native._session_completed(actor, 1)
    retained_path = project / 'reports/work-report.json'
    actor.until(lambda _row: retained_path.is_file() and native.FINAL in retained_path.read_text())
    retained_bytes = retained_path.read_bytes()
    retained = json.loads(retained_bytes)
    text = native.qml(actor, 'Session.assistant.workReportDocument()')
    exported = json.loads(text)
    after_copy_bytes = retained_path.read_bytes()
    (actor.folder / 'report-size.json').write_text(
        json.dumps({
            'reads': reads,
            'retained_bytes': len(retained_bytes),
            'exported_bytes': len(text.encode()),
        })
    )
    native.qml(actor, '(function(){feedbackDialog.openAs("feedback", "");return true;})()')
    actor.until(lambda _row: native.qml(actor, 'feedbackDialog.opened'))
    available = any(
        row['name'] == 'feedback.files.workReport' and row['fully_exposed']
        for row in actor.last['ui']['controls']
    )
    if available:
        actor.command('click', name='feedback.files.workReport')
    attached = native.qml(actor, 'feedbackDialog.attachedFiles')
    return {
        'actor': actor,
        'calls': calls,
        'after_copy_bytes': after_copy_bytes,
        'retained_bytes': retained_bytes,
        'retained': retained,
        'text': text,
        'exported': exported,
        'attached': attached,
    }


@pytest.mark.parametrize('scenario', SCENARIOS, ids=itemgetter('id'))
def test_repeated_inspection_report_is_smaller_and_keeps_reader_evidence(  # noqa: PLR0914, PLR0915
    report_observations, scenario
):
    observed = report_observations[scenario['id']]
    actor = observed['actor']
    calls = observed['calls']
    retained_bytes = observed['retained_bytes']
    retained = observed['retained']
    text = observed['text']
    exported = observed['exported']
    attached = observed['attached']
    assert '\n' not in text and len(text.encode()) * 2 < len(retained_bytes), (
        'Repeated raw observations export compact JSON at less than half the retained size'
    )
    assert observed['after_copy_bytes'] == retained_bytes, (
        'Copying a compact report preserves every byte of the retained diagnostic report'
    )
    for key in ('schema', 'coverage', 'observations', 'agent_assessment'):
        assert exported[key] == retained[key], (
            'Compact copying preserves report identity, coverage, observations and assessment'
        )
    for key in ('instance_id', 'scope_id', 'turns'):
        assert exported['scope_coverage'][key] == retained['scope_coverage'][key], (
            'Compact copying keeps the original report scope and terminal turn facts'
        )
    assert exported['artifact']['state'] == retained['artifact']['state'], (
        'The cached prepublication copy does not claim a different artifact publication state'
    )
    original_rows = {entry['row_id']: entry for entry in retained['history_evidence']}
    assert [entry['row_id'] for entry in exported['history_evidence']] == list(original_rows), (
        'Every original history entry remains present in its original order'
    )
    requests = {
        row['id']: row['params']['callId']
        for row in map(json.loads, actor.trace.with_suffix('.sent.jsonl').read_text().splitlines())
        if row.get('method') == 'item/tool/call'
    }
    wire = {requests[reply['id']]: reply['result'] for reply in actor.responses()}
    seen = set()
    for entry in exported['history_evidence']:
        original = original_rows[entry['row_id']]
        payload = entry['row'].get('payload', {})
        if 'contentItems' not in payload:
            assert entry == original, 'Non-tool history remains complete in the copied report'
            continue
        call = payload['id']
        seen.add(call)
        assert payload['contentItems'] == wire[call]['contentItems'], (
            'Each exported tool call keeps every exact content item the model actually read'
        )
        assert entry['row']['status'] == original['row']['status'], (
            'Compaction preserves each tool completion or failure status'
        )
        assert {key: value for key, value in entry['row'].items() if key != 'payload'} == {
            key: value for key, value in original['row'].items() if key != 'payload'
        }, 'Original row identities, captions, kinds and statuses remain available to the reader'
        expected_payload = dict(original['row']['payload'])
        expected_payload.pop('nativeOutcome', None)
        observed_payload = dict(payload)
        observed_payload.pop('nativeOutcome', None)
        assert observed_payload == expected_payload, (
            'Only the duplicate native result may be omitted from an exported tool payload'
        )
        assert not isinstance(payload.get('nativeOutcome'), dict), (
            'The exported report does not repeat the native result beside the model-visible copy'
        )
        previous = original.get('work_evidence', {}).get('value', {}).get('projected_reply', {})
        projection = entry.get('work_evidence', {}).get('value', {}).get('projected_reply', {})
        if previous.get('value', {}).get('contentItems') == payload['contentItems']:
            assert not isinstance(projection['value']['contentItems'], list), (
                'The same model-visible reply is not repeated in the projection evidence'
            )
        else:
            assert projection == previous, (
                'A distinct projection remains available instead of being dropped as a duplicate'
            )
    assert (
        seen == {call['call_id'] for call in calls} and not wire['missing-dataset']['success']
    ), 'The size witness retains all real successful reads and the real failed-read explanation'
    for original, copied in zip(
        retained['identity_inputs']['skills'], exported['identity_inputs']['skills'], strict=True
    ):
        assert {key: value for key, value in copied.items() if key != 'body'} == {
            key: value for key, value in original.items() if key != 'body'
        }, 'Compaction preserves each skill capture, version, identity and digest'
        assert (
            copied['skill_id'] == original['skill_id'] and copied['sha256'] == original['sha256']
        ), 'The copied report still identifies every skill by its original name and digest'
        body = original['body'].get('value')
        if isinstance(body, str):
            assert copied['body']['value'] == {'bytes': len(body.encode())}, (
                'Repeated skill text is represented by its exact original UTF-8 byte count'
            )
    schema = retained['identity_inputs']['tool_schema']
    assert exported['identity_inputs']['tool_schema']['sha256'] == schema['sha256'], (
        'The tool schema keeps its original identity after its repeated body is compacted'
    )
    if isinstance(schema['body'].get('value'), list):
        assert exported['identity_inputs']['tool_schema']['body']['value']['tools'] == [
            tool['name'] for tool in schema['body']['value']
        ], 'The reader can still identify every available tool without repeated schema text'
    assert len(attached) == 1 and attached[0]['name'] == 'work-report.json', (
        'One click attaches exactly the current AI work report without a file chooser'
    )
    attached_bytes = base64.b64decode(attached[0]['data'])
    attached_document = json.loads(attached_bytes)
    for key in ('history_evidence', 'identity_inputs', 'agent_assessment'):
        assert attached_document[key] == exported[key], (
            'The attached JSON keeps the same complete replies, identities and assessment'
        )
    assert attached[0]['size'] == len(attached_bytes) and len(attached_bytes) * 2 < len(
        retained_bytes
    ), 'The actual attached file has an exact UTF-8 size and retains the compact representation'
