"""Independent classic ZIP and malformed-text fixture controls."""

import struct
import zipfile

from tests.fixtures.project_text.generate import classic_zip, invalid_texts, project


def test_project_generator_copies_only_model_inputs(tmp_path):
    source = project(tmp_path / 'project')
    assert {path.suffix for path in source.rglob('*') if path.is_file()} == {'.edi'}, (
        'The project witness contains model inputs without unrelated fixture programs or prose'
    )


def test_classic_zip_witness_has_exactly_the_classic_limit(tmp_path):
    source = project(tmp_path / 'project')
    archive = classic_zip(tmp_path / 'classic.zip', source)
    data = archive.read_bytes()
    end = data.rfind(b'PK\x05\x06')
    assert end >= 0, 'The boundary archive carries a classic end-of-directory record'
    assert struct.unpack_from('<HH', data, end + 8) == (65535, 65535), (
        'The boundary witness uses the exact valid classic member count'
    )
    assert data[end - 20 : end - 16] != b'PK\x06\x07', (
        'The classic-count witness has no ZIP64 locator before its end record'
    )
    with zipfile.ZipFile(archive) as independent:
        rows = independent.infolist()
        assert len(rows) == 65535 and all(not row.is_dir() for row in rows), (
            'Python independently reads every regular member of the classic-limit witness'
        )
        assert (
            independent.read('structures/structure.edi')
            == (source / 'structures/structure.edi').read_bytes()
        ), 'The count-boundary archive retains its independently authored project'


def test_invalid_text_set_changes_each_required_failure_class(tmp_path):
    source = project(tmp_path / 'project')
    text = (source / 'structures/structure.edi').read_text()
    invalid = invalid_texts(text)
    assert set(invalid) == {
        'unknown-item',
        'unknown-category',
        'bad-number',
        'short-loop-row',
        'broken-block-name',
    }, 'The hand-authored invalid texts cover every validation class in the Text-tab brief'
    assert len(set(invalid.values())) == len(invalid) and all(
        v != text for v in invalid.values()
    ), 'Every invalid text is a distinct reached mutation of the valid input'
