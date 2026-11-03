"""Observer-selection transport checks with independently saved scan columns."""

import copy

import pytest

from tests.system.py import test_scan_screen as screen


@pytest.fixture
def release_trace(monkeypatch):
    chosen = screen.files(screen.FULL)[:3]
    monkeypatch.setattr(screen, 'files', lambda _root: chosen)
    names = [path.name for path in chosen]

    def frame(index, generation, ms, calculated='transport fitted series'):
        x, y, _sigma = screen.measured(chosen[index])[0]
        return {
            'ms': ms,
            'running': True,
            'modelMeasured': screen.measured_hash(chosen[index]),
            'drawnMeasured': 'transport measured series',
            'drawnCalculated': calculated,
            'drawnPoints': [[x, y]],
            'finished': names,
            'patternGeneration': generation,
            'presentedGeneration': generation,
        }

    return {
        'heldMs': 100,
        'releasedMs': 1000,
        'releasedGeneration': 5,
        'finishedAtRelease': names[:2],
        'frames': [
            frame(0, 1, 0, 'transport template series'),
            frame(0, 5, 1010),
            frame(2, 6, 1100),
        ],
    }, frame


def test_scan_release_selection_keeps_held_redraw_diagnostic_and_checks_the_new_handover(
    release_trace,
):
    item, _frame = release_trace
    before = copy.deepcopy(item)
    records = screen.resumed_draws(item)
    assert len(records) == 1 and records[0]['presentedGeneration'] == 6, (
        'ADR-0029: a held-generation redraw is separate from a new presented handover'
    )
    assert item == before and len(item['frames']) == 3, (
        'ADR-0029: qualifying a new handover retains every raw drawing for validation'
    )
    screen.test_adaptive_takes_newest_finished_file_when_chart_becomes_free(
        {'desktop': {'results': {'adaptive': item}}}, 'desktop'
    )


@pytest.mark.parametrize('same_series', [False, True], ids=['changed-series', 'unchanged-series'])
def test_scan_release_observer_refuses_a_newly_applied_stale_file_even_when_redrawn(
    release_trace, same_series
):
    item, frame = release_trace
    stale = frame(
        0, 6, 1050, item['frames'][0]['drawnCalculated'] if same_series else 'stale series'
    )
    item['frames'].insert(2, stale)
    item['frames'][-1].update(patternGeneration=7, presentedGeneration=7)
    with pytest.raises(AssertionError, match='newest finished file'):
        screen.test_adaptive_takes_newest_finished_file_when_chart_becomes_free(
            {'desktop': {'results': {'adaptive': item}}}, 'desktop'
        )
    assert screen.resumed_draws(item)[0]['file'] == screen.files(screen.FULL)[0].name, (
        'ADR-0029: the first new handover retains the original newest-file bound'
    )


@pytest.mark.parametrize(
    'escape',
    [
        'missing-release',
        'zero-release',
        'float-release',
        'bool-release',
        'missing-frame',
        'negative-frame',
        'bool-frame',
        'ahead-presented',
    ],
)
def test_scan_release_observer_refuses_missing_or_incoherent_generation_evidence(
    release_trace, escape
):
    item, _frame = release_trace
    if escape == 'missing-release':
        del item['releasedGeneration']
    elif escape in {'zero-release', 'float-release', 'bool-release'}:
        item['releasedGeneration'] = {
            'zero-release': 0,
            'float-release': 5.5,
            'bool-release': True,
        }[escape]
    else:
        target = item['frames'][-1]
        if escape == 'missing-frame':
            del target['presentedGeneration']
        else:
            target['presentedGeneration'] = {
                'negative-frame': -1,
                'bool-frame': True,
                'ahead-presented': 7,
            }[escape]
    with pytest.raises(AssertionError, match='ADR-0029:'):
        screen.resumed_draws(item)
    assert len(item['frames']) == 3, (
        'ADR-0029: missing or incoherent evidence refuses instead of choosing a later frame'
    )


@pytest.mark.parametrize('escape', ['only-held', 'stopped', 'before-release'])
def test_scan_release_observer_requires_a_live_post_release_handover(release_trace, escape):
    item, _frame = release_trace
    if escape == 'only-held':
        item['frames'][-1]['presentedGeneration'] = item['releasedGeneration']
    elif escape == 'stopped':
        item['frames'][-1]['running'] = False
    else:
        item['frames'][-1]['ms'] = item['releasedMs'] - 1
    with pytest.raises(AssertionError, match='newest finished file'):
        screen.test_adaptive_takes_newest_finished_file_when_chart_becomes_free(
            {'desktop': {'results': {'adaptive': item}}}, 'desktop'
        )
    assert not screen.resumed_draws(item), (
        'ADR-0029: held-only, stopped and pre-release drawings cannot satisfy a live handover'
    )


@pytest.mark.parametrize('defect', ['none', 'model', 'drawing', 'running', 'later'])
def test_initial_lazy_read_transition_keeps_exact_template_drawing(defect):
    template = screen.template_measured(screen.FULL / 'experiments/d20.edi')
    pending = screen.measured(screen.files(screen.FULL)[0])[: len(template)]
    initial = {
        'running': False,
        'modelMeasured': screen.columns_hash(pending),
        'drawnMeasured': 'template measured series',
        'drawnCalculated': 'template calculated series',
        'drawnPoints': [[x, y] for x, y, _ in template],
    }
    item = {'frames': [initial]}
    if defect == 'model':
        initial['modelMeasured'] = screen.columns_hash(pending[:-1])
    elif defect == 'drawing':
        initial['drawnPoints'][0][1] += 0.125
    elif defect == 'running':
        initial['running'] = True
    elif defect == 'later':
        item['frames'].insert(0, dict(initial, modelMeasured=screen.columns_hash(template)))
    if defect == 'none':
        assert screen.shown(item) == [], (
            'The exact stopped lazy-read transition retains '
            'the independently saved template drawing'
        )
    else:
        with pytest.raises(AssertionError, match='independently saved measured columns'):
            screen.shown(item)
