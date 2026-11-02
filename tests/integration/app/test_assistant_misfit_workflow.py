"""Actual adopted-fit and data-read receipts, with independent scalar math."""

import json
import os
import shutil
from operator import itemgetter
from pathlib import Path

import pytest

from tests.integration.py.assistant_misfit_reference import (
    native_windows,
    peak,
    population,
    weighted,
)
from tests.system.py import test_e11_t5_dev_native_integration as base

ROOT = Path(__file__).resolve().parents[3]


def actor_in(folder, turns):
    folder.mkdir()
    binary = Path(
        os.environ.get(
            'EDI_ASSISTANT_UI_PROBE',
            ROOT / 'build/app/assistant-ui-probe/assistant_real_owner_probe',
        )
    )
    actor = base.MainActor(binary, folder, {'turns': turns}, False)
    base.qml(actor, '(function(){raise();requestActivate();return true;})()')
    project = folder / 'project'
    shutil.copytree(ROOT / 'tests/fixtures/fit_quality/uncertainty', project)
    bank = project / 'experiments/bank.edi'
    (bank.parent / 'second.edi').write_text(
        bank.read_text().replace('data_bank\n', 'data_second\n', 1)
    )
    analysis = project / 'analysis/analysis.edi'
    analysis.write_text(
        analysis.read_text().replace('_fitting_mode.type single', '_fitting_mode.type joint')
    )
    opened = actor.command('open', path=str(project))['reply']['opened']
    assert opened, 'The ordinary project loader must open the two-pattern captured-input fixture'
    actor.until(lambda row: not row['ui']['project']['calculating'])
    actor.connect()
    return actor


def send(actor, count):
    actor.connect()
    actor.until(lambda _row: base.qml(actor, 'Session.assistant.draftAdmissionReady'))
    identity = base.qml(
        actor,
        'Session.assistant.submitDraft('
        '"Exercise the current native operation and retain its actual result.")',
    )
    assert identity, (
        'The original current assistant must admit exactly this deterministic peer request'
    )
    base._session_completed(actor, count)


def replies(actor):
    sent = list(map(json.loads, actor.trace.with_suffix('.sent.jsonl').read_text().splitlines()))
    results = {row['id']: row['result'] for row in actor.responses()}
    return {
        row['params']['callId']: {
            'success': results[row['id']]['success'],
            'value': json.loads(results[row['id']]['contentItems'][0]['text']),
        }
        for row in sent
        if row.get('method') == 'item/tool/call' and row['id'] in results
    }


@pytest.fixture(scope='module')
def fitted(tmp_path_factory):
    actor = actor_in(
        tmp_path_factory.mktemp('misfit-adopted') / 'actor',
        [[base.tool_call('run_fit', 'fit-with-summary')]],
    )
    try:
        send(actor, 1)
        outcome = replies(actor)['fit-with-summary']['value']
        actor.until(lambda row: not row['ui']['project']['calculating'])
        patterns = (
            actor.command('pattern_inputs')['reply']['patterns'] if 'misfit' in outcome else None
        )
        receipt = {'outcome': outcome, 'patterns': patterns}
        (actor.folder / 'misfit-and-original-arrays.json').write_text(
            json.dumps(receipt, indent=2) + '\n'
        )
        yield receipt
    finally:
        actor.close()


def near(value, expected, requirement):
    assert value == pytest.approx(expected, rel=2e-10, abs=2e-10), (
        f'Independent scalar summary follows the original arrays: {requirement}'
    )


@pytest.fixture(scope='module')
def evidence(fitted, reads):
    # The runtime bank records one module setup cost. Set up both actual owners
    # at one trigger so that cost belongs to one real pytest setup phase.
    return {'fitted': fitted, 'reads': reads}


def test_every_adopted_powder_pattern_summary_matches_original_arrays(evidence):
    fitted = evidence['fitted']
    result = fitted['outcome']
    assert result.get('adopted') is True and 'misfit' in result, (
        'Every genuinely adopted fit carries its numerical powder-pattern misfit '
        'evidence on the native wire'
    )
    patterns = {row['dataset_id']: row for row in fitted['patterns']}
    assert (
        len(patterns) == 2 and {row['dataset_id'] for row in result['misfit']} == patterns.keys()
    ), (
        'The fit receipt includes each original powder pattern, rather than just '
        'the selected experiment'
    )
    for summary in result['misfit']:
        data = patterns[summary['dataset_id']]
        used = population(data)
        assert data['current'] and summary['current'] and summary['points'] == len(used), (
            'An adopted fit summary refers to the current captured native arrays and '
            'exact included population'
        )
        near(
            summary['weighted_rms'],
            weighted(data, used)[1],
            'Native overall misfit is the closed-form weighted residual RMS',
        )
        covered = []
        assert len(summary['regions']) == 8, (
            'Each measured powder pattern has eight bounded contiguous residual regions'
        )
        for region in summary['regions']:
            rows = [i for i in used if region['x_from'] <= data['x'][i] <= region['x_to']]
            assert region['points'] == len(rows) and rows, (
                'Every native summary region names and counts its actual rows'
            )
            mean, rms = weighted(data, rows)
            near(
                region['weighted_mean'],
                mean,
                'Native region signed residual follows an independent rational sum',
            )
            near(
                region['weighted_rms'],
                rms,
                'Native region RMS follows an independent weighted square sum',
            )
            covered += rows
        assert covered == used, (
            'Native residual regions cover the current included arrays exactly once'
        )
        quiet = [
            i for i in used if data['calculated'][i] - data['background'][i] < data['sigma'][i] / 2
        ]
        assert summary['background']['quiet_points'] == len(quiet), (
            'The native quiet background uses the declared half-sigma population'
        )
        if quiet:
            mean, rms = weighted(data, quiet, 'background')
            near(
                summary['background']['weighted_mean'],
                mean,
                'Native quiet background bias uses the original measured and background values',
            )
            near(
                summary['background']['weighted_rms'],
                rms,
                'Native quiet background RMS uses the original supplied sigmas',
            )
        expected = sorted(
            (peak(data, *window) for window in native_windows(data)),
            key=itemgetter('weighted_square_sum'),
            reverse=True,
        )[:5]
        assert len(summary['worst_peaks']) == len(expected), (
            'The native receipt retains the five worst supported reflection windows'
        )
        for actual, reference in zip(summary['worst_peaks'], expected, strict=True):
            assert actual['phase_id'] == reference['phase_id'], (
                'Native worst-reflection ordering retains phase identity'
            )
            for key, expected_value in reference.items():
                if key != 'phase_id':
                    near(
                        actual[key],
                        expected_value,
                        f'Native reflection {key} matches independent sums '
                        'over its original source rows',
                    )


@pytest.fixture(scope='module')
def reads(tmp_path_factory):
    actor = actor_in(tmp_path_factory.mktemp('misfit-reads') / 'actor', [[]])
    try:
        datasets = json.loads(actor.last['ui']['context'])['datasets']
        one, two = datasets
        calls = [
            {
                'tool': 'inspect_data',
                'call_id': 'named-rows',
                'arguments': {'dataset_id': one['id'], 'start': 3, 'count': 5},
            },
            base.tool_call(
                'inspect_data',
                'clamped-rows',
                dataset_id=two['id'],
                start=two['axis']['count'] - 2,
                count=9,
            ),
            base.tool_call(
                'inspect_data',
                'summary-read',
                dataset_id=one['id'],
                start=7,
                count=9,
                view='summary',
                partitions=3,
            ),
            base.tool_call(
                'inspect_data',
                'bragg-read',
                dataset_id=two['id'],
                start=0,
                count=1,
                source='bragg',
            ),
            base.tool_call('inspect_data', 'fifth-read', dataset_id=one['id'], start=0, count=1),
        ]
        actor.configure_turns([calls])
        send(actor, 1)
        first = replies(actor)
        again = [
            base.tool_call(
                'inspect_data', 'fresh-read-' + str(i), dataset_id=one['id'], start=4 + i, count=2
            )
            for i in range(4)
        ]
        actor.append_turn(again)
        send(actor, 2)
        receipt = {
            'first': first,
            'all': replies(actor),
            'calls': calls,
            'datasets': datasets,
            'again': again,
        }
        (actor.folder / 'read-budget-and-original-descriptions.json').write_text(
            json.dumps(receipt, indent=2) + '\n'
        )
        receipt['actor'] = actor
        yield receipt
    finally:
        actor.close()


def test_data_reads_share_four_call_budget_and_reset_only_on_new_turn(evidence):
    reads = evidence['reads']
    first = reads['first']
    assert all(first[call['call_id']]['success'] for call in reads['calls'][:4]), (
        'Four actual row/summary/Bragg reads across datasets share one allowed turn budget'
    )
    assert (
        not first['fifth-read']['success']
        and first['fifth-read']['value'].get('status') == 'refused'
    ), 'A fifth valid data read is refused before returning another native data slice'
    assert first['fifth-read']['value'].get('code') == 'refused', (
        'The fifth valid call is rejected by the read budget, not a malformed-range error'
    )
    assert 'data' not in first['fifth-read']['value'], (
        'A budget refusal cannot leak the fifth requested data slice'
    )
    assert all(reads['all'][call['call_id']]['success'] for call in reads['again']), (
        'A fresh genuine provider turn receives a new four-read allowance without '
        'clearing the session'
    )


def test_data_read_step_names_actual_dataset_and_rows_even_when_clamped(evidence):
    reads = evidence['reads']
    actor = reads['actor']
    descriptions = [
        actor.command('activity_description', row_id=row['id'])['reply']['description']
        for row in actor.last['ui']['messages']
        if (row.get('payload') or {}).get('tool') == 'inspect_data'
    ]
    (actor.folder / 'rendered-read-descriptions.json').write_text(
        json.dumps(descriptions, indent=2) + '\n'
    )
    for call in reads['calls'][:2]:
        data = reads['first'][call['call_id']]['value']['data']
        matching = [text for text in descriptions if data['dataset_id'] in text]
        assert matching, 'The actual rendered human step names the dataset it read'
        assert any(f'{data["start"] + 1} to {data["end"]}' in text for text in matching), (
            'The human step names the actual one-based rows returned, including a '
            'clamped end, with or without purpose metadata'
        )
