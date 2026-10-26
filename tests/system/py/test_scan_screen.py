"""Drawn scan patterns and the per-machine Extras choice, on both production hosts."""

from __future__ import annotations

import copy
import json

import pytest

from tests.fixtures.app_environment.observations import Observations
from tests.fixtures.scan_app.harness import (
    FULL,
    columns_hash,
    files,
    measured,
    measured_hash,
    template_measured,
)
from tests.fixtures.scan_screen.harness import MODES, observation


@pytest.fixture(scope='module')
def screens(tmp_path_factory):
    root = tmp_path_factory.mktemp('scan-screen')

    def observe(backend):
        result = observation(backend, root)
        (root / (backend + '-evidence.json')).write_text(json.dumps(result, indent=2))
        return result

    return Observations(observe)


# Separate module fixtures account for setup and isolate an unavailable host.
@pytest.fixture(scope='module')
def desktop_screen_capture(screens):
    return screens['desktop']


@pytest.fixture(scope='module')
def browser_screen_capture(screens):
    return screens['browser']


@pytest.fixture(autouse=True)
def prepare_screen_capture(request):
    backend = request.node.callspec.params['backend']
    request.getfixturevalue(backend + '_screen_capture')


def shown(item):
    names = {measured_hash(path): path.name for path in files(FULL)}
    template_columns = template_measured(FULL / 'experiments/d20.edi')
    template = columns_hash(template_columns)
    pending_template = columns_hash(measured(files(FULL)[0])[: len(template_columns)])
    records = []
    last = None
    raw = {path.name: {x: y for x, y, _ in measured(path)} for path in files(FULL)}
    initial = item['frames'][0] if item['frames'] else {}
    initial_series = (initial.get('drawnMeasured'), initial.get('drawnCalculated'))
    for frame in item['frames']:
        identity = names.get(frame['modelMeasured'])
        assert (
            identity
            or frame['modelMeasured'] == template
            or (
                frame is initial
                and not frame['running']
                and frame['modelMeasured'] == pending_template
                and frame['drawnPoints'] == [[x, y] for x, y, _ in template_columns]
            )
        ), (
            'Scan chart: every synchronized model must identify independently saved '
            'measured columns, including the exact initial lazy-read transition'
        )
        if identity:
            assert frame['drawnPoints'] and all(
                raw[identity].get(round(x, 4)) == y for x, y in frame['drawnPoints']
            ), (
                'Scan chart: the measured points actually synchronized to the screen '
                'must belong to the independently identified file'
            )
        if (frame['drawnMeasured'], frame['drawnCalculated']) == initial_series:
            assert frame['modelMeasured'] == initial['modelMeasured'], (
                'Scan chart: an unchanged drawing cannot claim a changed measured file'
            )
            continue
        if identity and identity != last:
            assert frame['drawnMeasured'] and frame['drawnCalculated'], (
                'Scan chart: a displayed file requires measured and calculated series at a '
                'real frame swap'
            )
            assert identity in [name.rsplit('/', 1)[-1] for name in frame['finished']], (
                'Scan chart: a drawn dataset must already be finished in the actual worker receipt'
            )
            records.append(dict(frame, file=identity))
            last = identity
        elif identity and records and not frame['running']:
            records[-1] = dict(frame, file=identity)
    return records


def resumed_draws(item):
    # Keep independent measured-column and actual drawn-point validation for every frame,
    # including the held pattern's redraw. Only the ADR's new handover predicate is qualified.
    shown(item)
    released = item.get('releasedGeneration')
    assert isinstance(released, int) and not isinstance(released, bool) and released > 0, (
        'ADR-0029: release observations must identify the actual pattern held before reopening'
    )
    names = {measured_hash(path): path.name for path in files(FULL)}
    records = []
    for frame in item['frames']:
        generation, presented = frame.get('patternGeneration'), frame.get('presentedGeneration')
        assert (
            all(
                isinstance(value, int) and not isinstance(value, bool) and value >= 0
                for value in (generation, presented)
            )
            and presented <= generation
        ), 'ADR-0029: every swapped frame binds its model and presented pattern generations'
        if not frame['running'] or frame['ms'] < item['releasedMs'] or presented <= released:
            continue
        identity = names.get(frame['modelMeasured'])
        assert identity and frame['drawnMeasured'] and frame['drawnCalculated'], (
            'ADR-0029: a new handover binds actual saved data and both drawn series'
        )
        records.append(dict(frame, file=identity))
    return records


@pytest.mark.parametrize('backend', ['desktop', 'browser'])
def test_adaptive_draws_changed_pattern_while_scan_running(screens, backend):
    item = screens[backend]['results']['adaptive']
    records = shown(item)
    running = [row for row in records if row['running']]
    assert (
        len(running) >= 2
        and len({row['drawnMeasured'] for row in running}) >= 2
        and len({row['drawnCalculated'] for row in running}) >= 2
    ), (
        'ADR-0029: adaptive mode must draw changed measured and calculated patterns '
        'while the actual scan is running'
    )


@pytest.mark.parametrize('backend', ['desktop', 'browser'])
@pytest.mark.parametrize('mode', MODES)
def test_scan_pattern_mode_draws_its_promised_files(screens, backend, mode, request):
    item = screens[backend]['results'][mode]
    request.node.add_report_section(
        'call',
        'scan chart diagnostics',
        json.dumps(
            {
                'backend': backend,
                'mode': mode,
                'error': item.get('error'),
                'followEvents': item.get('followEvents', 'unavailable in this capture'),
                'frames': [
                    {key: value for key, value in frame.items() if key != 'drawnPoints'}
                    for frame in item['frames']
                ],
            },
            indent=2,
        ),
    )
    assert not item.get('error'), (
        'Scan chart: each selected mode must complete through the actual app worker'
    )
    records = shown(item)
    expected = [path.name for path in files(FULL)]
    assert records and records[-1]['file'] == expected[-1] and not records[-1]['running'], (
        'Scan chart: every mode must draw the final dataset after the worker has stopped'
    )
    assert [name.rsplit('/', 1)[-1] for name in records[-1]['finished']] == expected, (
        'Scan chart: the final drawing must follow the actual completion of every input file'
    )
    if mode == 'every':
        assert [row['file'] for row in records] == expected, (
            'Scan chart: every pattern means every completed file reaches a frame swap in order'
        )
    elif mode == 'second':
        live = [row for row in records if row['running']]
        assert live and all(
            b['ms'] - a['ms'] >= 1000 for a, b in zip(live, live[1:], strict=False)
        ), (
            'Scan chart: about once per second draws during the scan with no two live '
            'patterns less than one second apart'
        )
    elif mode == 'end':
        assert [row['file'] for row in records] == [expected[-1]] and not any(
            row['running'] for row in records
        ), 'Scan chart: only at the end draws only the final file after the scan has stopped'
    else:
        positions = {name: i for i, name in enumerate(expected)}
        assert all(
            positions[a['file']] < positions[b['file']]
            for a, b in zip(records, records[1:], strict=False)
        ), (
            'ADR-0029: adaptive frames advance through completed files without '
            'replaying an older pattern'
        )


@pytest.mark.parametrize('backend', ['desktop', 'browser'])
@pytest.mark.parametrize('mode', MODES)
def test_extras_choice_defaults_adaptive_and_survives_host_restart(screens, backend, mode):
    item = screens[backend]['results'][mode]
    assert item['extras'] and item['label'] and item['selectorUsable'], (
        'Scan preferences: Extras must expose the Pattern updates during a scan selector'
    )
    options = item['options']
    expected = {
        'Adaptive',
        'About once a second',
        'Every pattern, fit waits for the display',
        'Every pattern, display catches up',
        'Only at the end',
    }
    assert len(options) == len(expected) and set(options) == expected, (
        'Scan preferences: the selector offers all five distinct owner-requested modes'
    )
    expected_mode = {
        'adaptive': 'Adaptive',
        'second': 'About once a second',
        'every': 'Every pattern, fit waits for the display',
        'end': 'Only at the end',
    }[mode]
    assert item['selected'] == expected_mode, (
        'Scan preferences: the observer selects the promised mode by its exact displayed label'
    )
    assert 'adaptive' in item['initial'].lower(), (
        'Scan preferences: a fresh machine must default to adaptive updates'
    )
    assert (
        item['selected']
        and item['saved']['selected'] == item['selected'] == item['reopened']['initial']
    ), (
        'Scan preferences: every choice must survive a real desktop restart or '
        'browser reload on the same machine'
    )


@pytest.mark.parametrize('backend', ['desktop', 'browser'])
def test_adaptive_takes_newest_finished_file_when_chart_becomes_free(screens, backend):
    item = screens[backend]['results']['adaptive']
    records = resumed_draws(item)
    finished = item.get('finishedAtRelease', [])
    assert finished and item.get('releasedMs', 0) > item.get('heldMs', 0), (
        'ADR-0029: the real chart must be hidden and made free after worker files finish'
    )
    positions = {path.name: index for index, path in enumerate(files(FULL))}
    resumed = [row for row in records if row['ms'] >= item['releasedMs'] and row['running']]
    assert (
        resumed and positions[resumed[0]['file']] >= positions[finished[-1].rsplit('/', 1)[-1]]
    ), (
        'ADR-0029: when the chart becomes free its first live frame must be the '
        'newest finished file'
    )


@pytest.mark.parametrize('backend', ['desktop', 'browser'])
def test_stale_drawn_points_cannot_claim_a_new_model_file(screens, backend):
    item = copy.deepcopy(screens[backend]['results']['adaptive'])
    known = {measured_hash(path): path.name for path in files(FULL)}
    final = next(
        (frame for frame in reversed(item['frames']) if frame['modelMeasured'] in known), None
    )
    assert final is not None, (
        'Scan observer escape: the real app must produce a final measured-file frame'
    )
    other = next(path for path in files(FULL) if path.name != known[final['modelMeasured']])
    final['modelMeasured'] = measured_hash(other)
    item['frames'] = [item['frames'][0], final]
    with pytest.raises(AssertionError, match='independently identified file'):
        shown(item)
