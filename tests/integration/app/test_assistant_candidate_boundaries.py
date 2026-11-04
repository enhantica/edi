"""Provider receipts and restoration after a candidate changes its setup."""

import json

import pytest

from tests.integration.app.test_assistant_misfit_workflow import actor_in, replies, send
from tests.integration.app.test_assistant_review_receipts import fit_record
from tests.integration.py.assistant_misfit_reference import population, weighted
from tests.system.py import test_e11_t5_dev_native_integration as base

TRIAL_PATH = 'experiments[second].background[3].coef'


def call(tool, identity, **arguments):
    return base.tool_call(tool, identity, **arguments)


def record_receipts(actor, name, record):
    (actor.folder / name).write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    return record


def observe_calculate(folder):
    actor = actor_in(
        folder,
        [
            [
                call(
                    'set_parameters',
                    'edit-before-calculate',
                    values=[{'path': 'experiments[bank].background[1].coef', 'value': 7.25}],
                )
            ]
        ],
    )
    try:
        before = actor.command('pattern_inputs')['reply']['patterns']
        send(actor, 1)
        actor.until(lambda row: not row['ui']['project']['calculating'])
        after = actor.command('pattern_inputs')['reply']['patterns']
        actor.append_turn([call('diagnostics', 'after-calculate')])
        send(actor, 2)
        return record_receipts(
            actor,
            'ordinary-calculate.json',
            {'before': before, 'after': after, 'wire': replies(actor)},
        )
    finally:
        actor.close()


def prepare_combined_project(project):
    structure = project / 'structures/phase.edi'
    structure.with_name('phase2.edi').write_text(
        structure.read_text().replace('data_phase\n', 'data_phase2\n', 1), encoding='utf-8'
    )
    analysis = project / 'analysis/analysis.edi'
    analysis.write_text(
        analysis.read_text().replace('_fitting_mode.type joint', '_fitting_mode.type single'),
        encoding='utf-8',
    )
    bank = project / 'experiments/bank.edi'
    text = bank.read_text().replace('phase 0\n', 'phase 0.001\nphase2 0.001\n', 1)
    rows = ''.join(f'{40 + i / 10:.1f} {5 + i / 80:.6f} 1\n' for i in range(321))
    key = '_data.intensity_meas_su\n'
    bank.write_text(text.split(key)[0] + key + rows, encoding='utf-8')
    (project / 'experiments/second.edi').unlink()


def observe_combined(folder):
    actor = actor_in(
        folder,
        [[call('run_fit', 'combined-fit')]],
        prepare=prepare_combined_project,
    )
    try:
        send(actor, 1)
        actor.until(lambda row: not row['ui']['project']['calculating'])
        patterns = actor.command('pattern_inputs')['reply']['patterns']
        return record_receipts(
            actor, 'combined-fit.json', {'patterns': patterns, 'wire': replies(actor)}
        )
    finally:
        actor.close()


def setup_trial(first, endpoint):
    if endpoint == 'refusal':
        flags = [
            {'path': row['path'], 'free': False} for row in first['parameters'] if row['free']
        ]
    else:
        flags = [{'path': TRIAL_PATH, 'free': True}]
    return [
        call('set_free', 'candidate-flags', flags=flags),
        call(
            'add_relations',
            'candidate-relations',
            aliases=[{'id': 'trial_coefficient', 'path': TRIAL_PATH}],
            constraints=[
                {
                    'id': 'trial_constraint',
                    'expression': 'trial_coefficient = a - b',
                    'enabled': False,
                }
            ],
        ),
    ]


def stop_during_trial(actor):
    base._session_configure(actor, final_gate=str(actor.gate))
    actor.request('Prepare the next trial using the current native controls.')
    actor.until(
        lambda row: (
            row['ui']['can_cancel']
            and {'candidate-flags', 'candidate-relations'} <= replies(actor).keys()
        )
    )
    prepared = fit_record(actor)
    actor.command('cancel')
    actor.until(
        lambda row: not row['ui']['can_cancel'] and row['ui']['state'] in {'idle', 'interrupted'}
    )
    return prepared


def observe_trial(folder, endpoint):
    actor = actor_in(folder, [[call('run_fit', 'accepted-a')]])
    try:
        send(actor, 1)
        first = fit_record(actor)
        actor.append_turn(setup_trial(first, endpoint))
        second = None
        if endpoint == 'stop':
            prepared = stop_during_trial(actor)
        else:
            send(actor, 2)
            prepared = fit_record(actor)
            actor.append_turn([call('run_fit', 'candidate-b')])
            send(actor, 3)
            if endpoint == 'undo':
                second = fit_record(actor)
                actor.append_turn([
                    call('undo_fit', 'reject-b'),
                    call('inspect_project', 'after-rejection'),
                ])
                send(actor, 4)
        restored = fit_record(actor)
        return record_receipts(
            actor,
            f'trial-{endpoint}.json',
            {
                'accepted': first,
                'prepared': prepared,
                'candidate': second,
                'restored': restored,
                'wire': replies(actor),
                'interrupts': [
                    event['params']
                    for event in map(json.loads, actor.trace.read_text().splitlines())
                    if event.get('method') == 'turn/interrupt'
                ],
            },
        )
    finally:
        actor.close()


@pytest.fixture(scope='module')
def evidence(tmp_path_factory):
    root = tmp_path_factory.mktemp('candidate-boundaries')
    return {
        'calculate': observe_calculate(root / 'calculate'),
        'combined': observe_combined(root / 'combined'),
        **{end: observe_trial(root / end, end) for end in ('undo', 'stop', 'refusal')},
    }


def test_calculate_misfit_reaches_provider_without_any_fit(evidence):
    observed = evidence['calculate']
    wire = observed['wire']
    assert wire['edit-before-calculate']['success'] and wire['after-calculate']['success'], (
        'The ordinary edit and the subsequent native diagnostics both complete'
    )
    assert observed['before'][0]['calculated'] != observed['after'][0]['calculated'], (
        'The edit reaches a real newly calculated powder pattern'
    )
    patterns = {p['dataset_id']: p for p in observed['after']}
    misfit = wire['after-calculate']['value'].get('misfit', [])
    assert {p['dataset_id'] for p in misfit} == patterns.keys(), (
        'Provider diagnostics carry the result of ordinary Calculate for each powder dataset'
    )
    for summary in misfit:
        pattern = patterns[summary['dataset_id']]
        rows = population(pattern)
        assert rows and summary['coverage'] == 'calculation' and summary['current'], (
            'The published diagnostic identifies the completed calculation and its usable rows'
        )
        assert summary['weighted_rms'] == pytest.approx(weighted(pattern, rows)[1]), (
            'Calculate misfit agrees with independent arithmetic over the newly published columns'
        )


@pytest.mark.parametrize('endpoint', ['undo', 'stop', 'refusal'])
def test_candidate_endpoint_restores_accepted_flags_relations_and_record(evidence, endpoint):
    record = evidence[endpoint]
    accepted, prepared = record['accepted'], record['prepared']
    wire = record['wire']
    analysis = 'analysis/analysis.edi'
    assert (
        wire['accepted-a']['value'].get('adopted')
        and '_fit_result.result_kind' in accepted['files'][analysis]
    ), 'Fit A is an actual adopted and serialized native fit'
    assert wire['candidate-flags']['success'] and wire['candidate-relations']['success'], (
        'Both ordinary candidate setup operations publish before the endpoint'
    )
    before_flags = {p['path']: p['free'] for p in accepted['parameters']}
    prepared_flags = {p['path']: p['free'] for p in prepared['parameters']}
    assert (
        prepared_flags != before_flags
        and prepared['aliases'] != accepted['aliases']
        and prepared['constraints'] != accepted['constraints']
    ), 'Candidate setup reaches changed free flags, aliases and constraints'
    if endpoint == 'undo':
        assert wire['candidate-b']['value'].get('adopted') and wire['reject-b']['success'], (
            'Fit B is adopted before the native Undo rejects it'
        )
        before_values = {p['path']: p['value'] for p in prepared['parameters']}
        assert any(
            p['value'] != before_values[p['path']] for p in record['candidate']['parameters']
        ), 'Fit B changes a real scientific value before its rejection'
    elif endpoint == 'refusal':
        assert not wire['candidate-b']['success'], 'The all-fixed candidate is genuinely refused'
    else:
        assert len(record['interrupts']) == 1, 'Stop interrupts the actual active provider turn'
    assert record['restored'] == accepted, (
        'The endpoint retains the accepted serialized fit, values, flags and relations'
    )


def test_accepted_fit_currentness_reaches_both_provider_roles(evidence):
    wire = evidence['undo']['wire']
    assert wire['reject-b']['success'] and wire['after-rejection']['success'], (
        'The model receives real Undo and inspection replies for the same accepted fit'
    )
    result = wire['reject-b']['value']
    state = wire['after-rejection']['value'].get('native_state', {})
    assert (result.get('fit_result_current'), state.get('fit_result_current')) == (True, True), (
        'Both the native Undo Result and subsequent NativeState report accepted-fit currentness'
    )


def test_native_fit_wire_retains_real_combined_peak(evidence):
    observed = evidence['combined']
    fit = observed['wire']['combined-fit']
    assert fit['success'] and fit['value'].get('adopted'), (
        'The ordinary single fit actually adopts on the two coincident authored phases'
    )
    patterns = {p['dataset_id']: p for p in observed['patterns']}
    bank = patterns['bank']
    assert any(c > b for c, b in zip(bank['calculated'], bank['background'], strict=True)), (
        'The original calculated columns have measurable above-background peak support'
    )
    phases = {phase['phase_id']: set(phase['positions']) for phase in bank['phases']}
    shared = phases['phase'] & phases['phase2']
    assert shared, 'The captured native pattern contains coincident reflections'
    summaries = {p['dataset_id']: p for p in fit['value'].get('misfit', [])}
    combined = [p for p in summaries['bank']['worst_peaks'] if p.get('combined')]
    assert combined, 'The real provider reply includes a combined peak on the overlapping phases'
    assert any(
        {'phase', 'phase2'} <= set(p['phase_ids']) and shared & set(p['positions'])
        for p in combined
    ), 'A combined provider peak identifies both phases and their actual shared position'
