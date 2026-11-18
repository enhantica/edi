# SPDX-License-Identifier: BSD-3-Clause
"""The feedback service's attachment limits and privacy contract, without transport."""

import base64
import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
CONTACT = {'name': 'Ada User', 'email': 'ada@example.invalid', 'affiliation': 'Institute'}


def probe(operation, args):
    request = {
        'module': str(ROOT / 'app/feedback/Payload.js'),
        'operation': operation,
        'args': args,
    }
    result = subprocess.run(
        ['node', str(ROOT / 'tests/fixtures/feedback_contract/driver.cjs')],
        input=json.dumps(request),
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, 'ADR-0063: the production payload builder runs without network'
    return json.loads(result.stdout)


def invoke(files):
    return probe(
        'buildPayload',
        [
            'problem',
            'Cannot read sample.cif at line 17',
            True,
            {},
            'diagnostic log',
            '/fixture-data/account-fixture',
            'account-fixture',
            CONTACT,
            'Unreadable structure',
            files,
        ],
    )


def attachment(name='sample.cif', size=12, text='data_sample\n'):
    return {
        'name': name,
        'size': size,
        'type': 'text/plain',
        'data': base64.b64encode(text.encode()).decode(),
    }


def test_unreadable_file_is_attached_with_contact_and_diagnostic_preserved():
    source = 'data_sample\n# /fixture-data/account-fixture/sample.cif\n# user account-fixture\n'
    result = invoke([attachment(text=source, size=len(source.encode()))])
    assert 'error' not in result, (
        'ADR-0063: a valid unreadable file can accompany its problem report'
    )
    payload = result['result']
    assert payload.get('attachments'), 'ADR-0063: unreadable input is retained as an attachment'
    attached = payload['attachments'][0]
    assert attached['name'] == 'sample.cif', 'ADR-0063: the attachment keeps its file name'
    content = base64.b64decode(attached['data']).decode()
    assert '/fixture-data/account-fixture' not in content and 'account-fixture' not in content, (
        'ADR-0063: encoded attachment contents cannot reveal the home directory or account name'
    )
    assert 'data_sample' in content, 'ADR-0063: privacy scrubbing preserves the scientific input'
    assert payload['contact'] == CONTACT, 'ADR-0063: sending a problem keeps saved contact details'
    assert 'line 17' in payload['text'] and payload['log'] == 'diagnostic log', (
        'ADR-0062: the diagnostic location and log survive feedback prefill'
    )


@pytest.mark.parametrize(
    ('count', 'size', 'limit'),
    [
        (6, 1, '5 files'),
        (1, 5 * 1024 * 1024 + 1, '5 MB'),
        (3, 4 * 1024 * 1024, '10 MB'),
    ],
)
@pytest.mark.parametrize('kind', ['text', 'binary'])
def test_attachment_limit_is_named_and_never_silently_drops_files(count, size, limit, kind):
    files = [attachment(name=f'file-{index}.cif', size=size) for index in range(count)]
    if kind == 'binary':
        for file in files:
            file['name'] = file['name'].replace('.cif', '.raw')
            file['type'] = 'application/octet-stream'
    result = invoke(files)
    assert 'error' in result and limit in result['error'], (
        'ADR-0063: exceeding the file count, per-file size or total size names the refused limit'
    )


def test_empty_attachments_keep_the_existing_payload_shape():
    result = invoke([])
    assert 'error' not in result and not result['result'].get('attachments'), (
        'ADR-0063: ordinary feedback without files remains accepted'
    )


@pytest.mark.parametrize(
    'sizes',
    [
        [1, 1, 1, 1, 1],
        [5 * 1024 * 1024],
        [5 * 1024 * 1024, 5 * 1024 * 1024],
    ],
)
def test_attachment_preflight_accepts_the_declared_boundary(sizes):
    files = [
        attachment(name=f'boundary-{index}.txt', size=size) for index, size in enumerate(sizes)
    ]
    request = {
        'module': str(ROOT / 'app/feedback/Payload.js'),
        'operation': 'attachmentProblem',
        'args': [files, sizes],
    }
    run = subprocess.run(
        ['node', str(ROOT / 'tests/fixtures/feedback_contract/driver.cjs')],
        input=json.dumps(request),
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert run.returncode == 0, 'ADR-0063: attachment preflight executes offline'
    assert json.loads(run.stdout) == {'result': ''}, (
        'ADR-0063: preflight accepts five files, 5 MB per file and 10 MB total at the boundary'
    )


@pytest.mark.parametrize(
    ('name', 'mime'),
    [
        ('detector.raw', 'application/octet-stream'),
        ('calibration-\u00b5.nxs', 'application/x-hdf5'),
        ('notes.pdf', 'application/pdf'),
        ('collection.zip', 'application/zip'),
        ('extensionless', ''),
        ('screenshot.png', 'image/png'),
        ('recording.mp4', 'video/mp4'),
    ],
)
def test_any_file_type_is_accepted_without_rewriting_opaque_bytes(name, mime):
    content = bytes(range(256)) + b'opaque-file-tail\x00\xff'
    file = {
        'name': name,
        'type': mime,
        'size': len(content),
        'data': base64.b64encode(content).decode(),
    }
    ready = probe('filesProblem', [[file]])
    assert ready == {'result': ''}, (
        '2026-11-17 zip ruling: the form accepts arbitrary file types within its limits'
    )
    result = invoke([file])
    assert 'error' not in result, (
        '2026-11-17 zip ruling: arbitrary binaries and existing inline media reach the service'
    )
    attached = result['result']['attachments'][0]
    assert attached['name'] == name and attached['type'] == (mime or 'application/octet-stream'), (
        '2026-11-17 zip ruling: opaque attachment names and MIME metadata survive submission'
    )
    assert base64.b64decode(attached['data']) == content and attached['size'] == len(content), (
        '2026-11-17 zip ruling: opaque bytes are preserved for the service upload or zip'
    )


@pytest.mark.parametrize(
    ('name', 'mime'),
    [
        ('unknown-extension.custom', 'text/plain'),
        ('structure.cif', 'application/octet-stream'),
    ],
)
def test_text_bytes_are_scrubbed_without_changing_other_content(name, mime):
    source = (
        'data_\u00b5\r\n# /fixture-data/account-fixture/input.cif\r\n'
        '# account-fixture\r\n_tail 12.345\r\n'
    )
    expected = 'data_\u00b5\r\n# ~/input.cif\r\n# ~\r\n_tail 12.345\r\n'.encode()
    file = attachment(name, len(source.encode()), source)
    file['type'] = mime
    result = invoke([file])
    assert 'error' not in result, (
        '2026-11-17 zip ruling: text is recognised by its MIME type or scientific suffix'
    )
    attached = result['result']['attachments'][0]
    assert base64.b64decode(attached['data']) == expected, (
        '2026-11-17 zip ruling: scrubbed text retains Unicode, CRLF and every other byte'
    )
    assert attached['size'] == len(expected), (
        '2026-11-17 zip ruling: the transfer size describes the scrubbed bytes being archived'
    )


def test_large_text_file_stays_complete_and_out_of_message_log_and_copied_report():
    row = 'file-content-sentinel 12.345 67.890 0.123\n'
    source = (
        '# /fixture-data/account-fixture/input.xye account-fixture\n'
        + row * 2200
        + '# end \u00b5\n'
    )
    expected = ('# ~/input.xye ~\n' + row * 2200 + '# end \u00b5\n').encode()
    result = invoke([attachment('input.xye', len(source.encode()), source)])
    assert 'error' not in result, (
        '2026-11-17 zip ruling: a long scientific text file remains an accepted attachment'
    )
    payload = result['result']
    assert base64.b64decode(payload['attachments'][0]['data']) == expected, (
        '2026-11-17 zip ruling: the complete scrubbed file survives for the zip '
        'without body-size truncation'
    )
    assert payload['text'] == 'Cannot read sample.cif at line 17', (
        '2026-11-17 zip ruling: attachment text is not expanded into the feedback message'
    )
    assert payload['log'] == 'diagnostic log', (
        '2026-11-17 zip ruling: the diagnostic log remains separate from attached file content'
    )
    report = probe('reportText', [payload])
    assert 'error' not in report and 'input.xye' in report['result'], (
        '2026-11-17 zip ruling: the plain-text report names the file sent for archive delivery'
    )
    assert (
        'file-content-sentinel' not in report['result'] and 'diagnostic log' in report['result']
    ), '2026-11-17 zip ruling: copied report text keeps the log but never expands attached text'
