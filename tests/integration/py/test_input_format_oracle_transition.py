"""Keep independently archived byte provenance for each owner-ratified input change."""

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from tests.fixtures.cwl_family.historical import original_tokens
from tests.fixtures.loop_parameter_ids import adapt_input_oracles as generator
from tests.fixtures.table_display.metadata_bytes import pre_catalogue_bytes

ROOT = Path(__file__).resolve().parents[3]
RECORDS = json.loads(
    (ROOT / 'tests/fixtures/loop_parameter_ids/input-format-transitions.json').read_text()
)['files']


def previous(row):
    return generator.retained_source(row)


def current(key, row):
    path = ROOT / row['file']
    return (
        original_tokens(pre_catalogue_bytes(path))
        if key.endswith('#pre-catalogue')
        else path.read_bytes()
    )


@pytest.mark.parametrize('key', sorted(RECORDS))
def test_recorded_input_change_keeps_every_non_identity_byte(key):
    row = RECORDS[key]
    before, after = previous(row), current(key, row)
    assert hashlib.sha256(before).hexdigest() == row['before_sha256'], (
        'Each newest-format input record retains its complete independently committed old source'
    )
    assert hashlib.sha256(after).hexdigest() == row['after_sha256'], (
        'Each newest-format input record binds the entire current source at its declared seam'
    )
    generator.require_transition(row['file'], before, after)


@pytest.mark.parametrize('damage', ['descriptor', 'science', 'data', 'inventory'])
def test_input_name_conversion_refuses_unrelated_retained_byte_changes(damage):
    key = 'docs/user/cli/pd-neut-cwl_lab6-11b-echidna_tch-fcj/project/experiments/echidna.edi'
    row = RECORDS[key]
    before, after = previous(row), current(key, row)
    generator.require_transition(row['file'], before, after)
    extra = {
        'descriptor': b'\n_metadata.title "unrelated change"\n',
        'science': b'\n_peak.cutoff_fwhm 3.125\n',
        'data': b'\n12.5 31.76 0.75\n',
        'inventory': b'\nloop_\n_unexpected.id\nextra\n',
    }[damage]
    with pytest.raises(AssertionError, match='retains every byte'):
        generator.require_transition(row['file'], before, after + extra)


def test_before_oracles_are_available_without_repository_history(tmp_path, monkeypatch):
    fixture = tmp_path / 'retained'
    fixture.mkdir()
    for name in ['input-format-before.zip', 'input-format-transitions.json']:
        shutil.copyfile(generator.HERE / name, fixture / name)
    monkeypatch.setattr(generator, 'HERE', fixture)
    monkeypatch.setattr(generator, 'ROOT', tmp_path / 'no-repository')
    for row in RECORDS.values():
        assert hashlib.sha256(previous(row)).hexdigest() == row['before_sha256'], (
            'Every before oracle is readable from delivered fixtures '
            'with no git history or sibling'
        )
