"""Exercise the app's real QML arithmetic against the owner's declared display rules."""

import json
import re
import shlex
import shutil
import subprocess
from pathlib import Path

import pytest

from tests.integration.py.test_scan_app_contract import (
    object_id,
    property_value,
    status_item_results,
)

ROOT = Path(__file__).resolve().parents[3]
RUNNER = ROOT / 'tests/fixtures/table_display/run_functions.cjs'


def run_functions(source, names, calls, *, fit=None, consumer=None):
    node = shutil.which('node')
    assert node, 'Scientific display gates require the declared Node runtime'
    request = {
        'source': str(source),
        'functions': names,
        'calls': calls,
        'fit': fit,
        'consumer': consumer,
    }
    result = subprocess.run(
        [node, str(RUNNER)],
        input=json.dumps(request),
        capture_output=True,
        text=True,
        check=False,
        timeout=5,
    )
    assert result.returncode == 0, (
        'Scientific display executes the real QML function body: ' + result.stderr
    )
    return json.loads(result.stdout)


def test_scientific_thresholds_and_signed_four_digit_values():
    cases = [
        (999999, '999999'),
        (1000000, '1.000e6'),
        (0.0001, '0.0001'),
        (0.00009999, '9.999e-5'),
        (0, '0'),
        (-1000000, '-1.000e6'),
        (-0.00001, '-1.000e-5'),
        (22900000, '2.290e7'),
    ]
    actual = run_functions(
        ROOT / 'app/qml/Globals/NumberText.qml',
        ['parameter', 'exponent'],
        [{'name': 'parameter', 'args': [value, 0, 64]} for value, _ in cases],
    )
    assert actual == [text for _, text in cases], (
        'Scientific display follows the owner magnitude thresholds and four significant digits'
    )


def test_display_precision_is_independent_of_cell_clip_width():
    actual = run_functions(
        ROOT / 'app/qml/Globals/NumberText.qml',
        ['parameter', 'exponent'],
        [{'name': 'parameter', 'args': [22900000, 0, width]} for width in (3, 8, 64)],
    )
    assert actual == ['2.290e7'] * 3, (
        'Number cells clip the end without changing the specified scientific precision'
    )


def test_sequential_count_colours_follow_zero_and_nonzero_state():
    for ok, failed in ((0, 0), (7, 0), (0, 3), (7, 3)):
        test_displayed_sequential_counts_consume_state_colours(False, ok, failed)


@pytest.mark.parametrize(
    'project',
    [
        'pd-neut-tof_diamond-dream_basic',
        'pd-neut-cwl_lab6-echidna_fcj-asymmetry',
        'pd-neut-tof_fe_pseudo-voigt',
        'pd-xray-cwl_lif_single',
        'pd-neut-cwl_y2o3_beta-adp',
    ],
)
def test_fullprof_comparison_projects_retain_verification_purpose(project):
    # The declared FullProf comparison corpus is an input independent of the app filter.
    text = (ROOT / f'docs/user/cli/{project}/project/project.edi').read_text()
    match = re.search(r'(?m)^_metadata\.purpose\s+(\S+)', text)
    assert match and shlex.split(match[1]) == ['verification'], (
        'FullProf comparison projects retain verification as their stored purpose'
    )
    metadata = json.loads((ROOT / 'app/examples/metadata.json').read_text())
    assert metadata['examples'][project]['values']['purpose'] == ['verification'], (
        'The app catalogue preserves verification metadata so it can exclude that workflow'
    )


@pytest.mark.parametrize('summary', [False, True], ids=['running', 'completed-summary'])
@pytest.mark.parametrize(('ok', 'failed'), [(0, 0), (7, 0), (0, 3), (7, 3)])
def test_displayed_sequential_counts_consume_state_colours(summary, ok, failed):
    fit = {
        'scanOk': ok,
        'scanFailed': failed,
        'scanning': not summary,
        'running': not summary,
        'scanSummary': summary,
        'scanFiles': '10 files',
        'elapsed': '1s',
        'eta': '2s',
        'goodnessOfFit': '1.4',
        'iterations': '8',
    }
    fit['outcome'] = 'success'
    actual = status_item_results((ROOT / 'app/qml/Components/StatusBar.qml').read_text(), fit)
    # Before: coloured HTML count fragments. After the owner's status items:
    # the shared icon and numeric value carry the state colour; the key stays neutral.
    rows = {row['key']: row for row in actual}
    for key, count, colour, icon in (
        ('OK', ok, '#009900', 'check'),
        ('Failed', failed, '#cc0000', 'times'),
    ):
        assert rows[key]['value'] == str(count) and rows[key]['icon'] == icon, (
            'The actual sequential consumer retains each supplied count and its own semantic icon'
        )
        expected = {colour} if count else {'#111111', '#666666'}
        assert rows[key]['value_color'] in expected and rows[key]['icon_color'] in expected, (
            'Running scans and completed summaries display state-coloured counts '
            'through their real consumer bindings; zero remains neutral'
        )
        assert rows[key]['key_shown'], (
            'The actual status item shows its semantic key '
            'when the caller provides room for every key'
        )
    keys = [row['key'] for row in actual]
    assert keys.index('OK') < keys.index('Failed') < keys.index('Time') < keys.index('χ²'), (
        'The displayed sequential consumer retains count, time and goodness-of-fit order'
    )
    assert rows['Time']['value'] == '1s' and rows['χ²']['value'] == '1.4', (
        'The actual shared status cells display the supplied time and goodness of fit'
    )
    assert ('Files' in rows) is summary and ('ETA' in rows) is (not summary), (
        'The actual status items distinguish running progress from a completed scan summary'
    )
    if summary:
        assert rows['Files']['value'] == '10 files', (
            'The completed summary keeps the supplied file inventory'
        )
    else:
        assert rows['ETA']['value'] == '2s', (
            'A running scan keeps the supplied remaining-time estimate'
        )


@pytest.mark.parametrize('escape', ['unused-formatter', 'coloured-zero'])
def test_scan_consumer_gate_rejects_disconnected_or_coloured_zero_display(
    tmp_path, monkeypatch, escape
):
    source = (ROOT / 'app/qml/Components/StatusBar.qml').read_text()
    ok_item = object_id(source, 'okItem')
    colour = property_value(ok_item, 'valueColor')
    if escape == 'unused-formatter':
        changed_item = ok_item.replace(
            'valueColor: ' + colour, 'valueColor: EaStyle.Colors.themeForeground'
        )
        ok, failed = 7, 3
    else:
        changed_item = ok_item.replace('valueColor: ' + colour, 'valueColor: EaStyle.Colors.green')
        ok, failed = 0, 0
    mutated = source.replace(ok_item, changed_item)
    assert mutated != source, 'The consumer escape exercise reaches the actual scan text binding'
    target = tmp_path / 'app/qml/Components/StatusBar.qml'
    target.parent.mkdir(parents=True)
    target.write_text(mutated)
    singleton = tmp_path / 'app/qml/Globals/FitOutcomes.qml'
    singleton.parent.mkdir(parents=True)
    singleton.write_text((ROOT / 'app/qml/Globals/FitOutcomes.qml').read_text())
    monkeypatch.setitem(
        test_displayed_sequential_counts_consume_state_colours.__globals__, 'ROOT', tmp_path
    )
    for summary in (False, True):
        with pytest.raises(AssertionError, match='display state-coloured counts'):
            test_displayed_sequential_counts_consume_state_colours(summary, ok, failed)
