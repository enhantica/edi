"""Unchanged app saves retain the template subset's correlation IDs and text."""

import json
import os
import subprocess
from pathlib import Path

import pytest

from tests.conftest import crysta_reference_prefix
from tests.fixtures.correlations.rename_history import literal_source
from tests.integration.py.test_default_structure_rename import observe
from tests.integration.py.test_parameter_correlations import correlations

ROOT = Path(__file__).resolve().parents[3]
CASES = [
    (mode, later, scenario)
    for mode in ['sequential', 'independent']
    for later in ['first', 'later']
    for scenario in ['complete', 'partial', 'single-undo', 'reset-undo']
]


@pytest.fixture(scope='module')
def save_observations(tmp_path_factory):
    root = tmp_path_factory.mktemp('scan-correlation-save')
    sdk = (
        Path(os.environ['EDI_PLAIN_DATA_SDK_DIR'])
        if os.environ.get('EDI_PLAIN_DATA_SDK_DIR')
        else crysta_reference_prefix()
    )
    build = (
        Path(os.environ['EDI_PLAIN_DATA_HOST_BUILD'])
        if os.environ.get('EDI_PLAIN_DATA_HOST_BUILD')
        else root / 'host'
    )
    command = [
        'pixi',
        'run',
        '-e',
        'app',
        'python',
        str(ROOT / 'tests/fixtures/plain_data/build_probe.py'),
        '--root',
        str(ROOT),
        '--build',
        str(build),
        '--sdk',
        str(sdk),
    ]
    if gui := os.environ.get('EDI_SCAN_APP_GUI_SOURCE'):
        command += ['--gui-source', gui]
    subprocess.run(command, check=True)
    binary = build / 'cmake/tests/fixtures/plain_data/plain_data_probe'
    result = {'binary': binary, 'root': root}
    for mode, later, scenario in CASES:
        work = root / (mode + '-' + later + '-' + scenario)
        work.mkdir()
        completed = subprocess.run(
            [
                str(binary),
                'correlation-save-stability',
                str(ROOT / ('tests/fixtures/correlations/scan-' + mode)),
                str(work),
                mode,
                scenario,
                later,
            ],
            env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen', 'QSG_RHI_BACKEND': 'software'},
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        if completed.returncode:
            raise RuntimeError('The real app save lifecycle failed: ' + completed.stderr)
        record = json.loads(completed.stdout.splitlines()[-1])
        paths = ['saved', 'core-copy', 'saved-again', 'saved-third']
        texts = {
            name: (work / name / 'analysis/analysis.edi').read_text()
            for name in paths
            if (work / name / 'analysis/analysis.edi').is_file()
        }
        result[mode, later, scenario] = record, texts
    result['renames'] = observe_renames(root, binary)
    return result


@pytest.mark.parametrize(('mode', 'later', 'scenario'), CASES)
def test_template_correlation_ids_survive_unchanged_app_reload_and_save(
    save_observations, mode, later, scenario
):
    record, texts = save_observations[mode, later, scenario]
    assert 'error' not in record, (
        'The actual scan, template selection, Undo, save and reload must complete: '
        + record.get('error', '')
    )
    assert record['fitted'] >= 2, 'The later-template witness must contain an earlier real fit'
    for step in ['firstLive', 'laterLive']:
        assert record[step]['available'] == 3, (
            'Both fitted datasets retain their three-parameter matrices before persistence'
        )
    if scenario == 'partial':
        assert record['fitted'] == 2, 'The partial scan stops before the third dataset finishes'
    assert record['otherAfterSave']['available'] == 3, (
        'Saving the template subset keeps every selected live matrix in memory'
    )
    other = record['firstReopened' if later == 'later' else 'laterReopened']
    assert other['available'] == 0 and 'template' in other['emptyText'].lower(), (
        'Reopened non-template datasets explain why their in-memory matrices were not persisted'
    )
    first = correlations(texts['saved'])
    assert len(first) == 3 and all(row['file_path'] == record['template'] for row in first), (
        'The required SDK saves only the explicitly selected template dataset matrix'
    )
    assert correlations(texts['core-copy']) == first, (
        'The core writer is an unchanged-save control for retained correlation row IDs'
    )
    for step in ['saved-again', 'saved-third']:
        assert correlations(texts[step]) == first, (
            'An unchanged app reload and save retains every correlation '
            'ID, name and coefficient text'
        )


RENAME_CASES = [
    ('historical', kind, scan) for kind in ['structure', 'experiment'] for scan in [False, True]
] + [('default', 'structure', scan) for scan in [False, True]]


def observe_renames(root, binary):
    literal = literal_source(root / 'literal-source')
    result = {}
    for history, kind, scan in RENAME_CASES:
        work = root / (history + '-' + kind + '-' + str(scan))
        work.mkdir()
        source = (
            literal
            if history == 'default'
            else ROOT
            / (
                'tests/fixtures/correlations/scan-sequential'
                if scan
                else 'tests/fixtures/correlations/polynomial-3'
            )
        )
        completed = subprocess.run(
            [
                str(binary),
                'correlation-'
                + ('historical' if history == 'historical' else 'default')
                + '-rename',
                str(source),
                str(work),
                'scan' if scan else 'plain',
                kind,
                'accepted',
            ],
            env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen', 'QSG_RHI_BACKEND': 'software'},
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        if completed.returncode:
            raise RuntimeError('The actual app rename actor failed: ' + completed.stderr)
        record = json.loads(completed.stdout.splitlines()[-1])
        documents = {
            name: (work / name / 'analysis/analysis.edi').read_text()
            for name in ['input', 'saved', 'undone-saved']
            if (work / name / 'analysis/analysis.edi').is_file()
        }
        result[history, kind, scan] = record, documents
    return result


def renamed_reference(before, kind):
    structure, experiment = (
        ('structure', 'bank')
        if any(name.startswith('structure.cell.') for name in before['aliases'])
        else ('phase', 'bank')
    )

    def name(value):
        if kind == 'experiment':
            return (
                value.replace(experiment + '.', 'new_bank.', 1)
                if value.startswith(experiment + '.')
                else value
            )
        if value.startswith(structure + '.'):
            return 'new_phase.' + value.removeprefix(structure + '.')
        return value.replace('.' + structure + '.', '.new_phase.')

    return {
        'aliases': [name(value) for value in before['aliases']],
        'pairs': [
            {**pair, 'i': name(pair['i']), 'j': name(pair['j'])} for pair in before['pairs']
        ],
        'links': [
            'new_phase' if kind == 'structure' and value == structure else value
            for value in before['links']
        ],
        'textures': [
            'new_phase' if kind == 'structure' and value == structure else value
            for value in before['textures']
        ],
    }


@pytest.mark.parametrize(('history', 'kind', 'scan'), RENAME_CASES)
def test_app_history_and_literal_cell_renames_survive_undo_and_reload(
    save_observations, history, kind, scan
):
    record, documents = save_observations['renames'][history, kind, scan]
    assert 'error' not in record, (
        'Actual app rename, cache, Undo, save and reload must complete: ' + record.get('error', '')
    )
    if history == 'historical':
        assert any('curve.coef' in pair['i'] for pair in record['before']['pairs']) and any(
            'curve.coef' in pair['j'] for pair in record['before']['pairs']
        ), 'A real native fit retains the removed term in both historical endpoint directions'
    else:
        before = observe(documents['input'])
        assert len(before['ids']) == 6, (
            'The default structure reaches all six compact fit-state IDs'
        )
        assert observe(documents['saved'])['ids'] == before['ids'], (
            'The app preserves compact storage IDs '
            'while public default-structure cell names change'
        )
    expected = renamed_reference(record['before'], kind)
    assert record['renamed'] == expected and record['reopened'] == expected, (
        'Actual app renames follow both historical endpoints '
        'and all default structure cell references'
    )
    assert record['undone'] == record['before'] and record['undoReopened'] == record['before'], (
        'Literal rename Undo restores historical names, alias roles and link/texture identities'
    )
    assert record['undoneTemplate'] == record['beforeTemplate'], (
        'A scan rename Undo restores the template cache including its historical matrix'
    )
