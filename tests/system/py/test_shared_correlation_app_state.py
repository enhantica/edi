"""Observe immutable live bundle pointers across actual app actions on real scan fits."""

import copy
import json
import os
import subprocess
from pathlib import Path

import pytest

from tests.conftest import crysta_reference_prefix
from tests.fixtures.shared_correlations.freeze_saved import HERE, loop_bytes

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope='module')
def shared_app_state(tmp_path_factory):
    work = tmp_path_factory.mktemp('shared-correlations-app')
    sdk = Path(os.environ.get('EDI_PLAIN_DATA_SDK_DIR', crysta_reference_prefix()))
    build = Path(os.environ.get('EDI_PLAIN_DATA_HOST_BUILD', work / 'host'))
    source = Path(os.environ.get('EDI_PLAIN_DATA_SOURCE_ROOT', ROOT))
    command = [
        'pixi',
        'run',
        '-e',
        'app',
        'python',
        str(ROOT / 'tests/fixtures/plain_data/build_probe.py'),
        '--root',
        str(source),
        '--build',
        str(build),
        '--sdk',
        str(sdk),
    ]
    if gui := os.environ.get('EDI_SCAN_APP_GUI_SOURCE'):
        command += ['--gui-source', gui]
    subprocess.run(command, check=True)
    binary = build / 'cmake/tests/fixtures/plain_data/plain_data_probe'
    completed = subprocess.run(
        [
            str(binary),
            'correlation-save-stability',
            str(ROOT / 'tests/fixtures/correlations/scan-sequential'),
            str(work),
            'sequential',
            'shared-undo',
            'later',
        ],
        env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen', 'QSG_RHI_BACKEND': 'software'},
        capture_output=True,
        text=True,
        check=True,
    )
    record = json.loads(completed.stdout.splitlines()[-1])
    order_work = work / 'order'
    order_work.mkdir()
    completed = subprocess.run(
        [
            str(binary),
            'shared-order',
            str(ROOT / 'tests/fixtures/correlations/scan-sequential'),
            str(order_work),
            'sequential',
            'unused',
            'later',
        ],
        env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen', 'QSG_RHI_BACKEND': 'software'},
        capture_output=True,
        text=True,
        check=True,
    )
    record['order'] = json.loads(completed.stdout.splitlines()[-1])
    record['generated'] = {}
    for case in ['single', 'scan']:
        completed = subprocess.run(
            [
                str(binary),
                'frozen-generated',
                str(HERE),
                str(work / case),
                case,
                'unused',
                'later',
            ],
            env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen', 'QSG_RHI_BACKEND': 'software'},
            capture_output=True,
            text=True,
            check=True,
        )
        record['generated'][case] = json.loads(completed.stdout.splitlines()[-1])
    return record


def original_files(state):
    original = state['original']
    assert original['compact'], 'Real scan fits must publish shared immutable result bundles'
    assert len(original['files']) == 3, 'Every completed dataset must retain its own live bundle'
    return original['files']


@pytest.mark.parametrize('case', ['single', 'scan'])
def test_frozen_numeric_state_generates_the_complete_pre_change_saved_loop(shared_app_state, case):
    observed = shared_app_state['generated'][case]
    assert observed['loadedPairs'] == 0, (
        'Generated-output witnesses must load original input with no expected correlation rows'
    )
    if case == 'scan':
        assert observed['otherPairs'] == 0, (
            'A generated non-template table must contribute no persisted rows'
        )
    assert observed['generatedPairs'] == observed['numericPairs'] > 0, (
        'Fresh production table conversion must emit the complete single or template fitted state'
    )
    actual = loop_bytes(Path(observed['analysis']).read_bytes())
    assert actual == (HERE / (case + '-correlations.edi')).read_bytes(), (
        'Fresh numeric fitted-state conversion and saving must retain every pre-change loop byte'
    )


def test_real_scan_columns_share_one_names_vector(shared_app_state):
    files = original_files(shared_app_state)
    assert len({row['names'] for row in files.values()}) == 1, (
        'Equal ordered covariance columns must share one names vector across real file events'
    )
    assert len({row['bundle'] for row in files.values()}) == 3, (
        'Each real file event must publish a distinct immutable result bundle'
    )
    expected = json.loads((ROOT / 'tests/fixtures/correlations/reference.json').read_text())[
        'cases'
    ]['3']
    scan_cases = json.loads(
        (ROOT / 'tests/fixtures/correlations/scan-reference.json').read_text()
    )['cases']
    by_file = {case['file']: case for case in scan_cases}
    by_file['03.xy'] = by_file['02.xy']
    for file, row in files.items():
        expected = by_file[file]
        assert row['labels'] == expected['names'], (
            'Shared names must retain the independent polynomial free-column order'
        )
        assert row['coefficients'] == pytest.approx(
            [pair['correlation'] for pair in expected['rows']], abs=2e-4
        ), 'Compact coefficients must retain the frozen diffraction-lib polynomial projection'


@pytest.mark.parametrize('step', ['refreshed', 'renameUndo', 'resetUndo'])
def test_refresh_and_actual_undo_restore_identical_bundle_pointers(shared_app_state, step):
    original_files(shared_app_state)
    before = 'renameUndo' if step == 'resetUndo' else 'original'
    assert shared_app_state[step] == shared_app_state[before], (
        'Refresh and rename/reset Undo must retain exact bundle, table and vector pointers'
    )


def test_actual_reset_clears_current_map_and_keeps_retained_tables_unchanged(shared_app_state):
    original_files(shared_app_state)
    assert shared_app_state['reset'] == {'compact': True, 'files': {}}, (
        'Reset fits must clear every current dataset bundle'
    )
    assert shared_app_state['resetMatrix']['available'] == 0, (
        'The shown dataset must expose no stale correlation matrix after Reset fits'
    )
    assert shared_app_state['resetUndoAvailable'], (
        'Reset fits must leave its real Undo action available'
    )
    for step in ['originalAfterRename', 'originalAfterReset', 'originalAfterResetUndo']:
        assert shared_app_state[step] == shared_app_state['original'], (
            'Published tables retained by an earlier record must never change at ' + step
        )


@pytest.mark.parametrize(
    'step', ['originalAfterRename', 'originalAfterReset', 'originalAfterResetUndo']
)
def test_retained_boundary_gate_refuses_each_changed_snapshot(step):
    original = {'compact': True, 'files': {str(i): {'coefficients': [0.5]} for i in range(3)}}
    state = {
        'original': original,
        'reset': {'compact': True, 'files': {}},
        'resetMatrix': {'available': 0},
        'resetUndoAvailable': True,
        **{
            boundary: copy.deepcopy(original)
            for boundary in ['originalAfterRename', 'originalAfterReset', 'originalAfterResetUndo']
        },
    }
    state[step]['files']['0']['coefficients'][0] = -0.25
    with pytest.raises(AssertionError, match='must never change'):
        test_actual_reset_clears_current_map_and_keeps_retained_tables_unchanged(state)


def test_actual_block_rename_replaces_shared_names_once_and_keeps_coefficient_pointers(
    shared_app_state,
):
    original = original_files(shared_app_state)
    renamed = shared_app_state['renamed']['files']
    assert len({row['names'] for row in renamed.values()}) == 1, (
        'One block rename must create one replacement names vector for every old holder'
    )
    for file, before in original.items():
        after = renamed[file]
        assert after['labels'] == [
            name.replace('bank.', 'renamed_bank.', 1) for name in before['labels']
        ], 'Every live table must see the renamed block through its shared names'
        assert after['names'] != before['names'], (
            'A rename must preserve the immutable original names'
        )
        assert (
            after['values'] == before['values'] and after['coefficients'] == before['coefficients']
        ), 'A rename must retain exact coefficient pointers, values and pair order'


def test_real_reordered_free_columns_get_new_names_and_new_pair_order(shared_app_state):
    states = shared_app_state['order']
    assert states['first']['compact'] and states['second']['compact'], (
        'Both actual scans must publish compact tables before testing reordered free sets'
    )
    first, second = states['first']['files'], states['second']['files']
    assert len(first) == len(second) == 2, 'Both scans must fit the complete two-file inventory'
    assert len({row['names'] for row in second.values()}) == 1, (
        'The reordered scan must still share one vector for its equal ordered free sets'
    )
    expected = json.loads((ROOT / 'tests/fixtures/correlations/reference.json').read_text())[
        'cases'
    ]['3']
    by_file = {
        case['file']: case
        for case in json.loads(
            (ROOT / 'tests/fixtures/correlations/scan-reference.json').read_text()
        )['cases']
    }
    for file, row in second.items():
        coefficients = [pair['correlation'] for pair in by_file[file]['rows']]
        assert row['names'] != first[file]['names'], (
            'An equal free set in a different order must get a new ordered names vector'
        )
        assert row['labels'] == [
            expected['names'][1],
            expected['names'][0],
            expected['names'][2],
        ], 'The second actual scan must resolve ramp, base, curve in its covariance column order'
        assert row['coefficients'] == pytest.approx(
            [coefficients[0], coefficients[2], coefficients[1]], abs=2e-4
        ), 'Packed values must follow the reordered columns against the frozen external projection'
    assert states['retained'] == states['first'], (
        'A changed free-column order must never mutate a retained earlier scan table'
    )
