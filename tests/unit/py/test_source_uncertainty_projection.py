"""Archived input spelling changes retain nominal values at declared save precision."""

import hashlib
import json
import zipfile

import pytest

from tests.fixtures.table_display import source_uncertainties


def test_free_marker_projection_is_bound_to_whole_inputs_and_six_significant_digits(
    tmp_path, monkeypatch
):
    before = b'data_probe\n_value 1.23456789(52)\n_other retained\n'
    after = before.replace(b'(52)', b'()')
    digest = hashlib.sha256(before).hexdigest()
    (tmp_path / 'source-uncertainties.json').write_text(
        json.dumps({
            'probe.edi': {
                'before_sha256': digest,
                'after_sha256': hashlib.sha256(after).hexdigest(),
            }
        })
    )
    with zipfile.ZipFile(tmp_path / 'source-uncertainties.zip', 'w') as archive:
        archive.writestr(digest, before)
    monkeypatch.setattr(source_uncertainties, 'HERE', tmp_path)
    frozen = {'_value': ['1.23456789(52)'], '_other': ['retained']}
    assert source_uncertainties.reader_values('probe.edi', frozen, after) == {
        '_value': ['1.23457()'],
        '_other': ['retained'],
    }, 'The archived empty-s.u. transition retains the free marker and six significant digits'
    assert frozen == {'_value': ['1.23456789(52)'], '_other': ['retained']}, (
        'Applying the declared input transition never rewrites the original regression pin'
    )
    for damaged in (after.replace(b'1.23456789', b'1.24456789'), after + b'# extra\n'):
        with pytest.raises(AssertionError, match='entire independently archived source'):
            source_uncertainties.reader_values('probe.edi', frozen, damaged)
    with pytest.raises(AssertionError, match='frozen nominal'):
        source_uncertainties.reader_values('probe.edi', {'_value': ['9.876(5)']}, after)
    assert source_uncertainties.reader_values('another.edi', frozen, after) == frozen, (
        'A declared source transition cannot alter another input with identical numeric spelling'
    )
