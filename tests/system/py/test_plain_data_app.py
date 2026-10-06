"""Observe the production view model without enabling the GUI test groups."""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
from pathlib import Path

import pytest

from tests.conftest import crysta_reference_prefix
from tests.integration.py.test_scan_app_contract import block, item, source

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / 'tests/fixtures/plain_data'
CASES = json.loads((FIXTURE / 'cases.json').read_text())


@pytest.fixture(scope='module')
def native_probe(tmp_path_factory):
    header = (ROOT / 'app/src/project_view_model.hpp').read_text()
    assert 'createStructure(' in header and 'loadData(' in header, (
        'Create structure / Load data: the product view model must expose the actions '
        'declared in the visible native host contract before execution'
    )
    build = tmp_path_factory.mktemp('plain-data-host')
    command = [
        'pixi',
        'run',
        '-e',
        'app',
        'python',
        str(FIXTURE / 'build_probe.py'),
        '--root',
        str(ROOT),
        '--build',
        str(build),
        '--sdk',
        str(crysta_reference_prefix()),
    ]
    gui = os.environ.get('EDI_SCAN_APP_GUI_SOURCE')
    if gui:
        command += ['--gui-source', gui]
    completed = subprocess.run(command, capture_output=True, text=True, check=False, timeout=600)
    assert completed.returncode == 0, (
        'Plain-data native host: compile the actual app module against the installed SDK\n'
        + completed.stdout
        + completed.stderr
    )
    return build / 'cmake/tests/fixtures/plain_data/plain_data_probe'


def run(native_probe, tmp_path, mode='load', beam='cwl', case='two_columns', escape='none'):
    work = tmp_path / (mode + '-' + beam + '-' + case + '-' + escape)
    work.mkdir()
    spec = CASES[beam + '/' + case]
    command = [
        str(native_probe),
        mode,
        str(FIXTURE),
        str(work),
        beam,
        escape,
        beam + '/' + case + '/' + spec['file'],
    ]
    environment = dict(os.environ, QT_QPA_PLATFORM='offscreen', QSG_RHI_BACKEND='software')
    completed = subprocess.run(
        command, env=environment, capture_output=True, text=True, check=False, timeout=30
    )
    assert completed.returncode == 0, (
        'Plain-data native host: complete the observed action without process failure\n'
        + completed.stderr
    )
    return json.loads(completed.stdout.splitlines()[-1])


def require_success(record):
    assert 'error' not in record, (
        'Plain-data workflow: all admitted view-model actions must complete: '
        + record.get('error', '')
    )


def rows(state):
    e = state['experiments'][0]
    return [list(row) for row in zip(e['x'], e['y'], e['sigma'], strict=True)]


def require_reopened(record, expected):
    require_success(record)
    assert record['opened'] and rows(record['reopened']) == expected, (
        'Save plain data: reopen solely from the saved project after deleting the input file'
    )


def require_unlinked(state):
    assert state['experiments'][0]['links'] == ['structure1', 'structure2'], (
        'Create structure: a new structure must never link to an existing experiment'
    )


@pytest.mark.parametrize('beam', ['cwl', 'tof'])
def test_load_lock_replace_and_single_step_undo(native_probe, tmp_path, beam):
    record = run(native_probe, tmp_path, beam=beam)
    require_success(record)
    expected = CASES[beam + '/two_columns']['rows']
    e = record['after']['experiments'][0]
    assert record['loaded'] and rows(record['after']) == expected, (
        'Load data: the created experiment receives the hand-constructed measured triples'
    )
    assert not e['simulation'] and record['typeRefused'], (
        'Load data: measured data locks the type and disables simulation-range editing'
    )
    assert e['range'] == [expected[0][0], expected[-1][0], expected[1][0] - expected[0][0]], (
        'Load data: visible range reports measured start, end and nontrivial step'
    )
    assert rows(record['afterTypeAttempt']) == expected, (
        'Load data: attempting a type change preserves all measured columns'
    )
    assert (
        record['before']['parameters'] == record['after']['parameters'] and e['weight'] == 2.5
    ), 'Load data: instrument, peak, background and parameter state survive import'
    assert record['firstLoad'] and record['secondLoad'], (
        'Load data: a created experiment permits repeated replacement after its first import'
    )
    assert rows(record['secondData']) == CASES[beam + '/three_columns']['rows'], (
        'Load data: the second import replaces rather than appends data'
    )
    assert rows(record['undoSecond']) == expected, (
        'Undo load: one undo restores the entire preceding measured dataset'
    )
    undone = record['undoFirst']['experiments'][0]
    assert undone['simulation'] and undone['range'] == (
        [2400, 2412, 3] if beam == 'tof' else [14, 16, 0.5]
    ), 'Undo load: the next undo restores the prior simulation range and editable type'


@pytest.mark.parametrize('beam', ['cwl', 'tof'])
def test_saved_data_is_self_contained_and_edi_load_cannot_replace_it(native_probe, tmp_path, beam):
    record = run(native_probe, tmp_path, beam=beam)
    expected = CASES[beam + '/two_columns']['rows']
    require_reopened(record, expected)
    assert record['ediLoadRefused'] and rows(record['afterEdiLoadAttempt']) == expected, (
        'Load data admission: an experiment reopened from .edi cannot use the creation-only action'
    )
    assert not record['reopened']['experiments'][0]['simulation'], (
        'Save plain data: the reopened experiment retains its measured-data type lock'
    )


@pytest.mark.parametrize(
    ('mode', 'expected_name'), [('load', 'pattern'), ('renamed', 'User name')]
)
def test_filename_and_user_name(native_probe, tmp_path, mode, expected_name):
    record = run(native_probe, tmp_path, mode=mode)
    require_success(record)
    e = record['after']['experiments'][0]
    assert e['name'] == expected_name and e['file'] == 'pattern.xy', (
        'Load data naming: default names take the stem, user names survive, '
        'File shows the original filename'
    )
    assert record['reopened']['experiments'][0]['file'] == 'pattern.xy', (
        'Save plain data: the original File column label survives save and reopen'
    )


@pytest.mark.parametrize(
    'case', ['two_columns', 'headers_malformed', 'nonpositive', 'unsorted_duplicates', 'comma']
)
def test_one_load_message_reports_constructed_counts(native_probe, tmp_path, case):
    record = run(native_probe, tmp_path, mode='counts', case=case)
    require_success(record)
    messages = record['messages']
    assert len(messages) == 1, (
        'Load data messages: one import appends exactly one status-bar entry'
    )
    message = messages[0].lower()
    counts = CASES['cwl/' + case]['counts']
    for label, count in [
        ('skip', counts['skipped']),
        ('non-positive', counts['nonpositive']),
        ('duplicate', counts['duplicates']),
        ('reorder', counts['reordered']),
    ]:
        if count:
            assert re.search(
                r'(?:\b'
                + str(count)
                + r'\b.{0,25}'
                + re.escape(label)
                + '|'
                + re.escape(label)
                + r'.{0,25}\b'
                + str(count)
                + r'\b)',
                message,
            ), (
                'Load data messages: skipped, nonpositive, duplicate and reordered counts '
                'match the fixture'
            )
    if counts['derived']:
        assert ('sqrt' in message or '√' in message) and (
            'sigma' in message or '\u03c3' in message
        ), 'Load data messages: two-column import names the derived uncertainty convention'


def test_default_structure_matches_frozen_beta_cif(native_probe, tmp_path):
    record = run(native_probe, tmp_path, mode='structure')
    require_success(record)
    reference = (FIXTURE / 'default.cif').read_text()
    assert (
        '_space_group_name_H-M_alt "P b n m"' in reference and 'O O 0 0 0 1 Biso 0' in reference
    ), (
        'Create structure reference: the frozen upstream block declares '
        'the expected group and oxygen site'
    )
    assert record['created'] and record['createdSecond'], (
        'Create structure: both successive creation actions must succeed'
    )
    tokens = shlex.split(reference)
    expected = {
        'name': 'structure1',
        'group': tokens[tokens.index('_space_group_name_H-M_alt') + 1],
        'cell': [
            float(tokens[tokens.index('_cell_' + tag) + 1])
            for tag in [
                'length_a',
                'length_b',
                'length_c',
                'angle_alpha',
                'angle_beta',
                'angle_gamma',
            ]
        ],
        'sites': [{'id': 'O', 'type': 'O', 'xyz': [0, 0, 0], 'occupancy': 1, 'biso': 0}],
    }
    assert record['first']['structures'][0] == expected, (
        'Create structure: all cell, group and site values equal the frozen beta default CIF'
    )
    assert [s['name'] for s in record['second']['structures']] == ['structure1', 'structure2'], (
        'Create structure: successive creations allocate increasing default names'
    )
    assert record['undo']['structures'] == record['first']['structures'], (
        'Undo create structure: one undo removes only the last created structure'
    )


def test_link_all_unlinked_new_structure_and_atomic_remove_undo(native_probe, tmp_path):
    record = run(native_probe, tmp_path, mode='links')
    require_success(record)
    assert record['newExperiment']['experiments'][0]['links'] == ['structure1', 'structure2'], (
        'Create experiment: automatically link every existing structure'
    )
    require_unlinked(record['newStructure'])
    assert record['removed']['experiments'][0]['links'] == ['structure2'], (
        'Remove structure: remove all referring experiment links in the same edit'
    )
    assert [s['name'] for s in record['removed']['structures']] == ['structure2', 'structure3'], (
        'Remove structure: remove the selected structure and retain every other structure'
    )
    assert (
        record['undo']['structures'] == record['newStructure']['structures']
        and record['undo']['experiments'] == record['newStructure']['experiments']
    ), 'Undo remove structure: one undo restores both the structure and all experiment links'
    assert record['messages'], (
        'Remove linked structure: report the removed experiment links in Messages'
    )


def test_mixed_project_create_fit_measured_only_calculate_all(native_probe, tmp_path):
    record = run(native_probe, tmp_path, mode='mixed')
    require_success(record)
    assert record['createdExtra'] and record['mixed']['canCreate'], (
        'Mixed project: measured data must not disable Create experiment'
    )
    assert len(record['calculated']) == 2 and all(count > 0 for count in record['calculated']), (
        'Mixed project: calculation covers both the measured and data-less experiment'
    )
    assert record['fitPoints'] == 3 and record['afterFit']['experiments'][1]['simulation'], (
        'Mixed project: fitting consumes only measured points and keeps the data-less experiment'
    )


def test_packet_escape_controls_reject_bad_observations():
    good = {'opened': True, 'reopened': {'experiments': [{'x': [1], 'y': [4], 'sigma': [2]}]}}
    require_reopened(good, [[1, 4, 2]])
    with pytest.raises(AssertionError, match='Plain-data workflow'):
        require_reopened({'error': 'external data required on reopen'}, [[1, 4, 2]])
    require_unlinked({'experiments': [{'links': ['structure1', 'structure2']}]})
    with pytest.raises(AssertionError, match='Create structure'):
        require_unlinked({'experiments': [{'links': ['structure1', 'structure2', 'structure3']}]})


@pytest.mark.parametrize(('mode', 'escape'), [('load', 'source-reopen'), ('links', 'link-new')])
def test_packet_escapes_reach_the_native_actions(native_probe, tmp_path, mode, escape):
    control = run(native_probe, tmp_path, mode=mode)
    require_success(control)
    mutated = run(native_probe, tmp_path, mode=mode, escape=escape)
    if mode == 'load':
        require_reopened(control, CASES['cwl/two_columns']['rows'])
        assert mutated.get('error') == 'external data required on reopen', (
            'Save-data escape: the actor must actually try to reopen the deleted source file'
        )
        with pytest.raises(AssertionError, match='Plain-data workflow'):
            require_reopened(mutated, CASES['cwl/two_columns']['rows'])
    else:
        require_unlinked(control['newStructure'])
        require_success(mutated)
        with pytest.raises(AssertionError, match='Create structure'):
            require_unlinked(mutated['newStructure'])


def test_desktop_browser_picker_and_editability_bindings_share_load_path():
    qml = source('qml/Pages/Experiment/ExperimentsGroup.qml')
    control = item(qml, 'experiments.loadData.${row.index}')
    assert 'enabled: false' not in control and 'loadData' in control, (
        'Load data picker: the per-experiment action must open its working data chooser'
    )
    assert 'WebFiles.openFiles' in qml and all(
        ext in qml for ext in ['.xye', '.xy', '.dat', '.txt', '.csv']
    ), 'Load data browser: offer every declared data extension through the shipped WebFiles picker'
    callback = block(qml, 'function onFilesOpened')
    assert 'loadData' in callback and 'request' in callback and 'webRequestProject' in callback, (
        'Load data browser: deliver its own picker result to the same admitted load action'
    )
    assert 'calculationOnly' not in control, (
        'Load data availability: retain the action after a created experiment receives data'
    )
    assert 'All files' in qml, 'Load data desktop: include the unrestricted All files filter'
    range_qml = source('qml/Pages/Experiment/MeasuredRangeGroup.qml')
    type_qml = source('qml/Pages/Experiment/ExperimentTypeGroup.qml')
    assert (
        'experiment.calculationOnly' in range_qml and 'experiment.calculationOnly' in type_qml
    ), 'Load data editability: measured data disables both range and type selectors'
    structure_qml = source('qml/Pages/Structure/StructuresGroup.qml')
    assert 'Create structure' in structure_qml and '.createStructure()' in structure_qml, (
        'Create structure button: replace the disabled manual-definition '
        'action in the shipped page'
    )
    cmake = (ROOT / 'app/CMakeLists.txt').read_text()
    assert 'src/web_files.cpp' in cmake, (
        'Load data browser build: the common app target compiles its picker implementation'
    )
    browser = source('src/web_files.cpp')
    assert 'EMSCRIPTEN' in browser and ('openFile' in browser or 'openFiles' in browser), (
        'Load data browser build: compile the picker implementation for the web platform'
    )
