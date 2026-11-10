"""Run-log requirements through Qt's real handler, files and process exit."""

import json
import os
import re
import subprocess
from pathlib import Path

import pytest

from tests.fixtures.onboarding.build_native import require_native

ROOT = Path(__file__).resolve().parents[3]
SOURCE = Path(os.environ.get('EDI_ONBOARDING_SOURCE_ROOT', ROOT))
HEADER = {
    'date': '2026-07-18 (+02:00)',
    'app': '8.7.6 (commit 0123456789abcdef)',
    'crysta': '5.4.3 (commit fedcba9876543210)',
    'Qt': '6.8.2',
    'OS': 'injected OS',
    'graphics': 'injected backend',
    'preferences': 'logging level Info',
}
RECORD = re.compile(
    r'(?P<time>\d{2}:\d{2}:\d{2}\.\d{3})  '
    r'\+(?P<delta>\d\.\d{3}|\d{2}\.\d{2}|\d{3}\.\d|\d{5})  '
    r'(?P<level>DEBUG   |INFO    |WARNING |ERROR   |FATAL   )  '
    r'(?P<source>app   |crysta|qml   )  '
    r'(?P<message>[^\r\n]+)  (?P<location>\S+)'
)


@pytest.fixture(scope='module')
def logger_binary():
    assert (SOURCE / 'app/src/run_log.cpp').is_file(), (
        'Per-run logging must provide the native logger exercised by the file and process gates'
    )
    return require_native(SOURCE, ROOT / 'build/onboarding-native', 'log_probe')


def invoke(binary, directory, time, operation='start', **extra):
    directory.mkdir(parents=True, exist_ok=True)
    request = directory.parent / 'log-request.json'
    request.write_text(
        json.dumps({
            'directory': str(directory),
            'time': time,
            'operation': operation,
            'header': HEADER,
            **extra,
        })
    )
    run = subprocess.run(
        [str(binary), str(request)], capture_output=True, text=True, check=False, timeout=10
    )
    assert run.returncode == 0, 'The native log operation must finish successfully: ' + run.stderr
    result = json.loads(run.stdout)
    result['terminal'] = run.stderr
    return result


def test_log_records_have_independent_clock_grammar_and_sources(logger_binary, tmp_path):
    result = invoke(logger_binary, tmp_path / 'logs', '2026-07-18T09:41:26.125+02:00', 'records')
    content = Path(result['path']).read_text(encoding='utf-8')
    lines = [line for line in content.splitlines() if not line.startswith('#')]
    records = [RECORD.fullmatch(line) for line in lines]
    assert records and all(records), 'Every non-header log line follows the declared field grammar'
    by_message = {match['message']: match for match in records}
    assert by_message['cpp-sentinel']['time'] == '09:41:26.262', (
        'The injected wall clock reaches the native record at a nontrivial millisecond offset'
    )
    assert by_message['cpp-sentinel']['delta'] == '0.137', (
        'Sub-ten-second deltas use three decimals within the five-character field'
    )
    assert by_message['qml-sentinel']['delta'] == '2.100', (
        'The QML record receives the injected nontrivial elapsed interval'
    )
    for message, source in [
        ('cpp-sentinel', 'app'),
        ('qml-sentinel', 'qml'),
        ('engine-sentinel', 'crysta'),
    ]:
        assert by_message[message]['source'].rstrip() == source, (
            'The installed Qt message handler preserves each independently emitted source kind'
        )
    assert by_message['second-line']['delta'] == '0.000', (
        'A multiline message becomes separate records without inventing elapsed time'
    )
    assert 'hidden-debug-sentinel' not in content, (
        'The source/clock grammar witness explicitly selects Info and excludes Debug'
    )
    for key, value in HEADER.items():
        assert f'# {key}: {value}' in content, (
            'The run header retains every supplied metadata field'
        )
    assert not list((tmp_path / 'logs').glob('*.running')), (
        'Normal completion removes this run marker'
    )


def test_rotation_keeps_exactly_the_last_three_normal_runs(logger_binary, tmp_path):
    directory = tmp_path / 'logs'
    paths = []
    for day in range(11, 17):
        result = invoke(logger_binary, directory, f'2026-07-{day}T09:41:26.125+02:00')
        paths.append(Path(result['path']))
        assert not result['crashed'], 'A completed earlier run never becomes a crash report'
    assert set(directory.glob('session-*.log')) == set(paths[-3:]), (
        'Rotation retains exactly the three newest normally completed runs'
    )


def test_abrupt_exit_is_detected_and_its_old_log_survives_rotation(logger_binary, tmp_path):
    directory = tmp_path / 'logs'
    crashed = invoke(logger_binary, directory, '2026-07-11T09:41:26.125+02:00', 'crash')
    assert crashed['running_markers'], 'A live run creates a running marker before any crash'
    for day in range(12, 17):
        (directory / f'session-202607{day}-094126.log').write_text('newer retained run\n')
    next_run = invoke(logger_binary, directory, '2026-07-18T09:41:26.125+02:00')
    assert next_run['crashed'] == crashed['path'], (
        'The next process identifies the run whose marker survived abrupt process exit'
    )
    assert Path(crashed['path']).is_file(), (
        'The crashed log is protected even when older than the rotation window'
    )
    assert 'retained-crash-sentinel' in next_run['crash_text'], (
        'The offered crash attachment contains the actual flushed pre-crash log bytes'
    )


@pytest.mark.parametrize('message_size', [1, 7, 19, 70, 200])
def test_log_growth_is_bounded_in_bytes(logger_binary, tmp_path, message_size):
    result = invoke(
        logger_binary,
        tmp_path / 'logs',
        '2026-07-18T09:41:26.125+02:00',
        'bounded',
        max_bytes=4096,
        message_size=message_size,
    )
    path = Path(result['path'])
    assert path.stat().st_size <= 4096, (
        'The injected byte limit includes the final truncation notice and multibyte messages'
    )
    assert path.read_text(encoding='utf-8').count('later lines') <= 1, (
        'The log emits at most one size-limit notice'
    )


@pytest.mark.parametrize(
    ('milliseconds', 'expected'),
    [(1, '0.001'), (9999, '9.999'), (50647, '50.65'), (116194, '116.2'), (12345000, '12345')],
)
def test_rounded_delta_and_padded_columns_align_messages(
    logger_binary, tmp_path, milliseconds, expected
):
    # Independent decimal examples from the recorded run-log format decision.
    result = invoke(
        logger_binary,
        tmp_path / 'logs',
        '2026-07-18T09:41:26.125+02:00',
        'columns',
        milliseconds=milliseconds,
    )
    lines = [
        line
        for line in Path(result['path']).read_text(encoding='utf-8').splitlines()
        if not line.startswith('#')
    ]
    records = [RECORD.fullmatch(line) for line in lines]
    assert len(records) == 4, (
        'The probe emits all four independently selected source/level records'
    )
    for line, record in zip(lines, records, strict=True):
        assert record is not None, (
            'Each record has a five-character delta, an eight-character level and a six-character '
            'app/crysta/qml source, with no language column: ' + repr(line)
        )
    assert [record['delta'] for record in records] == [expected] * 4, (
        'Elapsed seconds round to the independently specified five-character field'
    )
    assert [record['level'] for record in records] == [
        'DEBUG   ',
        'INFO    ',
        'WARNING ',
        'ERROR   ',
    ], 'Every emitted level occupies exactly eight characters'
    assert [record['source'] for record in records] == ['app   ', 'qml   ', 'crysta', 'app   '], (
        'The only source values are app, qml and crysta padded to six characters'
    )
    assert len({record.start('message') for record in records}) == 1, (
        'Messages start at the same column across levels and sources'
    )
    assert records[1]['location'].endswith('ColumnWitness.qml:19'), (
        'A QML component name remains in file:line rather than the source column'
    )
