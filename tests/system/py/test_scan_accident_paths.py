"""Ordinary user accidents from review 6; observe real scientific and rendered outcomes."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
from itertools import pairwise
from pathlib import Path

import pytest

from tests.conftest import _build_native_observer, crysta_reference_source  # noqa: PLC2701
from tests.fixtures.scan_app.accident_inputs import project
from tests.fixtures.scan_app.harness import (
    Harness,
    csv_text,
    files,
    measured_hash,
    projection_csv,
    read_csv,
    scale_project,
)


@pytest.fixture(scope='module')
def accidents(tmp_path_factory):
    root = tmp_path_factory.mktemp('scan-accidents')
    library, preload = _build_native_observer(root)
    return root, Harness(root, library, preload)


@pytest.mark.parametrize(
    'action', ['fit', 'value', 'free', 'setting', 'reset', 'undo', 'saveas', 'start-scan']
)
def test_pending_dataset_actions_keep_the_fitted_file_and_newer_scientific_state(
    accidents, action
):
    root, harness = accidents
    target = project(root / ('pending-' + action), fitted=action != 'start-scan')
    observed = harness.invoke(
        'pending', target, 'start-fitting' if action == 'fit' else action, observe=True
    )
    assert observed['blocked'] and observed['pending'], (
        'Pending selection: the accident action must reach a real unresolved dataset read'
    )
    assert observed['projected'], 'Pending selection: the newest scientific state must settle'
    if action == 'fit':
        assert not observed['admitted'] and observed['refusal'], (
            'Pending single Fit: refuse visibly until the chosen measured dataset is applied'
        )
        assert observed['nativeInputs'] and all(
            value == measured_hash(files(target)[1]) for value in observed['nativeInputs']
        ), 'Pending Fit: every actual optimizer snapshot must contain the selected dataset bytes'
        if observed['after']['held']:
            assert Path(observed['after']['template']).name == files(target)[1].name, (
                'Pending Fit: a retained result designates the dataset that was actually fitted'
            )
    elif action in {'value', 'free', 'setting'}:
        assert not observed['admitted'] and observed['refusal'], (
            'Pending edit: value, free flag and minimizer settings refuse visibly until '
            'the chosen measured dataset is applied'
        )
    elif action == 'start-scan':
        assert observed['admitted'], (
            'Pending scan: Start remains admitted while a view read is pending'
        )
        rows = read_csv(observed['files']['results.csv'])
        assert {Path(row['file_path']).name for row in rows} == {
            path.name for path in files(target)
        }, 'Pending scan: fit each actual scan file and retain its own dataset identity'
        assert observed['work'] == [
            ['pending-scan', path.name, measured_hash(path)] for path in files(target)
        ], 'Pending scan: each actual optimizer receives its own independently hashed payload'
        assert not observed['after']['following'], (
            'Pending scan: Follow ends with the worker; its last dataset remains shown'
        )
        assert observed['after']['selected'] == len(files(target)) - 1, (
            'Pending scan: an older chosen read cannot overwrite the newest followed dataset'
        )
        assert observed['measuredHash'] == measured_hash(files(target)[-1]), (
            'Pending scan: the shown measurement matches the newest followed dataset bytes'
        )
    elif action == 'reset':
        assert observed['admitted'], 'Pending Reset: clears results while a view read is pending'
        assert all(value is None for value in observed['files'].values()) and all(
            not row['fitOutcome'] for row in observed['after']['rows']
        ), 'Pending Reset: older captured rows cannot reinstate cleared dataset fit facts'
    elif action == 'undo':
        assert observed['admitted'], (
            'Pending Undo: restores scan results while a view read is pending'
        )
        assert all(row['fitOutcome'] for row in observed['after']['rows']), (
            'Pending Undo: older unfitted projections cannot erase the restored fitted rows'
        )
    else:
        assert observed['admitted'] and (target.parent / (target.name + '-saved')).is_dir(), (
            'Pending Save As: admitted destination receives the project during a view read'
        )


def reset_observation(accidents):
    root, harness = accidents
    key = root / 'reset-state.json'
    if not key.exists():
        target = project(root / 'reset-state')
        key.write_text(json.dumps(harness.invoke('reset-state', target)))
    return json.loads(key.read_text())


def test_reset_after_a_single_fit_clears_every_visible_and_held_result(accidents):
    observed = reset_observation(accidents)
    assert observed['scan']['completed'] == 3 and observed['priorSingle']['held'], (
        'Reset witness: an actual scan and retained single fit must precede the user reset'
    )
    reset = observed['reset']
    assert not reset['held'] and all(not row['fitOutcome'] for row in reset['rows']), (
        'Reset fits: the template and every dataset lose all prior fit facts, '
        'including single fits'
    )
    assert all(value is None for value in observed['resetFiles'].values()), (
        'Reset fits: CSV, per-file provenance and run summary are all absent'
    )
    assert not any(row['metric'] == 'Overall status' for row in reset['summary']), (
        'Reset fits: the status/results view no longer displays the removed run or single outcome'
    )


def test_one_reset_undo_restores_the_whole_prior_fit_state(accidents):
    observed = reset_observation(accidents)
    assert observed['filesRestored'], 'Reset Undo: every prior output byte is restored as one step'
    before, after = observed['beforeReset'], observed['undoReset']
    for field in (
        'parameterFacts',
        'parameters',
        'rows',
        'summary',
        'held',
        'template',
        'stale',
        'evolutionStale',
    ):
        assert after[field] == before[field], (
            'Reset Undo: parameter state, dataset outcomes, summary kind/time, template and stale '
            'markers return together to their complete prior state; '
            f'changed observable: {field}'
        )


@pytest.mark.parametrize('state', ['undoSingle', 'reopenedUndoSingle'])
def test_single_fit_undo_restores_the_scan_summary_live_and_after_reopening(accidents, state):
    observed = reset_observation(accidents)
    assert not observed['undoSaveError'], 'Single Undo: Save As of the restored scan must succeed'
    assert observed[state]['summary'] == observed['priorScan']['summary'], (
        'Single Undo: the prior scan outcome, file counts and run time replace the single summary '
        'both live and after saving and reopening'
    )


@pytest.mark.parametrize('action', ['reset', 'undo'])
@pytest.mark.parametrize('output', [0, 1, 2], ids=['csv', 'provenance', 'run-summary'])
def test_storage_failure_and_failed_rollback_cannot_lose_a_prior_output(accidents, action, output):
    root, harness = accidents
    observed = harness.invoke(
        'io-rollback', project(root / f'io-{action}-{output}'), action, output
    )
    assert observed['hit'] > 0, (
        'Output transaction: the storage failure must reach a real mutation of its selected output'
    )
    assert observed['refusal'], 'Output transaction: a storage refusal is visible to the user'
    for value in observed['before'].values():
        if value is not None:
            digest = hashlib.sha256(value.encode()).hexdigest()
            assert digest in observed['retained'], (
                'Output transaction: every prior output remains durably recoverable even when '
                'the initial operation and subsequent rollback writes both fail'
            )
    for field in (
        'parameterFacts',
        'parameters',
        'rows',
        'summary',
        'held',
        'template',
        'stale',
        'evolutionStale',
    ):
        assert observed['afterState'][field] == observed['beforeState'][field], (
            'Output transaction: a refused Reset or Undo keeps the entire previous scientific '
            'and displayed fit state together'
        )


@pytest.mark.parametrize('edit', ['value', 'free', 'setting'])
def test_continue_keeps_old_generation_marks_through_save_reopen_and_reset_undo(accidents, edit):
    root, harness = accidents
    observed = harness.invoke('mixed', project(root / ('mixed-' + edit)), edit, observe=True)
    assert observed['first']['completed'] == 1 and not observed['editError'], (
        'Mixed-generation witness: a stopped prefix precedes a real admitted template edit'
    )
    assert observed['prefixKept'], (
        'Continue fitting: every retained prefix byte survives the attempt'
    )
    continued = observed['continued']
    assert continued['completed'] == 2 or (
        edit == 'free'
        and continued['completed'] == 0
        and (continued['refusal'] or continued['after']['lastError'])
    ), (
        'Continue fitting: compatible value/settings edits fit only missing files; a changed '
        'free-column schema either completes or names its refusal without replacing old rows'
    )
    assert not observed['saveError'], 'Mixed generation: Save As of retained results must succeed'
    for name in ('mixed', 'reopened', 'undoReset'):
        assert observed[name]['stale'] and observed[name]['evolutionStale'], (
            'Mixed generation: retained old rows keep their out-of-date warning after Continue, '
            'Save As, reopening and Reset Undo'
        )
    assert observed['fresh']['completed'] == 3 and not observed['freshState']['stale'], (
        'Mixed generation: only Reset followed by a complete fresh run clears the old-generation '
        'warning'
    )


def box_bounds(observed):
    x0, x1, y0, y1 = observed['before']
    sx, sy = observed['start']
    ex, ey = observed['end']
    xs = [x0 + value / observed['width'] * (x1 - x0) for value in (sx, ex)]
    ys = [y1 - value / observed['height'] * (y1 - y0) for value in (sy, ey)]
    return [min(xs), max(xs), min(ys), max(ys)]


@pytest.mark.parametrize(
    'gesture',
    [
        'left',
        'right',
        'horizontal',
        'vertical',
        'diagonal',
        'wheel',
        'wheel-out',
        'wheel-zero',
        'axis',
        'parameter',
    ],
)
def test_real_evolution_pointer_gestures_keep_selection_and_valid_viewports(accidents, gesture):
    root, harness = accidents
    target = project(root / ('gesture-' + gesture), fitted=True)
    rows = read_csv((target / 'analysis/results.csv').read_text())
    for row in rows:
        row['cosio.cell.length_a.uncertainty'] = '0'
        row['cosio.cell.length_c'] = repr(13.75 + rows.index(row) * 0.002)
        row['cosio.cell.length_c.uncertainty'] = '0'
    (target / 'analysis/results.csv').write_text(csv_text(rows))
    observed = harness.invoke('gestures', target, gesture)
    assert all(math.isfinite(value) for value in observed['after']) and all(
        observed['after'][index] < observed['after'][index + 1] for index in (0, 2)
    ), 'Evolution gestures: every rendered axis retains a finite positive span'
    if gesture == 'left':
        assert observed['selection'] == 1, (
            'Evolution point click: the positive control selects the actual rendered middle point'
        )
    else:
        assert observed['selection'] == observed['beforeSelection'], (
            'Evolution gestures: right reset and drag zoom cannot select a dataset '
            'as a side effect'
        )
    if gesture in {'axis', 'parameter'}:
        assert not observed['zoom'], (
            'Evolution choice: changing the actual parameter or x mode releases its old viewport'
        )
    elif gesture in {'wheel', 'wheel-out', 'wheel-zero'}:
        x0, x1, y0, y1 = observed['before']
        factor = {'wheel': 0.8, 'wheel-out': 1.25, 'wheel-zero': 1}[gesture]
        anchor = x0 + 0.4 * (x1 - x0)
        assert observed['after'] == pytest.approx([
            anchor - (anchor - x0) * factor,
            anchor + (x1 - anchor) * factor,
            y0,
            y1,
        ]), (
            'Evolution wheel: the rendered range follows pointer-centred scale, '
            'including zero delta'
        )
    elif gesture in {'right', 'horizontal', 'vertical'}:
        assert observed['after'] == pytest.approx(observed['before']), (
            'Evolution gestures: right reset restores the data viewport and a zero-width or '
            'zero-height box leaves it unchanged'
        )
    elif gesture == 'diagonal':
        assert observed['after'] == pytest.approx(box_bounds(observed)), (
            'Evolution drag: the actual plotted bounds equal the pointer box in data coordinates'
        )


def test_new_worker_rows_preserve_the_users_effective_evolution_zoom(accidents):
    root, harness = accidents
    observed = harness.invoke('live-zoom', project(root / 'live-zoom'))
    during = observed['during']
    assert observed['run']['completed'] == 3 and len(during) == 3 and during[0]['zoom'], (
        'Live Evolution witness: a real wheel zoom precedes further actual worker completions'
    )
    for frame in during[1:]:
        assert frame['axes'] == pytest.approx(during[0]['axes']), (
            'Live Evolution: incoming results retain the user viewport until an explicit reset '
            'or changed parameter/axis choice'
        )
    assert observed['axes'] == pytest.approx(during[0]['axes']), (
        'Live Evolution: terminal result reload also preserves the user viewport'
    )


@pytest.mark.parametrize('route', ['core', 'gui'])
@pytest.mark.parametrize('axis', ['cw', 'tof'])
@pytest.mark.parametrize('shape', ['ordinary', 'collapsed'])
def test_range_edit_and_save_refuse_collapsed_steps_or_preserve_every_point(
    accidents, axis, shape, route
):
    root, harness = accidents
    engine = crysta_reference_source()
    spec = importlib.util.spec_from_file_location(
        'range_input', engine / 'tests/fixtures/scan_range/range_input.py'
    )
    inputs = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(inputs)
    target, _ = inputs.input_project(
        engine, root / f'range-{axis}-{shape}-{route}', axis, 'ordinary'
    )
    observed = harness.invoke('range-accident', target, axis, shape, route)
    assert 'error' not in observed, 'Range witness: both ordinary saved experiment types must load'
    if not observed['admitted']:
        assert shape == 'collapsed' and observed['refusal'], (
            'Range admission: collapse is refused visibly while ordinary finite grids '
            'remain usable'
        )
        assert observed['grid'] == observed['before'], (
            'Range refusal: invalid range admission preserves all previous grid points'
        )
        return
    values = observed['grid']
    assert all(math.isfinite(value) for value in values) and all(
        left < right for left, right in pairwise(values)
    ), 'Range admission: every accepted positive step advances to a distinct double point'
    assert not observed['saveError'], (
        'Range save: a finite admitted grid cannot reach a zero-step saver candidate'
    )
    assert values == observed['reopened'], (
        'Range save: every grid point survives reopening exactly'
    )


@pytest.mark.parametrize('damage', ['csv', 'sidecar-json', 'sidecar-types', 'foreign-path'])
def test_damaged_retained_results_are_visible_and_cannot_be_replaced_by_start(accidents, damage):
    root, harness = accidents
    target = project(root / ('damaged-' + damage), fitted=True)
    csv = target / 'analysis/results.csv'
    if damage == 'csv':
        csv.write_text(csv.read_text().replace('10.126', 'XX.XXX'))
    elif damage == 'foreign-path':
        csv.write_text(csv.read_text().replace('experiments/d20_scan/', '/foreign/d20_scan/'))
    elif damage == 'sidecar-json':
        (target / 'analysis/scan-run.json').write_text('{"template":')
    else:
        (target / 'analysis/scan-run.json').write_text(
            '{"template":17,"seconds":"unknown","outcome":[],"last":null}'
        )
    observed = harness.invoke('result-boundary', target)
    before = observed['before']
    assert before['lastError'] or before['unavailableReason'], (
        'Damaged results: opening a corrupt index/provenance or foreign dataset identity names '
        'its refusal instead of assuming a current legacy run'
    )
    assert not observed['run']['entered'] and observed['unchanged'], (
        'Damaged results: Start cannot silently take or replace invalid retained result files; '
        'Reset is the explicit recovery action'
    )


def test_an_externally_changed_indexed_row_never_becomes_a_template_value(accidents):
    root, harness = accidents
    observed = harness.invoke('indexed-edit', project(root / 'indexed-edit', fitted=True))
    assert observed['error'] or observed['patternError'] or observed['value'] == 10.126, (
        'Changed indexed row: selection retains validated immutable bytes or reports its changed '
        'invalid number; it never silently presents a fallback template value as a fitted result'
    )


def test_changing_the_iteration_limit_cannot_reclassify_a_retained_result(accidents):
    root, harness = accidents
    observed = harness.invoke('outcome-settings', project(root / 'outcome-settings', fitted=True))
    assert observed['unchanged'], (
        'Retained outcome witness: the fit-setting edit does not refit rows'
    )
    assert [row['fitOutcome'] for row in observed['before']] == [
        row['fitOutcome'] for row in observed['after']
    ], (
        "Retained outcomes: changing today's iteration cap cannot change an earlier "
        'producing reason'
    )


def test_opening_a_fitted_scan_keeps_unselected_payload_reads_lazy(accidents):
    root, harness = accidents
    target = project(root / 'lazy-open', fitted=True, count=9)
    observed = harness.invoke('result-boundary', target, observe=True)
    allowed = {str(path.resolve()) for path in files(target)[:5]}
    reads = []
    for record in observed['trace']:
        columns = record.split('\t')
        if columns[0].startswith(('open', 'fopen', 'freopen')) and len(columns) > 1:
            path = Path(columns[1])
            if path.suffix == '.dat' and path.parent == target / 'experiments/d20_scan':
                reads.append(str(path.resolve()))
    assert reads, (
        'Lazy open witness: the observer reaches an actual selected measured payload read'
    )
    assert str(files(target)[0].resolve()) in reads, (
        'Lazy open witness: the observer reaches the actual initially shown dataset address'
    )
    assert set(reads) <= allowed, (
        'Lazy scan opening: digesting/reopening retained results cannot read unselected dataset '
        'payloads beyond the shown dataset and four upcoming resource addresses'
    )


@pytest.mark.parametrize('count', [5000, 5001, 20001])
def test_evolution_rebuild_keeps_whole_range_extrema_and_original_dataset_values(accidents, count):
    root, harness = accidents
    target = scale_project(harness, root / f'column-{count}', count)
    projection_csv(target, count)
    observed = harness.invoke('evolution', target)
    assert len(observed['columns']) == 1, 'Evolution rebuild: expose the synthetic fitted column'
    points = next(axis['points'] for axis in observed['columns'][0]['axes'] if axis['mode'] == 1)
    indexed = {round(point[0]) - 1: point for point in points}
    assert 0 < len(points) <= 5000, 'Evolution rebuild: retain a bounded nonempty drawn column'
    assert len(indexed) == len(points), 'Evolution rebuild: each drawn dataset occurs once'
    for index, point in indexed.items():
        value = 10.125 + ((index * 37) % 1001) / 100000
        error = 0.000125 + (index % 7) / 1000000
        assert point == pytest.approx([index + 1, value, value - error, value + error]), (
            'Evolution rebuild: dataset identity, value and error endpoints equal the '
            'independent closed-form CSV cells'
        )
    if count <= 5000:
        assert set(indexed) == set(range(count)), (
            'Evolution rebuild: retain every small-column point'
        )
    else:
        # Labelled regression pin: IEEE double uniform buckets over the WHOLE x range.
        # Scientific values remain independent closed forms; an incremental local-range
        # partition fails this witness.
        buckets = {}
        for index in range(count):
            bucket = min(2499, int(index / (count - 1) * 2500))
            buckets.setdefault(bucket, []).append(index)
        for candidates in buckets.values():
            minimum = min(candidates, key=lambda index: (index * 37) % 1001)
            maximum = max(candidates, key=lambda index: (index * 37) % 1001)
            assert {minimum, maximum} <= set(indexed), (
                'Evolution rebuild: preserve the independent minimum and maximum of every '
                'whole-range regression bucket even across the streaming threshold'
            )
