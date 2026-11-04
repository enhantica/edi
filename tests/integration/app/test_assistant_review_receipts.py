"""Native read details and accepted fit restoration across review boundaries."""

import json
import re

import pytest

from tests.integration.app.test_assistant_misfit_workflow import actor_in, replies, send
from tests.system.py import test_e11_t5_dev_native_integration as base


def capture_edge_reads(tmp_path_factory):
    actor = actor_in(tmp_path_factory.mktemp('edge-reads') / 'actor', [[]])
    try:
        dataset = json.loads(actor.last['ui']['context'])['datasets'][0]
        call = base.tool_call
        bragg = call('inspect_data', 'bragg-tail', dataset_id=dataset['id'], start=0, count=1)
        bragg['arguments']['source'] = 'bragg'
        summary = call(
            'inspect_data',
            'summary-tail',
            dataset_id=dataset['id'],
            start=dataset['axis']['count'] - 1,
            count=9,
            view='summary',
            partitions=8,
        )
        huge = call('inspect_data', 'huge', dataset_id=dataset['id'], start=1e20, count=9)
        fractional = call(
            'inspect_data', 'fractional', dataset_id=dataset['id'], start=2.5, count=7
        )
        actor.configure_turns([[bragg], [summary], [huge], [fractional]])
        send(actor, 1)
        first = replies(actor)['bragg-tail']['value']['data']['phases']
        total = max(phase['total'] for phase in first)
        bragg['arguments'].update(start=total - 1, count=9)
        actor.append_turn([bragg | {'call_id': 'bragg-clamped'}])

        descriptions = {}
        for turn, label in enumerate(('summary-tail', 'huge', 'fractional', 'bragg-clamped'), 2):
            known = {row['id'] for row in actor.last['ui']['messages']}
            send(actor, turn)
            rows = [
                row
                for row in actor.last['ui']['messages']
                if row['id'] not in known
                and (row.get('payload') or {}).get('tool') == 'inspect_data'
            ]
            assert len(rows) == 1, 'Each isolated turn retains its own actual native activity row'
            descriptions[label] = actor.command('activity_description', row_id=rows[0]['id'])[
                'reply'
            ]['description']
        outcome = {'replies': replies(actor), 'descriptions': descriptions}
        (actor.folder / 'edge-read-receipts.json').write_text(json.dumps(outcome, indent=2) + '\n')
        return outcome
    finally:
        actor.close()


def completed_ranges(text):
    return [
        tuple(map(int, bounds))
        for bounds in re.findall(
            r'\b(?:Read|Summarized) (?:rows|reflections) (\d+) to (\d+)', text
        )
    ]


def test_bragg_details_only_claim_returned_phase_rows(review_evidence):
    edge_reads = review_evidence['reads']
    receipt = edge_reads['replies']['bragg-clamped']
    assert receipt['success'], 'The current Bragg tail is admitted by the native reader'
    phases = receipt['value']['data']['phases']
    expected = {(phase['start'] + 1, phase['end']) for phase in phases if phase['rows']}
    assert expected and all(len(phase['rows']) <= 1 for phase in phases), (
        'The authored Bragg request has a clamped nonempty tail'
    )
    ranges = completed_ranges(edge_reads['descriptions']['bragg-clamped'])
    assert set(ranges) == expected, 'Bragg details name only the per-phase rows actually returned'


def test_summary_details_only_claim_returned_bins(review_evidence):
    edge_reads = review_evidence['reads']
    receipt = edge_reads['replies']['summary-tail']
    assert receipt['success'], 'The one-row summary is admitted by the native reader'
    data = receipt['value']['data']
    assert len(data['summary']['bins']) == 1, 'Only one returned row is available for binning'
    text = edge_reads['descriptions']['summary-tail']
    assert completed_ranges(text) == [(data['start'] + 1, data['end'])], (
        'Summary details use the actual clamped row range'
    )
    assert all(int(n) == 1 for n in re.findall(r'\bin (\d+) parts\b', text)), (
        'Summary details can claim only the one returned bin'
    )


def test_refused_numeric_indices_never_claim_a_completed_read(review_evidence):
    edge_reads = review_evidence['reads']
    for label in ('huge', 'fractional'):
        receipt = edge_reads['replies'][label]
        assert not receipt['success'], 'Invalid provider indices are refused by the native tool'
        assert not re.search(
            r'\b(?:Read|Summarized) (?:rows|reflections)\b',
            edge_reads['descriptions'][label],
        ), 'A refused read with an out-of-range or fractional index never claims observed rows'


def fit_record(actor):
    actor.until(lambda row: not row['ui']['project']['calculating'])
    files = actor.command('scientific_receipt')['reply']['files']
    project = actor.last['ui']['project']
    return {
        'files': {entry['relative']: entry['text'] for entry in files},
        **{key: project[key] for key in ('parameters', 'aliases', 'constraints', 'backgrounds')},
    }


def capture_rejected_fit(tmp_path_factory, *, show_actions):
    actor = actor_in(
        tmp_path_factory.mktemp('rejected-fit') / 'actor',
        [[base.tool_call('run_fit', 'accepted-fit')]],
        show_actions=show_actions,
    )
    try:
        send(actor, 1)
        first = fit_record(actor)
        actor.append_turn([base.tool_call('run_fit', 'rejected-fit')])
        send(actor, 2)
        second = fit_record(actor)
        actor.append_turn([base.tool_call('undo_fit', 'undo-rejected-fit')])
        send(actor, 3)
        restored = fit_record(actor)
        receipt = {
            'first': first,
            'second': second,
            'restored': restored,
            'replies': replies(actor),
        }
        (actor.folder / 'undo-accepted-record.json').write_text(
            json.dumps(receipt, indent=2) + '\n'
        )
        return receipt
    finally:
        actor.close()


@pytest.fixture(scope='module')
def review_evidence(tmp_path_factory):
    return {
        'reads': capture_edge_reads(tmp_path_factory),
        'background': capture_rejected_fit(tmp_path_factory, show_actions=False),
        'shown': capture_rejected_fit(tmp_path_factory, show_actions=True),
    }


@pytest.mark.parametrize('mode', ['background', 'shown'])
def test_undo_rejected_fit_restores_the_complete_accepted_record(review_evidence, mode):
    receipt = review_evidence[mode]
    for label in ('accepted-fit', 'rejected-fit'):
        fit = receipt['replies'][label]
        assert fit['success'] and fit['value']['adopted'], (
            'Both trials must reach ordinary native fit adoption before the second is rejected'
        )
    first = receipt['first']
    second = receipt['second']
    analysis = 'analysis/analysis.edi'
    assert '_fit_result.result_kind' in first['files'][analysis], (
        'The live accepted state includes a serialized native fit record'
    )
    assert first['files'][analysis] != second['files'][analysis], (
        'Trial B must have a distinct native fit record so Undo has a real restoration target'
    )
    undo = receipt['replies']['undo-rejected-fit']
    assert undo['success'], 'Rejecting B reaches the ordinary native fit Undo'
    assert receipt['restored'] == first, (
        'Undo of B restores the parameters, uncertainties, flags, relationships and saved record'
    )
