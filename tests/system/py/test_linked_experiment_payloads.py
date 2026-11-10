"""Every experiment importer and save keeps its admitted measured-source identity."""

import json
import os
import subprocess
from pathlib import Path

import gemmi
import pytest

from tests.fixtures.cif_import_baseline.generate_readers import saved_columns
from tests.system.py import test_save_policy_continuations as policy

ROOT = Path(__file__).resolve().parents[3]
tutorial_observer = policy.tutorial_observer
FORMS = ('powder-cwl', 'powder-tof', 'single-crystal-cwl', 'single-crystal-tof')
CASES = (
    [
        (form, 'unchanged', route, mode)
        for form in FORMS
        for route in policy.ROUTES
        for mode in ('linked', 'all')
    ]
    + [
        (form, transition, 'fresh-folder', 'linked')
        for form in FORMS
        for transition in ('ordinary', 'batch-copy', 'batch-link', 'relocate')
    ]
    + [
        (form, transition, 'fresh-folder', 'linked')
        for form in FORMS[:2]
        for transition in ('scan-copy', 'scan-link', 'scan-replace-copy', 'scan-replace-link')
    ]
)


def expected_rows(form, *, successor=False):
    increment = 10 if successor else 0
    if form.startswith('powder'):
        axis = (3500, 3600, 3700) if form.endswith('tof') else (17.5, 18, 18.5)
        return [
            [x, y + increment, su]
            for x, y, su in zip(axis, (4, 9, 16), (0.5, 1.25, 2.5), strict=True)
        ]
    rows = [[2, 1, 3, 18.5, 0.7], [-2, 1, 3, 9.2, 1.3], [0, 0, 2, -4.5, 0.2]]
    for row in rows:
        row[3] = row[3] - increment if row[3] < 0 else row[3] + increment
    if form.endswith('tof'):
        rows = [
            [*row, wavelength] for row, wavelength in zip(rows, (1.25, 1.75, 2.25), strict=True)
        ]
    return rows


def linked_observation(binary, tmp_path, form, transition, route, mode):
    result = subprocess.run(
        [
            binary,
            str(ROOT / 'tests/fixtures/loop_parameter_ids/line-segment'),
            f'linked-payload/{form}/{transition}/{route}/{mode}',
        ],
        text=True,
        capture_output=True,
        check=False,
        timeout=25,
        env={
            **os.environ,
            'TMPDIR': str(tmp_path),
            'QT_QPA_PLATFORM': 'offscreen',
            'QT_QUICK_BACKEND': 'software',
            'EDI_ONLINE_SOURCES': f'cod={tmp_path.as_uri()};easydiffraction={tmp_path.as_uri()}',
        },
    )
    (tmp_path / 'observation.log').write_text(result.stdout + result.stderr)
    assert result.returncode == 0, (
        'The source witness reaches real imports and final save boundaries: ' + result.stderr
    )
    rows = json.loads(result.stdout.splitlines()[-1])
    assert len(rows) == 1, (
        'One source witness belongs to exactly one declared replacement and save'
    )
    return rows[0]


def one_experiment(observation):
    assert len(observation['experiments']) == 1, (
        'Each fixture retains its one admitted experiment or scan template'
    )
    return observation['experiments'][0]


def check_link(record, physical):
    columns = saved_columns(record['text'])
    path = columns.get('_data_source_path', [])
    assert len(path) == 1, (
        'Keep linked persists one explicit source path in the actual saved experiment'
    )
    assert gemmi.cif.as_string(path[0]) == record['declared'], (
        'The native reader retains the exact independently parsed saved path'
    )
    assert record['physicalSource'] == physical, (
        'The saved source resolves to the admitted physical input rather than an earlier template'
    )
    assert not Path(record['declared']).is_absolute(), (
        'Same-volume experiment links use project-relative spelling when saved'
    )
    for tag in ('_data_intensity_meas', '_refln_intensity_meas'):
        assert tag not in columns, 'Keep linked omits both powder and reflection measurement loops'


@pytest.mark.parametrize(('form', 'transition', 'route', 'mode'), CASES)
def test_linked_sources_survive_every_replacement_and_save(
    tutorial_observer, tmp_path, form, transition, route, mode
):
    row = linked_observation(tutorial_observer, tmp_path, form, transition, route, mode)
    assert row['admitted'], (
        'All powder and single-crystal forms admit an explicitly linked measured file'
    )
    initial = one_experiment(row['initial'])
    check_link(initial, row['sourceA'])
    assert initial['rows'] == expected_rows(form), (
        'The seed source identity is established with independently authored measurements'
    )
    assert row['replaced'], (
        'Every declared common replacement route admits its independent successor input'
    )
    assert row['sourcesUnchanged'], (
        'Importing and saving never change either original external input folder'
    )
    assert row['published'], (
        'Each original save route reaches actual native publication or browser write payload'
    )
    saved = one_experiment(row['saved'])
    changed = transition not in {'unchanged', 'relocate'}
    assert saved['rows'] == expected_rows(form, successor=changed), (
        'Reopening the final saved model retains the independently different '
        'replacement measurements'
    )
    if transition.startswith('scan-'):
        assert not saved['declared'], (
            'Every scan constructor and replacement clears an inherited experiment-file link'
        )
        assert row['saved']['physicalScan'], (
            'A saved scan retains its admitted dataset-folder identity'
        )
    elif mode == 'linked' and transition not in {'ordinary', 'batch-copy'}:
        check_link(saved, row['sourceB'] if changed else row['sourceA'])
    else:
        assert not saved['declared'], (
            'An embedded import or Include all clears the earlier external source identity'
        )
    if mode == 'all':
        reopened = one_experiment(row['withoutSources'])
        assert reopened['rows'] == expected_rows(form, successor=changed), (
            'Included data reopen after both original external folders physically move'
        )
    if transition == 'relocate':
        assert row['missingOpened'], (
            'A missing external measured file never prevents the project opening'
        )
        assert row['missingMarked'], (
            'Every experiment form exposes its missing measured-file marker'
        )
        assert row['located'], (
            'The actual Locate file receiver reads and relinks its admitted target'
        )
        assert row['missingCleared'], 'Locate clears the missing-data marker after the actual read'
        assert row['relocatedSaved'], (
            'The located source saves through the ordinary project save route'
        )
        located = one_experiment(row['relocated'])
        check_link(located, row['movedSource'])
        assert located['rows'] == expected_rows(form), (
            'Locate and a second save preserve every original authored measurement'
        )


@pytest.mark.parametrize('form', FORMS)
def test_full_experiment_import_keeps_its_relative_source_base(tutorial_observer, tmp_path, form):
    row = linked_observation(
        tutorial_observer, tmp_path, form, 'full-experiment', 'fresh-folder', 'linked'
    )
    assert row['admitted'], 'The independent setup admits the full experiment source witness'
    assert row['replaced'], (
        'The actual full-experiment receiver admits a source-relative measured link'
    )
    assert row['sourcesUnchanged'], (
        'Full-experiment importing never changes either external measured source'
    )
    assert row['published'], (
        'An imported full experiment publishes through the actual project save route'
    )
    saved = one_experiment(row['saved'])
    check_link(saved, row['sourceB'])
    assert saved['rows'] == expected_rows(form, successor=True), (
        'An imported full experiment reopens its own source-relative measurements'
    )


@pytest.mark.parametrize('form', ['single-crystal-cwl', 'single-crystal-tof'])
def test_one_reflection_file_retains_every_authored_dataset(tutorial_observer, tmp_path, form):
    row = linked_observation(
        tutorial_observer, tmp_path, form, 'reflection-batch', 'fresh-folder', 'linked'
    )
    assert row['admitted'], (
        'The ordinary reflection setup admits the authored multi-dataset witness'
    )
    assert row['replaced'], 'The real batch reader admits a FullProf file with several dataset ids'
    assert row['published'], (
        'Every admitted reflection dataset reaches actual saved experiment files'
    )
    assert row['sourcesUnchanged'], (
        'Reading a reflection batch never changes the original measured files'
    )
    expected = [
        [[2, 1, 3, 9, 0.3], [2, 1, 3, 12, 0.4]],
        [[1, 2, 3, -4, 0.7]],
        [[3, 1, 2, 5, 0.2]],
    ]
    if form.endswith('tof'):
        expected[0] = [[*expected[0][0], 1.3], [*expected[0][1], 1.7]]
        expected[1][0].append(1.5)
        expected[2][0].append(1.9)
    records = row['saved']['experiments']
    assert len(records) == 3, (
        'One file contributes every distinct nonempty dataset returned by the '
        'existing reflection parser'
    )
    assert sorted(record['rows'] for record in records) == sorted(expected), (
        'Saved reflection datasets retain signed intensities, repeated indices, '
        'uncertainties and TOF wavelengths'
    )
    assert len({record['name'] for record in records}) == 3, (
        'Distinct reflection datasets have distinct persisted experiment identities'
    )
