"""Exercise project route and pending-work contracts in the real app test host."""

import base64
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import zipfile
from pathlib import Path

import edi
import pytest

from tests.fixtures.native_process import environment_bash
from tests.fixtures.project_archive.recalculated_copy import compare_members, input_bytes

ROOT = Path(__file__).resolve().parents[3]
CASES = tuple(
    'test_open:' + case + '-' + route
    for case in (
        'sc-neut-tof_taurine-senju',
        'pd-neut-cwl_cosio-d20_scan-3f',
        'sc-neut-cwl_tb2ti2o7-heidi_basic',
    )
    for route in ('folder', 'record', 'zip')
) + ('test_project_actions', 'test_escape', 'test_cancel', 'test_save_pending')
CASES += tuple(
    action + ':' + accept
    for action in ('test_create_completion', 'test_open_choice_completion')
    for accept in ('enter', 'ok')
)
CASES += tuple(
    'test_open_dialog:' + project + '-' + route
    for project in (
        'sc-neut-tof_taurine-senju',
        'pd-neut-cwl_cosio-d20_scan-3f',
        'sc-neut-cwl_tb2ti2o7-heidi_basic',
    )
    for route in ('folder', 'zip')
)
CASES += tuple(
    'test_drop:' + project + '-' + route
    for project in (
        'sc-neut-tof_taurine-senju',
        'pd-neut-cwl_cosio-d20_scan-3f',
        'sc-neut-cwl_tb2ti2o7-heidi_basic',
    )
    for route in ('folder', 'record', 'zip')
)
CASES += tuple(
    'test_save_copy:' + project + '-' + kind
    for project in (
        'sc-neut-tof_taurine-senju',
        'pd-neut-cwl_cosio-d20_scan-3f',
        'sc-neut-cwl_tb2ti2o7-heidi_basic',
    )
    for kind in ('folder', 'zip')
)
CASES += tuple(
    'test_save_zip:' + project
    for project in (
        'sc-neut-tof_taurine-senju',
        'pd-neut-cwl_cosio-d20_scan-3f',
        'sc-neut-cwl_tb2ti2o7-heidi_basic',
    )
) + (
    'test_save_folder_choice',
    'test_save_dialog_layout',
    'test_save_unwritable:read-only-zip',
    'test_save_unwritable:bundled-example',
)


def run_archive_actor(case):
    binary = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assert binary.is_file(), 'Project opening gates require the actual built app test host'
    result = subprocess.run(
        [
            environment_bash(),
            str(ROOT / 'tests/fixtures/scan_views/run.sh'),
            str(binary),
            '-input',
            str(ROOT / 'tests/unit/app/tst_project_archive.qml'),
            '-o',
            '-,txt',
            'ProjectArchive::' + case,
        ],
        capture_output=True,
        text=True,
        timeout=90 if case == 'test_save_copy' else 45,
        check=False,
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0, 'The real app executes the project opening contract: ' + output
    return output


@pytest.fixture(scope='module')
def copy_actors():
    # One display and Qt process; the real test still opens, saves and tears down
    # each independent folder/ZIP case. Keep each actor's evidence separate.
    output = run_archive_actor('test_save_copy')
    return {
        case: '\n'.join(
            line
            for line in output.splitlines()
            if 'ProjectArchive::test_save_copy(' + case.split(':', 1)[1] + ')' in line
        )
        for case in CASES
        if case.startswith('test_save_copy:')
    }


@pytest.fixture
def archive_actor(request):
    case = request.node.callspec.params['case']
    return (
        request.getfixturevalue('copy_actors')[case]
        if case.startswith('test_save_copy:')
        else run_archive_actor(case)
    )


@pytest.mark.parametrize('case', CASES)
def test_real_app_opens_project_routes_and_cancels_pending_work(case, tmp_path, archive_actor):
    output = archive_actor
    if case.startswith(('test_create_completion:', 'test_open_choice_completion:')):
        (tmp_path / 'dialog-completion.log').write_text(output)
    name, _, tag = case.partition(':')
    identity = re.escape('ProjectArchive::' + name + '(' + tag + ')')
    assert (
        len(re.findall(r'^PASS\s*:\s*(?:edi_app::)?' + identity + r'\s*$', output, re.MULTILINE))
        == 1
    ), 'Every app project route produces exactly one completed passing receipt: ' + output
    assert not re.search(r'^(?:FAIL!|SKIP|QFATAL)\s*:', output, re.MULTILINE), (
        'An incomplete, skipped or failed app contract cannot count as opening evidence'
    )

    if (case.startswith('test_open:') and case.endswith('-zip')) or case.startswith((
        'test_save_zip:',
        'test_save_copy:',
    )):
        assert_app_archive_matches_exports(output, tmp_path)


def assert_app_archive_matches_exports(output, tmp_path):
    rows = re.findall(r'PROJECT_ARCHIVE_EVIDENCE (\{[^\n]+\})', output)
    assert len(rows) == 1, 'A saved app ZIP supplies exactly one actual folder/archive receipt'
    evidence = json.loads(rows[0])
    expected = {name: base64.b64decode(body) for name, body in evidence['original'].items()}
    if 'archive' in evidence:
        with zipfile.ZipFile(io.BytesIO(base64.b64decode(evidence['archive']))) as archive:
            names = archive.namelist()
            assert len(names) == len(set(names)), 'App ZIP saves contain no duplicate members'
            actual = {name: archive.read(name) for name in names if not name.endswith('/')}
    else:
        actual = {name: base64.b64decode(body) for name, body in evidence['saved'].items()}
    if evidence['kind'] == 'copy':
        compare_members(expected, actual, tmp_path, edi)
    else:
        assert actual == expected, (
            'App ZIP rewrites retain every canonical folder member and report byte exactly'
        )
    report = (
        b'<p>Independently authored report</p>\n'
        if evidence['kind'] == 'opened-rewrite'
        else b'<p>Independent carried report</p>\n'
    )
    assert actual['reports/opaque.html'] == report, (
        'Save a copy and ordinary ZIP rewrites retain independently authored report bytes'
    )
    if evidence['kind'].endswith('rewrite'):
        assert evidence['name'].encode() in actual['project.edi'], (
            'The rewritten ZIP really contains the edited project name'
        )
    folder = tmp_path / 'canonical-folder'
    for name, body in actual.items():
        path = folder / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
    python_zip = tmp_path / 'python.zip'
    edi.Project.load(folder).export_zip(python_zip)
    cli_zip = tmp_path / 'cli.zip'
    completed = subprocess.run(
        [sys.executable, '-m', 'edi', 'export', str(folder), '-o', str(cli_zip)],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    assert completed.returncode == 0, (
        'The CLI exports the app-saved project successfully: ' + completed.stderr
    )
    for path in (python_zip, cli_zip):
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            assert len(names) == len(set(names)), 'CLI and Python exports have unique members'
            exported = {name: archive.read(name) for name in names if not name.endswith('/')}
        assert exported == actual, (
            'Save a copy as ZIP, CLI export and Python export have identical members and bytes'
        )


def test_opening_measurement_declares_both_targets_for_every_real_route():
    folder = ROOT / 'tests/fixtures/project_opening'
    data = json.loads((folder / 'baseline.json').read_text())
    assert (
        hashlib.sha256((folder / 'baseline.tsv').read_bytes()).hexdigest() == data['raw_sha256']
    ), 'Opening targets retain the complete independently recorded measurement rows'
    assert data['machine'] == 'visa-prod-2224', 'Opening targets name their measured machine'
    assert data['project'] == 'sc-neut-tof_taurine_fit', (
        'The original opening baseline keeps the identity that was actually measured'
    )
    assert data['current_project'] == 'sc-neut-tof_taurine-senju', (
        'Current opening actors use the renamed catalogue taurine project'
    )
    assert set(data['routes']) == {'folder', 'project.edi', 'zip', 'example'}, (
        'The baseline and targets cover every project opening route'
    )
    for name, phases in data['routes'].items():
        assert set(phases) == {'cold', 'warm'}, (
            'Each route retains cold and warm opening baselines'
        )
        for phase, row in phases.items():
            expected_display = (600 if name == 'example' else 500) if phase == 'cold' else 800
            expected_usable = 1000 if phase == 'cold' else 1500
            assert row['target_first_display_ms'] == expected_display, (
                'First-display bounds retain the published per-route cold/warm targets'
            )
            assert row['target_usable_ms'] == expected_usable, (
                'Usable-model bounds retain the published cold/warm targets'
            )
            assert 0 < row['target_first_display_ms'] < row['baseline_first_display_ms'], (
                'Each measured display baseline has a positive improvement target'
            )
            assert 0 < row['target_usable_ms'] < row['baseline_usable_ms'], (
                'Each measured usable-model baseline has a positive improvement target'
            )
            assert {
                'request',
                'loaded',
                'view-model',
                'replaced',
                'published-enter',
                'published-signalled',
                'first-frame',
                'calculated-frame',
            } <= set(row['marks_ms']), (
                'The retained baseline separates loading, view models, '
                'page rebuild, publication and frames'
            )


@pytest.mark.parametrize('changed', ['scalar', 'loop'])
def test_recalculated_copy_cannot_hide_inputs_after_computed_categories(changed):
    before = (
        b'data_phase\n_cell.length_a 5.123\n\nloop_\n_atom_site.id\n_atom_site.fract_x\nA 0.125\n'
    )
    derived = b'loop_\n_space_group_symop.id\n_space_group_symop.operation_xyz\n1 x,y,z\n\n'
    after = before.replace(b'loop_', derived + b'loop_', 1)
    assert input_bytes(after) == input_bytes(before), (
        'Dictionary-ordered computed geometry may appear between unchanged input categories'
    )
    escaped = (
        after.replace(b'5.123', b'5.124')
        if changed == 'scalar'
        else after.replace(b'0.125', b'0.126')
    )
    assert input_bytes(escaped) != input_bytes(before), (
        'A changed scientific input before or after computed geometry '
        'cannot borrow the copy exemption'
    )
