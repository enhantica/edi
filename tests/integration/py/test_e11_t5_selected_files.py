"""Independent selected-byte contract draft accepted a4ea3a556; private/uncompiled/unexecuted."""

import os
from pathlib import Path

import pytest

from tests.integration.py.test_e11_t5_assistant_protocol import Host, MODEL

RAW = '12\tαβ🙂\r\n7.5000\n'
SCHEMA_KEYS = {'collection_id', 'generation', 'file_id', 'name', 'offset', 'next_offset', 'eof', 'text'}


@pytest.fixture
def files():
    binary = Path(os.environ['EDI_ASSISTANT_SELECTED_FILES_PROBE'])
    assert binary.is_file(), 'I11/I15/files: real public selected-file consumer must build first'
    host = Host(binary, reply_timeout=3)
    host.command('attach', id='project-A')
    try:
        yield host
    finally:
        host.close()


def update(host, added=(), removed=(), *, generation='0', collection='selected-A'):
    return host.command('selected_update', collection=collection, generation=generation,
                        added=list(added), removed=list(removed))


def manifest(result):
    return result['context']['selected_files']


def admit(host, rows=None):
    before = host.last
    result = update(host, rows or [{'id': 'file-a', 'name': 'measurements.txt', 'text': RAW}])
    assert result['reply']['ok'], 'I11/I15/files: trusted selected immutable bytes admit atomically'
    assert manifest(result)['generation'] == '1', 'I11/files: first real admission starts generation1'
    assert result['snapshot'] == before['snapshot'], 'I4/files: selection never edits the scientific project'
    assert result['requests'] == before['requests'], 'I15/files: choosing bytes does not send inference/upload'
    return result


def begin(host):
    host.connect()  # Trusted offline ready after host scope consent, not provider text authority.
    result = host.user('message', text='Read only the selected scope', connection_id='connection-A', model=MODEL)
    assert result['reply']['ok'], 'I15/files: trusted consented current request can inspect selected text'
    assert result['requests'][-1]['attachments'] == [], 'I15/files: selected read does not invent provider uploads'
    return host.binding()


def read(host, *, offset=0, max_bytes=4, generation='1', collection='selected-A', file_id='file-a', **extra):
    return host.tool('read_selected_file', {'collection_id': collection, 'generation': generation,
                                          'file_id': file_id, 'offset': offset, 'max_bytes': max_bytes, **extra})


def outcome(result, call_id):
    events = [row for row in result['events'] if row.get('type') == 'tool_result' and row.get('call_id') == call_id]
    assert len(events) == 1, 'I3/files: selected read emits one exactly correlated complete outcome'
    return events[0]['result']


def test_real_bytes_manifest_utf8_chunks_eof_and_continuation(files):
    admitted = admit(files)
    row = manifest(admitted)['files'][0]
    assert row['id'] == 'file-a' and row['name'] == 'measurements.txt', 'I15/files: manifest describes the selected identity'
    assert row['bytes'] == len(RAW.encode()) and row['text_readable'] is True, 'I15/files: UTF8 byte count is independent of glyph count'
    assert RAW not in str(manifest(admitted)), 'I15/files: manifest does not dump selected content'
    original = begin(files)
    offset, chunks, calls = 0, [], []
    while offset <= len(RAW.encode()):
        result = read(files, offset=offset)
        assert result['reply']['ok'], 'I15/files: current read needs no scientific plan approval'
        call = f'call-{files.serial}'
        value = outcome(result, call)
        assert set(value) == SCHEMA_KEYS, 'I3/files: complete read object has exactly the declared wrapper'
        assert value['generation'] == '1' and value['offset'] == str(offset), 'I3/files: offsets/generation remain exact decimals'
        encoded = value['text'].encode()
        assert len(encoded) <= 4 and RAW.encode()[offset:offset + len(encoded)] == encoded, 'I15/files: chunks preserve exact source bytes/UTF8 boundaries'
        chunks.append(encoded); calls.append((call, value))
        if value['eof']:
            assert value['next_offset'] is None, 'I15/files: only complete EOF uses a null continuation'
            break
        assert value['next_offset'] == str(offset + len(encoded)) and encoded, 'I15/files: complete chunks advance without zero-progress loops'
        offset += len(encoded)
    assert b''.join(chunks) == RAW.encode(), 'I11/files: tabs/newlines/Unicode/numeric spelling survive complete reconstruction'
    result = read(files, offset=len(RAW.encode()))
    eof = outcome(result, f'call-{files.serial}')
    assert eof['text'] == '' and eof['eof'] and eof['next_offset'] is None, 'I15/files: reading exact EOF is empty success'
    continued = files.provider('turn_finished', **original, status='completed')
    history = continued['requests'][-1]['history']
    for call, value in calls:
        assert any(item.get('type') == 'tool_result' and item.get('call_id') == call and item['result'] == value for item in history), 'I3/I15/files: physical continuation retains each complete original read outcome'
    assert continued['snapshot'] == admitted['snapshot'], 'I4/files: all read/continuation work leaves actual project exact'


@pytest.mark.parametrize('fields,code', [
    ({'generation': '0'}, 'stale_revision'), ({'collection': 'foreign'}, 'stale_revision'),
    ({'file_id': 'unselected'}, 'invalid_argument'), ({'offset': 4}, 'invalid_argument'),
    ({'offset': 8}, 'invalid_argument'), ({'offset': 1000}, 'invalid_argument'),
    ({'offset': -1}, 'invalid_argument'), ({'max_bytes': 3}, 'invalid_argument'),
    ({'max_bytes': 65537}, 'resource_exhausted'), ({'path': '/unselected/owned-marker'}, 'invalid_argument'),
])
def test_wrong_identity_range_and_path_never_grant_read(files, fields, code):
    admitted = admit(files); begin(files)
    result = read(files, **fields)
    assert not result['reply']['ok'] and result['reply']['code'] == 'edi.assistant.' + code, 'I3/I15/files: invalid current read refuses with declared category'
    assert result['snapshot'] == admitted['snapshot'], 'I4/files: refusal changes no accepted scientific state'


@pytest.mark.parametrize('raw', [[0, 65], [255, 254, 0], [240, 159, 153]])
def test_selected_binary_and_invalid_utf8_stay_visible_but_not_text(files, raw):
    admitted = admit(files, [{'id': 'file-a', 'name': 'opaque.gpx', 'bytes': raw}])
    assert manifest(admitted)['files'][0]['text_readable'] is False, 'I11/files: nontext remains explicitly selected without pretending GPX import'
    begin(files); result = read(files)
    assert not result['reply']['ok'] and result['reply']['code'] == 'edi.assistant.unsupported_format', 'I15/files: binary/NUL/invalidUTF8 never executes or silently decodes'


@pytest.mark.parametrize('name', ['../outside.txt', '/absolute.txt', '.', 'a/../b', 'a//b', 'nul\0.txt'])
def test_invalid_names_preserve_prior_admitted_collection(files, name):
    before = admit(files)
    result = update(files, [{'id': 'new', 'name': name, 'text': 'data'}], generation='1')
    assert not result['reply']['ok'], 'I15/files: invalid collection-relative names cannot extend authority'
    assert manifest(result) == manifest(before) and result['snapshot'] == before['snapshot'], 'I4/I15/files: refused transaction preserves exact prior collection/project'


def test_append_remove_noop_busy_and_owner_reset(files):
    before = admit(files)
    noop = update(files, generation='1')
    assert noop['reply']['ok'] and manifest(noop) == manifest(before), 'I15/files: empty operation does not consume a generation'
    added = update(files, [{'id': 'b', 'name': '<b>literal.txt', 'text': 'selected data'}], generation='1')
    assert added['reply']['ok'] and manifest(added)['generation'] == '2', 'I15/files: one complete addition increments exactly once'
    binding = begin(files)
    busy = update(files, removed=['b'], generation='2')
    assert not busy['reply']['ok'] and busy['reply']['code'] == 'edi.assistant.busy', 'I15/files: active bound work prevents membership edits'
    assert manifest(busy) == manifest(added), 'I15/files: busy refusal cannot partially remove bytes'
    files.provider('turn_finished', **binding, status='completed')
    removed = update(files, removed=['b'], generation='2')
    assert removed['reply']['ok'] and manifest(removed)['generation'] == '3', 'I15/files: idle explicit removal is atomic and monotonic'
    files.command('mutate', path='structure.cell.length_a', value=4.41)
    assert manifest(files.last) == manifest(removed), 'I4/files: ordinary manual edit retains selected immutable bytes'
    cleared = files.command('detach')
    assert manifest(cleared)['files'] == [], 'I15/files: explicit project owner retirement revokes the collection'


@pytest.mark.parametrize('added,removed', [
    ([{'id': 'file-a', 'name': 'other.txt', 'text': 'x'}], []),
    ([{'id': 'b', 'name': 'measurements.txt', 'text': 'x'}], []),
    ([], ['missing']), ([], ['file-a', 'file-a']),
    ([{'id': 'b', 'name': 'b.txt', 'text': 'x'}, {'id': 'b', 'name': 'c.txt', 'text': 'y'}], []),
])
def test_duplicate_and_unknown_members_do_not_partially_commit(files, added, removed):
    before = admit(files); result = update(files, added, removed, generation='1')
    assert not result['reply']['ok'], 'I15/files: duplicate/unknown membership is an atomic refusal'
    assert manifest(result) == manifest(before) and result['requests'] == before['requests'], 'I15/files: no refused batch admits new handles or upload'


@pytest.mark.parametrize('added', [
    [{'id': str(i), 'name': f'{i}.txt', 'text': 'x'} for i in range(33)],
    [{'id': 'large', 'name': 'large.txt', 'repeat': 16777217}],
    [{'id': str(i), 'name': f'{i}.txt', 'repeat': 16777216} for i in range(4)] + [{'id': 'extra', 'name': 'extra.txt', 'text': 'x'}],
])
def test_declared_count_file_and_aggregate_limits_refuse_atomically(files, added):
    before = files.last; result = update(files, added)
    assert not result['reply']['ok'] and result['reply']['code'] == 'edi.assistant.resource_exhausted', 'I3/files: count/perfile/aggregate ceilings refuse with resource category'
    assert manifest(result) == manifest(before) and result['snapshot'] == before['snapshot'], 'I3/I4/files: quota never leaves a partial collection/project'


@pytest.mark.parametrize('added', [
    [{'id': str(i), 'name': f'{i}.txt', 'text': 'x'} for i in range(32)],
    [{'id': 'exact-file', 'name': 'exact.txt', 'repeat': 16777216}],
    [{'id': str(i), 'name': f'{i}.txt', 'repeat': 16777216} for i in range(4)],
    [{'id': 'name', 'name': 'Å' * 254 + '.txt', 'text': 'x'}],
])
def test_declared_exact_boundaries_have_supported_positive_controls(files, added):
    result = update(files, added)
    assert result['reply']['ok'], 'I3/I15/files: exact declared count/file/aggregate/UTF8-name limits are supported rather than blanket refusal'
    assert len(manifest(result)['files']) == len(added), 'I15/files: positive boundary admits every original member atomically'
    assert sum(item['bytes'] for item in manifest(result)['files']) == sum(item.get('repeat', len(item.get('text', '').encode())) for item in added), 'I15/files: admitted boundary metadata exactly counts independently selected bytes'


@pytest.mark.parametrize('name', ['x' * 513, 'Å' * 255 + '.txt'])
def test_utf8_name_budget_checks_encoded_bytes_without_partial_admission(files, name):
    before = admit(files)
    result = update(files, [{'id': 'b', 'name': name, 'text': 'x'}], generation='1')
    assert not result['reply']['ok'] and result['reply']['code'] == 'edi.assistant.resource_exhausted', 'I3/I15/files: encoded name budget refuses with the declared resource category'
    assert manifest(result) == manifest(before), 'I15/files: oversized display name cannot replace the original admitted collection'


@pytest.mark.parametrize('generation,collection', [('0', 'selected-A'), ('2', 'selected-A'), ('1', 'foreign')])
def test_stale_update_generation_and_collection_preserve_original(files, generation, collection):
    before = admit(files)
    result = update(files, removed=['file-a'], generation=generation, collection=collection)
    assert not result['reply']['ok'] and result['reply']['code'] == 'edi.assistant.stale_revision', 'I3/I15/files: exact expected owner/generation is required for membership changes'
    assert manifest(result) == manifest(before), 'I15/files: stale update cannot silently remove currently admitted bytes'


@pytest.mark.parametrize('change', [
    {'generation': 1}, {'offset': '0'}, {'offset': 0.5}, {'max_bytes': '4'}, {'max_bytes': 4.5},
    {'file_id': ''}, {'collection_id': ''},
])
def test_read_required_types_do_not_coerce_provider_arguments(files, change):
    before = admit(files); begin(files)
    arguments = {'collection_id': 'selected-A', 'generation': '1', 'file_id': 'file-a', 'offset': 0, 'max_bytes': 4}
    arguments.update(change)
    result = files.tool('read_selected_file', arguments)
    assert not result['reply']['ok'], 'I3/I15/files: exact required read types and identities are not supplied by coercion'
    assert result['snapshot'] == before['snapshot'], 'I4/files: malformed selected read arguments have no scientific mutation'


@pytest.mark.parametrize('prior_rows,extra', [
    ([{'id': str(i), 'name': f'{i}.txt', 'text': 'x'} for i in range(32)], [{'id': 'extra', 'name': 'extra.txt', 'text': 'x'}]),
    ([{'id': str(i), 'name': f'{i}.txt', 'repeat': 16777216} for i in range(4)], [{'id': 'extra', 'name': 'extra.txt', 'text': 'x'}]),
])
def test_append_budget_includes_existing_admitted_owners(files, prior_rows, extra):
    before = update(files, prior_rows)
    assert before['reply']['ok'], 'I3/I15/files: exact-boundary existing collection is a real admitted positive control'
    after = update(files, extra, generation='1')
    assert not after['reply']['ok'] and after['reply']['code'] == 'edi.assistant.resource_exhausted', 'I3/I15/files: append ceilings charge existing owners plus new members, not just the incoming batch'
    assert manifest(after) == manifest(before) and after['snapshot'] == before['snapshot'], 'I4/I15/files: append quota refusal preserves complete original ownership and project'
