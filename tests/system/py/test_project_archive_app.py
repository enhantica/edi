"""Exercise project route and pending-work contracts in the real app test host."""

import json
import os
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
CASES = tuple(
    'test_open:' + case + '-' + route
    for case in (
        'sc-neut-tof_taurine_fit',
        'pd-neut-cwl_cosio-d20_scan-3f',
        'sc-neut-cwl_tb2ti2o7-heidi_basic',
    )
    for route in ('folder', 'record', 'zip')
) + ('test_escape', 'test_cancel', 'test_save_pending')


@pytest.mark.parametrize('case', CASES)
def test_real_app_opens_project_routes_and_cancels_pending_work(case):
    binary = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assert binary.is_file(), 'Project opening gates require the actual built app test host'
    result = subprocess.run(
        [
            'bash',
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
        timeout=45,
        check=False,
    )
    output = result.stdout + result.stderr
    name, _, tag = case.partition(':')
    identity = re.escape('ProjectArchive::' + name + '(' + tag + ')')
    assert result.returncode == 0, 'The real app executes the project opening contract: ' + output
    assert (
        len(re.findall(r'^PASS\s*:\s*(?:edi_app::)?' + identity + r'\s*$', output, re.MULTILINE))
        == 1
    ), 'Every app project route produces exactly one completed passing receipt: ' + output
    assert not re.search(r'^(?:FAIL!|SKIP|QFATAL)\s*:', output, re.MULTILINE), (
        'An incomplete, skipped or failed app contract cannot count as opening evidence'
    )


def test_opening_measurement_declares_both_targets_for_every_real_route():
    path = ROOT / 'docs/dev/measurements/project-opening.json'
    assert path.is_file(), (
        'Fast opening first commits a measured taurine baseline and per-route targets'
    )
    data = json.loads(path.read_text())
    assert isinstance(data.get('machine'), str) and data['machine'], (
        'Opening baselines identify the measured machine'
    )
    assert data.get('project') == 'sc-neut-tof_taurine_fit', (
        'Opening measurements use the real taurine project'
    )
    assert set(data.get('routes', {})) == {'folder', 'project.edi', 'zip', 'example'}, (
        'The baseline and targets cover every project opening route'
    )
    for row in data['routes'].values():
        for phase in ('usable', 'first_display'):
            assert 0 < row['target_' + phase + '_ms'] <= row['baseline_' + phase + '_ms'], (
                'Each measured opening phase has its own positive improvement target'
            )
        assert all(
            row.get(stage + '_ms', -1) >= 0
            for stage in (
                'file_access',
                'parse',
                'model',
                'first_calculation',
                'chart',
                'reflections',
            )
        ), 'The baseline separates file access, parsing, model, calculation, chart and reflections'
