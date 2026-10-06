"""Actual worker/view-model contracts; reference values come from the driver and disk."""

from __future__ import annotations

import copy
import hashlib
import json
import re
import struct
from pathlib import Path

import pytest

from tests.conftest import _build_native_observer  # noqa: PLC2701 - shared native input observer
from tests.fixtures.scan_app.harness import (
    FULL,
    SMALL,
    Harness,
    copy_project,
    csv_text,
    files,
    measured,
    measured_hash,
    projection_csv,
    read_csv,
    scale_project,
)

MODES = ('sequential', 'independent')
DATASETS = range(162)  # Packet: run 01 of the frozen 324-file source, exactly 162 files.


def assert_cell_row(actual, expected):
    assert actual == expected, (
        'Scan run, consistency: every CSV cell equals the independent driver output'
    )


def assert_work(actual, expected, stage, common_hash=None):
    relevant = [row[1:] for row in actual if row[0] == stage]
    assert relevant == [[file.name, common_hash or measured_hash(file)] for file in expected], (
        'Stop and continue / scan run: optimizer entries identify exactly the intended '
        'files and full measured columns'
    )


@pytest.fixture(scope='module')
def execution(tmp_path_factory):
    root = tmp_path_factory.mktemp('scan-app-execution')
    library, preload = _build_native_observer(root)
    harness = Harness(root, library, preload)
    observed = {'harness': harness, 'root': root, 'modes': {}}
    full_observations(harness, root, observed)
    transition_observations(harness, root, observed)
    scale_observations(harness, root, observed)
    return observed


def full_observations(harness, root, observed):
    for mode in MODES:
        source = copy_project(FULL, root / (mode + '-reference'), mode)
        reference = harness.python_reference(source)
        rows = read_csv(reference.get('csv', ''))
        assert len(rows) == 162, (
            'Scan run, consistency: the independent driver must fit the full 162-file source'
        )
        target = copy_project(FULL, root / (mode + '-app'), mode)
        app = harness.invoke('run', target, observe=True)
        observed['modes'][mode] = {'reference': rows, 'app': app, 'files': files(source)}
    projection = copy_project(FULL, root / 'projection')
    csv_rows = observed['modes']['sequential']['reference']
    (projection / 'analysis/results.csv').write_text(csv_text(csv_rows))
    names = files(projection)
    analysis = projection / 'analysis/analysis.edi'
    analysis.write_text(
        analysis.read_text() + '\n_sequential_fit.template_file ' + names[17].name + '\n'
    )
    cells = root / 'projection-cells.json'
    cells.write_text(json.dumps(csv_rows))
    observed['inventory'] = harness.invoke('inventory', projection)
    observed['projectionReference'] = harness.invoke('reference-projection', projection, cells)
    observed['evolution'] = harness.invoke('evolution', projection)
    observed['click'] = harness.invoke('click', projection)
    observed['projectionRows'], observed['projectionFiles'] = csv_rows, names
    fallback = copy_project(SMALL, root / 'index-axis')
    analysis = fallback / 'analysis/analysis.edi'
    analysis.write_text(analysis.read_text().split('\nloop_\n_sequential_fit_extract.id')[0])
    projection_csv(fallback, 3)
    rows = read_csv((fallback / 'analysis/results.csv').read_text())
    for row, path in zip(rows, files(fallback), strict=True):
        row['file_path'] = path.name
        del row['temperature']
    (fallback / 'analysis/results.csv').write_text(csv_text(rows))
    observed['indexEvolution'] = harness.invoke('evolution', fallback)


def transition_observations(harness, root, observed):
    for mode in MODES:
        target = copy_project(FULL, root / (mode + '-flow'), mode, iterations=1)
        (target / 'analysis/results.csv').write_text(
            csv_text(observed['modes'][mode]['reference'])
        )
        observed[mode + '-flow'] = harness.invoke('flow', target, observe=True)
    unfitted = copy_project(FULL, root / 'unfitted')
    unfitted_cells = root / 'unfitted-cells.json'
    unfitted_cells.write_text(json.dumps([{'file_path': path.name} for path in files(unfitted)]))
    observed['unfitted'] = harness.invoke('inventory', unfitted)
    observed['unfittedReference'] = harness.invoke(
        'reference-projection', unfitted, unfitted_cells
    )
    single = copy_project(FULL, root / 'single', iterations=1)
    observed['single'] = harness.invoke('single', single, 17)
    observed['joint'] = harness.invoke('joint', copy_project(FULL, root / 'joint'))
    observed['singleReopened'] = harness.invoke('inventory', Path(str(single) + '-saved'))
    observed['bundle'] = harness.invoke(
        'bundle', 'pd-neut-cwl_cosio-d20_scan-162f', root / 'saved-bundle'
    )
    readonly = copy_project(FULL, root / 'readonly', iterations=1)
    paths = list(readonly.rglob('*'))
    try:
        for path in paths:
            path.chmod(0o555 if path.is_dir() else 0o444)
        readonly.chmod(0o555)
        observed['readonly'] = harness.invoke('readonly', readonly, root / 'saved-readonly')
    finally:
        readonly.chmod(0o755)
        for path in paths:
            path.chmod(0o755 if path.is_dir() else 0o644)


def scale_observations(harness, root, observed):
    scale = scale_project(harness, root / 'scale-100000', 100000)
    observed['scale'] = harness.invoke('scale', scale, observe=True)
    small_scale = scale_project(harness, root / 'scale-1000', 1000)
    observed['virtual1000'] = harness.invoke('virtual', small_scale)
    projection_csv(scale, 100000)
    observed['largeEvolution'] = harness.invoke('evolution', scale)
    observed['virtual100000'] = harness.invoke('virtual', scale)
    observed['scaleFiles'] = files(scale)
    twenty = scale_project(harness, root / 'lazy-20', 20)
    observed['lazySelected'] = harness.invoke('select', twenty, observe=True)
    observed['eager'] = harness.invoke('eager', twenty, observe=True)
    observed['lazyNames'] = files(twenty)
    for mode in MODES:
        analysis = twenty / 'analysis/analysis.edi'
        analysis.write_text(
            analysis.read_text().replace(
                '_fitting_mode.type sequential', '_fitting_mode.type ' + mode
            )
        )
        for old in (twenty / 'analysis').glob('results*.csv'):
            old.unlink()
        observed['lazy-' + mode] = harness.invoke('run', twenty, observe=True)


@pytest.mark.parametrize('mode', MODES)
def test_start_dispatches_the_real_162_file_worker(execution, mode):
    actual = execution['modes'][mode]['app']
    assert actual.get('entered') and actual.get('ended'), (
        'Scan run: Start must enter and finish the real app worker'
    )
    assert actual['workerOffOwner'], (
        'Scan run: optimizer work must execute off the GUI owner thread'
    )
    assert actual['completed'] == 162, 'Scan run: the real worker must complete all 162 datasets'
    assert_work(actual['work'], execution['modes'][mode]['files'], 'run')


@pytest.mark.parametrize('mode', MODES)
@pytest.mark.parametrize('dataset', DATASETS)
def test_every_162_file_csv_row_equals_the_independent_driver(execution, mode, dataset):
    actual = read_csv(execution['modes'][mode]['app'].get('csv', ''))
    assert len(actual) == 162, (
        'Scan run, consistency: app CSV must contain every one of the 162 datasets'
    )
    assert_cell_row(actual[dataset], execution['modes'][mode]['reference'][dataset])


def test_parity_gate_rejects_one_changed_cell(execution):
    row = execution['modes']['sequential']['reference'][81]
    damaged = copy.deepcopy(row)
    damaged['fit_result.reduced_chi_square'] = str(
        float(row['fit_result.reduced_chi_square']) + 0.375
    )
    with pytest.raises(AssertionError, match='every CSV cell'):
        assert_cell_row(damaged, row)


@pytest.mark.parametrize('dataset', DATASETS)
def test_fitted_selection_projects_csv_values_errors_and_calculated_pattern(execution, dataset):
    selected = execution['inventory'].get('selected', [])
    assert len(selected) == 162, (
        'Datasets: each fitted CSV row must be selectable in the actual view model'
    )
    actual = selected[dataset]
    expected = execution['projectionReference']['selected'][dataset]
    assert actual['index'] == dataset, 'Datasets: selection must name the requested dataset index'
    for name, value in expected['parameters'].items():
        assert name in actual['parameters'], (
            'Datasets: every fitted CSV parameter must reach the displayed parameter table'
        )
        assert actual['parameters'][name] == pytest.approx(value, nan_ok=True), (
            'Datasets: selected CSV values and uncertainties must reach the actual parameter items'
        )
    assert len(actual['pattern']) == len(expected['pattern']), (
        'Datasets: selected pattern must use its full measured grid'
    )
    for actual_point, expected_point in zip(actual['pattern'], expected['pattern'], strict=True):
        assert actual_point == pytest.approx(expected_point, rel=2e-12, abs=1e-10), (
            'Datasets: selected measured and calculated points must equal the independent '
            'crysta projection'
        )


@pytest.mark.parametrize('dataset', DATASETS)
def test_unfitted_selection_uses_own_measurement_and_template_calculation(execution, dataset):
    selected = execution['unfitted'].get('selected', [])
    assert len(selected) == 162, 'Datasets: every unfitted scan input must be selectable'
    expected = execution['unfittedReference']['selected'][dataset]['pattern']
    actual = selected[dataset]['pattern']
    assert len(actual) == len(expected), (
        'Datasets: an unfitted input must expose its own complete measured grid'
    )
    for actual_point, expected_point in zip(actual, expected, strict=True):
        assert actual_point == pytest.approx(expected_point, rel=2e-12, abs=1e-10), (
            'Datasets: unfitted measurement comes from its file and calculation from the '
            'unchanged template'
        )
    assert selected[dataset]['parameters'] == selected[0]['parameters'], (
        'Datasets: selecting an unfitted file must leave every displayed parameter unchanged'
    )


def test_initial_dataset_and_labels_follow_template_and_independent_extract(execution):
    inventory = execution['inventory']
    assert inventory['initial'] == 17, (
        'Datasets: opening a declared template starts on that dataset'
    )
    assert execution['unfitted']['initial'] == 0, (
        'Datasets: without a declared template the first dataset is selected'
    )
    assert len(inventory['rows']) == 162, (
        'Datasets: the explorer must expose all 162 file identities'
    )
    for index, row in enumerate(inventory['rows']):
        path = execution['projectionFiles'][index]
        temperature = re.search(r'^TEMP\s+([0-9.]+)', path.read_text(), re.MULTILINE).group(1)
        assert row['file'] == path.name, (
            'Datasets: explorer file names must retain the independent scan order'
        )
        assert path.name in row['label'], 'Datasets: selector labels must identify the data file'
        assert float(temperature) == float(row['extracted'][0].split()[0]), (
            'Datasets: labels must project the independent file header temperature'
        )
        assert row['extracted'][0].endswith(' K'), (
            'Datasets: temperature extraction must retain its kelvin unit'
        )
        assert row['isTemplate'] == (index == 17), (
            'Result tagging: exactly the declared dataset is the template'
        )


def test_evolution_all_parameter_values_errors_and_both_axes_equal_csv(execution):
    rows = execution['projectionRows']
    expected_names = {
        name.removesuffix('.uncertainty') for name in rows[0] if name.endswith('.uncertainty')
    }
    columns = execution['evolution'].get('columns', [])
    assert {column['name'] for column in columns} == expected_names, (
        'Evolution tab: every fitted CSV parameter must be selectable, without metadata columns'
    )
    for column in columns:
        name = column['name']
        for axis in column['axes']:
            assert axis['count'] == 162 and len(axis['points']) == 162, (
                'Evolution tab: the small full run preserves every fitted point'
            )
            for index, point in enumerate(axis['points']):
                row = rows[index]
                x = float(row['temperature']) if axis['mode'] == 0 else index + 1
                y, error = float(row[name]), float(row[name + '.uncertainty'] or 0)
                assert point == pytest.approx([x, y, y - error, y + error]), (
                    'Evolution tab: rendered x, y and error endpoints must project the disk CSV '
                    'cells'
                )
            if axis['mode'] == 0:
                assert 'K' in axis['title'], (
                    'Evolution tab: the extracted-temperature axis must display its unit'
                )


def test_evolution_without_extract_uses_one_based_file_index(execution):
    columns = execution['indexEvolution'].get('columns', [])
    assert len(columns) == 1, (
        'Evolution tab: a CSV without extracted metadata must expose its fitted parameter'
    )
    axis = columns[0]['axes'][0]
    assert [point[0] for point in axis['points']] == [1, 2, 3], (
        'Evolution tab: without an extracted x value, points use the one-based file index'
    )


def test_evolution_point_click_changes_the_shared_selection(execution):
    clicked = execution['click'].get('clicked', [])
    assert clicked, 'Evolution tab: an actual pointer event must reach a rendered fitted point'
    assert clicked[0]['selected'] == clicked[0]['wanted'] == clicked[0]['selector'], (
        'Evolution tab: clicking a point updates the dataset shared by the pattern, '
        'explorer and selector'
    )
    expected = execution['projectionReference']['selected'][clicked[0]['wanted']]['parameters']
    for name, value in expected.items():
        assert clicked[0]['parameters'][name] == pytest.approx(value), (
            'Evolution tab: point selection must update displayed fitted parameter values '
            'and errors'
        )


@pytest.mark.parametrize('mode', MODES)
def test_stop_undo_continue_and_template_edit_exercise_real_worker(execution, mode):
    flow = execution[mode + '-flow']
    assert flow['stop']['entered'] and flow['stop']['completed'] == 40, (
        'Stop and continue: Stop after file 40 must reach the real worker boundary'
    )
    assert len(read_csv(flow['partial'])) == 40, (
        'Stop and continue: stopping keeps exactly the first 40 CSV rows'
    )
    assert flow['stop']['after']['continuable'], (
        'Stop and continue: a partial unedited run must permit continuation'
    )
    assert not flow['stop']['after']['following'], 'Follow: it must be off after a stopped run'
    assert flow['stop']['after']['canUndo'], (
        'Undo: a completed partial worker run must enable Undo'
    )
    assert flow['undoRestored'], 'Undo: a partial run must restore the previous result bytes'
    assert flow['continue']['completed'] == 122 and flow['prefixKept'], (
        'Stop and continue: continuation keeps the prefix and fits only files 41 through 162'
    )
    expected = execution['modes'][mode]['files']
    assert_work(flow['work'], expected[40:], 'continue')
    assert not flow['edited']['continuable'], (
        'Result tagging: a template edit invalidates continuation'
    )
    assert (
        flow['editKept']
        and flow['staleFit']
        and flow['staleEvolution']
        and flow['oldResultsVisible']
    ), (
        'Result tagging: old CSV results remain visible with actual fit and Evolution '
        'out-of-date markers'
    )
    assert flow['restart']['completed'] == 162, (
        'Stop and continue: a template edit makes the next Start refit the whole scan'
    )
    assert_work(flow['work'], expected, 'restart')


@pytest.mark.parametrize('mode', MODES)
def test_follow_tracks_worker_and_manual_selection_until_reenabled(execution, mode):
    flow = execution[mode + '-flow']
    events = [event for event in flow.get('events', []) if event['stage'] == 'stop']
    assert len(events) == 40, (
        'Follow: worker-driven observations must reach every pre-stop dataset'
    )
    assert not flow['stop']['before']['following'], 'Follow: it is off before a scan'
    paths = execution['modes'][mode]['files']
    for index, event in enumerate(events):
        state = event['state']
        expected = 17 if 13 <= index <= 20 else index
        assert state['scanning'] and state['running'], (
            'Follow: observations must occur while the actual worker scan runs'
        )
        assert state['following'] == (not 13 <= index <= 20), (
            'Follow: a manual selection turns it off and pressing Follow turns it back on'
        )
        assert state['selected'] == expected, (
            'Follow: the displayed dataset must track worker progress or the manual choice'
        )
        points = event['pattern']
        expected_points = measured(paths[expected])
        assert len(points) == len(expected_points), (
            'Follow: the shown worker/manual dataset must expose its measured pattern'
        )
        for sample in (0, len(points) // 2, len(points) - 1):
            assert points[sample][:3] == pytest.approx(expected_points[sample]), (
                'Follow: the pattern must belong to the displayed dataset rather than just '
                'changing an index'
            )


def test_single_fit_persists_template_tag_and_selection(execution):
    single, reopened = execution['single'], execution['singleReopened']
    assert single['run']['entered'] and single['run']['ended'], (
        'Template: a single fit on the selected dataset must actually run'
    )
    assert not single['followingBefore'] and not single['followingAfter'], (
        'Follow: it is disabled in single mode'
    )
    assert not single['saveError'], 'Template: Save As must persist the fitted project'
    name = execution['projectionFiles'][17].name
    assert re.search(
        r'^_sequential_fit\.template_file\s+' + re.escape(name) + r'\s*$',
        single['analysis'],
        re.MULTILINE,
    ), 'Template: fitting a selected dataset must persist its template_file declaration'
    assert [index for index, row in enumerate(single['rows']) if row.get('isTemplate')] == [17], (
        'Result tagging: the fitted single dataset must carry the unique template tag'
    )
    assert reopened['initial'] == 17, (
        'Template: reopening the saved single result selects its template dataset'
    )
    assert reopened['selected'][17]['parameters'] == single['result'], (
        'Template: saved template parameter values and uncertainties must round-trip'
    )


def test_bundle_scan_uses_temporary_copy_and_save_as_retains_results(execution):
    bundle = execution['bundle']
    assert bundle.get('opened'), 'Temporary working copy: the bundled 162-file example must open'
    assert bundle['needsSaveAs'], (
        'Temporary working copy: an opened bundled project must require Save As'
    )
    assert not bundle['path'].startswith(':/') and '/docs/user/' not in bundle['path'], (
        'Temporary working copy: the worker writes into the extracted writable project'
    )
    assert bundle['run']['entered'] and bundle['run']['completed'] == 162, (
        'Temporary working copy: the actual bundled scan must finish on the worker'
    )
    assert bundle['beforeSave'], (
        'Temporary working copy: fitted CSV bytes must exist before Save As'
    )
    assert bundle['saved'] and not bundle['afterNeedsSaveAs'], (
        'Save As: the working copy must become a saved project'
    )
    assert bundle['afterSave'] == bundle['beforeSave'], (
        'Save As: every working result byte travels with the project'
    )


def assert_lazy_trace(trace, paths):
    ordered = [str(path.resolve()) for path in paths]
    by_address = {name: index for index, name in enumerate(ordered)}
    by_name = {path.name: index for index, path in enumerate(paths)}
    future, selected = set(), {0}
    next_file, work, opened = 0, 0, False
    for line in trace:
        cells = line.split('\t')
        assert cells[0] != 'unresolved', (
            'Scale: every observed native open must retain its resource identity'
        )
        if cells[0] == 'work':
            assert cells[2] in by_name, (
                'Scale: every worker receipt must identify a declared scan file'
            )
            index = by_name[cells[2]]
            assert index == next_file, (
                'Scale: native worker receipts retain the independent file order'
            )
            next_file = index + 1
            work += 1
            future = {index for index in future if index >= next_file}
        elif cells[0] == 'select':
            selected.add(int(cells[1]))
        elif len(cells) == 2 and cells[1] in by_address:
            opened = True
            index = by_address[cells[1]]
            if index >= next_file:
                future.add(index)
        assert all(index <= next_file + 4 for index in future - selected), (
            'Scale: read-ahead cannot jump beyond the next four unselected datasets'
        )
        assert len(future - selected - {next_file}) <= 4, (
            'Scale: native reads may reach only fitted or selected data and four read-ahead files'
        )
    assert opened, 'Scale: the observer must reach actual scan input opens'
    return work


@pytest.mark.parametrize('mode', MODES)
def test_lazy_reads_remain_bounded_through_later_and_independent_worker_windows(execution, mode):
    actual = execution['lazy-' + mode]
    assert actual['entered'] and actual['completed'] == 20, (
        'Scale: later read windows must exercise a real completed worker scan'
    )
    assert assert_lazy_trace(actual['trace'], execution['lazyNames']) == 20, (
        'Scale: the read observer must reach every dataset boundary in each scan mode'
    )


def test_lazy_selected_inputs_read_only_explicitly_selected_files(execution):
    actual = execution['lazySelected']
    assert [selection['index'] for selection in actual['selected']] == [0, 19, 19, 0], (
        'Scale: the selected-input exercise must reach the requested distant datasets'
    )
    assert_lazy_trace(actual['trace'], execution['lazyNames'])


def test_lazy_gate_rejects_real_eager_native_payload_reads(execution):
    actual = execution['eager']
    assert actual['eagerRead'] == 20, (
        'Scale: the escape must actually read all synthetic native payloads'
    )
    with pytest.raises(AssertionError, match=r'next four|four read-ahead'):
        assert_lazy_trace(actual['trace'], execution['lazyNames'])


def test_100000_files_reach_the_actual_optimizer_without_retained_payload_growth(execution):
    actual = execution['scale']
    assert actual['entered'] and actual['completed'] == 100000, (
        'Scale: all 100000 synthetic datasets must run through the real worker optimizer'
    )
    grid = [(8.125 + 0.125 * index, 4.5 + index / 10, 1.7) for index in range(11)]
    columns = [point[column] for column in range(3) for point in grid]
    expected_hash = hashlib.sha256(struct.pack('=' + 'd' * len(columns), *columns)).hexdigest()
    assert_work(actual['work'], execution['scaleFiles'], 'scale', expected_hash)
    assert len(read_csv(actual['csv'])) == 100000, (
        'Scale: a completed synthetic fit must write one durable row per dataset'
    )
    assert actual['peak1000'] > 0 and actual['peak100000'] > 0, (
        'Scale: memory measurements must reach both specified completed-file boundaries'
    )
    assert actual['peak100000'] <= 1.1 * actual['peak1000'], (
        'Scale: peak memory after file 100000 must be within ten percent of the peak '
        'after file 1000'
    )


def test_100000_file_median_time_has_no_scan_length_factor(execution):
    actual = execution['scale']
    assert actual['earlySamples'] == actual['lateSamples'] == 1000, (
        'Scale: timing must measure the full 1001..2000 and final-1000 windows'
    )
    assert actual['medianEarly'] > 0 and actual['medianLate'] > 0, (
        'Scale: real per-file timing samples must be positive'
    )
    assert actual['medianLate'] <= 1.2 * actual['medianEarly'], (
        'Scale: the final 1000 median may grow no more than twenty percent over files '
        '1001 through 2000'
    )


def test_100000_file_reads_have_at_most_four_files_of_read_ahead(execution):
    actual = execution['scale']
    assert assert_lazy_trace(actual['trace'], execution['scaleFiles']) == 100000, (
        'Scale: lazy-read evidence must reach all 100000 fitted dataset boundaries'
    )


def test_100000_file_models_lists_and_selector_popup_are_virtualized(execution):
    small, large = execution['virtual1000'], execution['virtual100000']
    for observation, count in ((small, 1000), (large, 100000)):
        assert 'error' not in observation, (
            'Scale: the actual table and selector popup must instantiate before '
            'virtualization is judged'
        )
        assert observation['count'] == count, (
            'Scale: virtualization must use the complete synthetic dataset model'
        )
        assert observation['firstDelegates'] > 0 and observation['lastReached'], (
            'Scale: actual first and last rows must become visible'
        )
        assert observation['firstDelegates'] <= observation['tableBound'], (
            'Scale: the first viewport creates only visible and cached table delegates'
        )
        assert observation['lastDelegates'] <= observation['tableBound'], (
            'Scale: scrolling to the end retains only visible and cached table delegates'
        )
        assert observation['popupOpened'] and observation['popupDelegates'] > 0, (
            'Scale: the actual populated selector popup must open'
        )
        assert observation['popupDelegates'] <= observation['popupBound'], (
            'Scale: the selector popup instantiates only visible and cached entries'
        )
    assert large['modelObjects'] <= small['modelObjects'], (
        'Scale: growing from 1000 to 100000 files must create no per-file QObject population'
    )


def test_large_evolution_thins_points_and_regression_bucket_partition_preserves_extrema(execution):
    columns = execution['largeEvolution'].get('columns', [])
    assert len(columns) == 1, (
        'Evolution tab: the synthetic CSV must expose its single fitted parameter'
    )
    for axis in columns[0]['axes']:
        points = axis['points']
        assert 0 < len(points) <= 5000, (
            'Evolution tab: large scans draw at most the packet thinning threshold'
        )
        values = [point[1] for point in points]
        assert min(values) == pytest.approx(10.125), (
            'Evolution tab: thinning must preserve the closed-form global minimum'
        )
        assert max(values) == pytest.approx(10.135), (
            'Evolution tab: thinning must preserve the closed-form global maximum'
        )
        if axis['mode'] == 1:
            # Regression pin for the existing uniform x-bucket partition (40 files here).
            # Numeric values/errors remain independent closed-form CSV references.
            indexed = {round(point[0]) - 1: point for point in points}
            for start in range(0, 100000, 40):
                bucket = range(start, min(start + 40, 100000))
                minimum = min(bucket, key=lambda index: (index * 37) % 1001)
                maximum = max(bucket, key=lambda index: (index * 37) % 1001)
                assert minimum in indexed and maximum in indexed, (
                    'Evolution tab: each thinning bucket must retain both independent closed-form '
                    'extrema'
                )
            for index, point in indexed.items():
                value = 10.125 + ((index * 37) % 1001) / 100000
                error = 0.000125 + (index % 7) / 1000000
                assert point == pytest.approx([index + 1, value, value - error, value + error]), (
                    'Evolution tab: thinning retains original dataset identity, value and error '
                    'endpoints'
                )


def test_template_tag_is_blue_in_the_actual_table_and_selector(execution):
    tags = execution['click'].get('templateTags', [])
    assert {tag['site'] for tag in tags} == {'table', 'selector'}, (
        'Result tagging: actual table and selector must both render the template tag'
    )
    for tag in tags:
        red, green, blue = tag['color']
        assert tag['text'] == 'template' and blue > max(red, green), (
            'Result tagging: the rendered template word must use a blue accent'
        )


@pytest.mark.parametrize('kind', ['bundle', 'readonly'])
def test_original_bundle_or_readonly_tree_is_unchanged_and_reopens_fresh(execution, kind):
    actual = execution[kind]
    assert actual.get('opened') and actual['needsSaveAs'], (
        'Temporary working copy: bundled and read-only inputs must open in a Save As copy'
    )
    assert actual['sourceBefore'] and actual['sourceBefore'] == actual['sourceAfter'], (
        'Temporary working copy: fitting and Save As cannot write into any original '
        'data or metadata file'
    )
    assert actual['freshOpened'] and not actual['freshCSV'], (
        'Temporary working copy: reopening the original begins with its own unmodified results'
    )
    assert actual['run']['entered'] and actual['beforeSave'], (
        'Temporary working copy: the writable temporary project must actually produce fit results'
    )
    assert actual['saved'] and actual['afterSave'] == actual['beforeSave'], (
        'Save As: temporary scan results must persist with the chosen project'
    )
    for name, digest in actual['sourceBefore'].items():
        if name.endswith('.dat'):
            assert actual['savedTree'].get(name) == digest, (
                'Save As: all original scan measurements retain their bytes in the saved project'
            )


def test_joint_mode_cannot_be_selected_in_a_scan_project(execution):
    joint = execution['joint']
    assert joint['after'] == joint['before'] == 'sequential', (
        'Stop and continue: joint mode must be refused at the real scan-project edit boundary'
    )
    assert joint['error'], (
        'Stop and continue: a refused joint-mode choice must explain the refusal'
    )
