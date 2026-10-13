"""Exercise the app's real QML arithmetic against the owner's declared display rules."""

import json
import re
import shlex
import shutil
import subprocess
from html.parser import HTMLParser
from pathlib import Path

import pytest

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
    pieces = run_functions(
        ROOT / 'app/qml/Components/StatusBar.qml', [], [], fit=fit, consumer='scan'
    )

    class Ink(HTMLParser):
        def __init__(self, colour):
            super().__init__()
            self.stack = [('root', colour)]
            self.characters = []

        def handle_starttag(self, tag, attrs):
            values = dict(attrs)
            colour = values.get('color', self.stack[-1][1])
            style = re.search(r'(?:^|;)\s*color\s*:\s*([^;]+)', values.get('style', ''))
            self.stack.append((tag, style[1].strip() if style else colour))

        def handle_endtag(self, tag):
            for index in range(len(self.stack) - 1, 0, -1):
                if self.stack[index][0] == tag:
                    self.stack = self.stack[:index]
                    break

        def handle_data(self, data):
            self.characters.extend((char, self.stack[-1][1]) for char in data)

    characters = []
    for piece in pieces:
        assert piece['format'] in {1, 2}, (
            'The visible count Text interprets colour markup instead of displaying literal tags'
        )
        ink = Ink(piece['color'])
        ink.feed(piece['text'])
        characters.extend(ink.characters)
        characters.append((' ', '#111111'))
    displayed = ''.join(char for char, _ in characters)
    expected_ok, expected_fail = f'{ok} ok', f'{failed} fail'
    assert expected_ok in displayed and expected_fail in displayed, (
        'Running scans and completed summaries display both supplied count words'
    )
    for word, count, colour in ((expected_ok, ok, '#009900'), (expected_fail, failed, '#cc0000')):
        start = displayed.index(word)
        actual = {value for _, value in characters[start : start + len(word)]}
        assert actual == {colour} if count else actual <= {'#111111', '#666666'}, (
            'Running scans and completed summaries display state-coloured counts '
            'through their real consumer bindings; zero remains neutral'
        )
    assert (
        displayed.index(expected_ok)
        < displayed.index(expected_fail)
        < displayed.index('1s')
        < displayed.index('χ² 1.4')
    ), 'The visible sequential consumer retains count, time and goodness-of-fit order'
    assert ('10 files' in displayed) == summary and ('eta 2s' in displayed) == (not summary), (
        'The actual consumer distinguishes running progress from the completed scan summary'
    )


@pytest.mark.parametrize('escape', ['unused-formatter', 'coloured-zero'])
def test_scan_consumer_gate_rejects_disconnected_or_coloured_zero_display(
    tmp_path, monkeypatch, escape
):
    source = (ROOT / 'app/qml/Components/StatusBar.qml').read_text()
    neutral = '[qsTr("%1 ok").arg(bar.fit.scanOk), qsTr("%1 fail").arg(bar.fit.scanFailed)]'
    if escape == 'unused-formatter':
        mutated = source.replace('fitArea.counts()', neutral)
        ok, failed = 7, 3
    else:
        start = source.index('id: numberText')
        tail = re.sub(
            r'(?m)^(\s*color:)[^\n]+', r'\1 EaStyle.Colors.green', source[start:], count=1
        )
        mutated = source[:start] + tail
        ok, failed = 0, 0
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
