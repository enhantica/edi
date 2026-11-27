"""Read the original attached CIF through the running assistant."""

import json
import os
import re
from pathlib import Path

import pytest

from tests.system.py import test_e11_t5_dev_native_integration as native

ENCODINGS = ('utf-8', 'iso-8859-1')
TEXTS = {
    'utf-8': '# Échantillon témoin\ndata_quartz\n_cell_length_a 4.913\n',
    'iso-8859-1': '# Élément témoin\ndata_silicon\n_cell_length_a 5.431\n',
}
BINARY_CIF = b'data_binary\n# contains a NUL\x00\n'


@pytest.fixture(scope='module')
def cif_reads(tmp_path_factory):
    root = tmp_path_factory.mktemp('assistant-cif-reads')
    binary = Path(
        os.environ.get(
            'EDI_ASSISTANT_UI_PROBE',
            native.ROOT
            / 'build/app/assistant-ui-probe'
            / (
                'assistant_real_owner_probe.exe'
                if os.name == 'nt'
                else 'assistant_real_owner_probe'
            ),
        )
    )
    actor = native.MainActor(binary, root, {'turns': [[]]}, False)
    try:
        sources = {encoding: root / f'{encoding}.cif' for encoding in ENCODINGS}
        for encoding, source in sources.items():
            source.write_bytes(TEXTS[encoding].encode(encoding))
        sources['binary'] = root / 'binary.cif'
        sources['binary'].write_bytes(BINARY_CIF)
        token = actor.begin_current_file_selection()
        response = actor.command(
            'selected_add', token=token, paths=[str(source) for source in sources.values()]
        )['reply']
        assert response['added'], 'Attach the CIF files through the app selection'
        attached = {row['name']: row['id'] for row in actor.last['ui']['selected_files']}
        assert attached.keys() == {source.name for source in sources.values()}, (
            'The assistant receives the identity of each selected CIF'
        )
        actor.configure_turns([
            [
                native.tool_call(
                    'read_selected_file',
                    'read-' + encoding,
                    file_id=attached[source.name],
                    offset=0,
                    max_bytes=source.stat().st_size,
                )
                for encoding, source in sources.items()
            ]
        ])
        actor.connect()
        actor.request('Read both attached CIFs and identify their distinct cell lengths.')
        actor.until(
            lambda row: len(actor.responses()) == len(sources) and row['ui']['state'] == 'idle'
        )
        yield {
            encoding: (sources[encoding], response)
            for encoding, response in zip(sources, actor.responses(), strict=True)
        }
    finally:
        actor.close()


@pytest.mark.parametrize('encoding', ENCODINGS)
def test_assistant_reads_the_selected_cif(cif_reads, encoding):
    source, response = cif_reads[encoding]
    text = TEXTS[encoding]
    payload = text.encode(encoding)
    reply = response['result']
    assert reply['success'], (
        f'The assistant must be able to read the attached {encoding} CIF: {reply}'
    )
    data = native.native_result(response)['selected_text']
    assert data['text'] == text, 'Return the CIF text with its original accented characters'
    expected_encoding = 'utf-8' if encoding == 'utf-8' else 'windows-1252'
    assert data['encoding'].casefold() == expected_encoding, (
        'Tell the assistant which encoding was used to read the attached CIF'
    )
    assert (data['start'], data['end'], data['complete']) == (0, len(payload), True), (
        'A complete CIF read must report the byte extent of the original attachment'
    )
    assert source.read_bytes() == payload, 'Reading a CIF must leave its original bytes intact'


def test_binary_cif_refusal_explains_why_it_is_unreadable(cif_reads):
    source, response = cif_reads['binary']
    result = response['result']
    payload = json.loads(result['contentItems'][0]['text'])
    assert not result['success'] and 'selected_text' not in payload, (
        'The assistant reader must refuse a binary attachment without returning a text result'
    )
    assert re.search(
        r'\b(binary|NUL|null byte|bytes that no text has)\b',
        payload.get('message', ''),
        re.IGNORECASE,
    ), 'The refusal tells the assistant that the attached CIF contains binary data'
    assert source.read_bytes() == BINARY_CIF, 'Refusing the binary CIF must leave its bytes intact'
