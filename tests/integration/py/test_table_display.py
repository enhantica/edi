"""Exercise the app's real QML arithmetic against the owner's declared display rules."""

import json
import re
import shlex
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
RUNNER = ROOT / 'tests/fixtures/table_display/run_functions.cjs'


def run_functions(source, names, calls, *, fit=None):
    node = shutil.which('node')
    assert node, 'Scientific display gates require the declared Node runtime'
    request = {'source': str(source), 'functions': names, 'calls': calls, 'fit': fit}
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
    source = ROOT / 'app/qml/Components/StatusBar.qml'
    for ok, failed in ((0, 0), (7, 0), (0, 3), (7, 3)):
        actual = run_functions(
            source,
            ['counts'],
            [{'name': 'counts', 'args': []}],
            fit={'scanOk': ok, 'scanFailed': failed},
        )[0]
        expected = [
            f'<font color="#009900">{ok} ok</font>' if ok else '0 ok',
            f'<font color="#cc0000">{failed} fail</font>' if failed else '0 fail',
        ]
        assert actual == expected, (
            'Sequential status colours positive ok green and positive fail red; zero stays neutral'
        )


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
