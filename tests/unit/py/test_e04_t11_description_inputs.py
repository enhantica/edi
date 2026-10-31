"""Closed source-byte migration controls; no saved/browser/numerical output oracle."""

import hashlib
from pathlib import Path

import pytest

from tests.fixtures.table_display import metadata_bytes

ROOT = Path(__file__).resolve().parents[3]
BASE = 'docs/user/cli/pd-neut-cwl_lbco-hrpt_start-4/project/'
# Independent5ee12a7b before/after SOURCE blobs; archived catalogue-before remains separate.
INPUTS = [
    (
        'project.edi',
        'b47088ce8a1198fba99f4cca2fdee1b317230e0c66fbdc2602273344bdbab721',
        'e32ac6ec6bcb5f5e793fd830ec0674abba9981663077bd86560adf3cf252cee5',
        '0f1ffd2f044fec55a27dc56a158827d246506e7cdceab58912c0431fe568f5c8',
    ),
    (
        'experiments/hrpt.edi',
        'c7a093e4cdee2aeca6553b84cca81293b748caeb6270d2083b5a043724128c26',
        '645318644c24043b73c2aff1878a59720dd509b47db16a559b3c01ffeb0a545e',
        'c7a093e4cdee2aeca6553b84cca81293b748caeb6270d2083b5a043724128c26',
    ),
]
LEGACY = {
    '_metadata.purpose': 'refinement',
    '_metadata.dimensionality': '1D',
    '_metadata.instrument': 'HRPT',
    '_metadata.facility': 'PSI',
    '_metadata.polarisation': 'none',
}
TYPED = {
    '_experiment_type.dimensionality': '1d',
    '_experiment_type.polarisation': 'unpolarised',
    '_instrument.name': 'HRPT',
    '_instrument.facility': 'PSI',
}


@pytest.mark.parametrize(('member', 'prior', 'current', 'retained'), INPUTS)
def test_declared_metadata_migration_is_exact_source_only(member, prior, current, retained):
    name = BASE + member
    raw = (ROOT / name).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == current, (
        'The positive input is the complete independently committed metadata-only replacement'
    )
    before = metadata_bytes.pre_description_bytes(name, raw)
    assert hashlib.sha256(before).hexdigest() == prior, (
        'The reversal recovers the full pre-migration source, never a sampled saved record'
    )
    fields = LEGACY if member == 'project.edi' else TYPED
    assert metadata_bytes.records(before if member == 'project.edi' else raw, fields) == fields, (
        'The exact declared legacy-to-typed values have independent literal anchors'
    )
    assert metadata_bytes.records(raw if member == 'project.edi' else before, fields) == {}, (
        'Retired project fields leave the source and only declared typed fields are introduced'
    )
    assert metadata_bytes.remainder(raw, fields) == metadata_bytes.remainder(before, fields), (
        'Every scientific, measured, calculated, residual and other unowned byte stays exact'
    )
    assert metadata_bytes.records(raw, {'_edi.schema_version'}) == {'_edi.schema_version': '2'}, (
        'This source schema is explicitly2, not the distinct canonical saved-schema3 boundary'
    )
    assert (
        hashlib.sha256(metadata_bytes.pre_catalogue_bytes(ROOT / name)).hexdigest() == retained
    ), 'The full existing caller still reaches its original frozen source witness and hash'


def change_first_digit(data, line):
    start = data.index(line)
    offset = next(i for i, value in enumerate(line) if ord('0') <= value <= ord('9'))
    index = start + offset
    return data[:index] + (b'1' if data[index : index + 1] == b'0' else b'0') + data[index + 1 :]


@pytest.mark.parametrize(('member', 'retained'), [(row[0], row[3]) for row in INPUTS])
@pytest.mark.parametrize('damage', ['schema', 'metadata', 'duplicate', 'missing', 'extra'])
def test_full_source_caller_refuses_changed_metadata_schema_or_unowned_bytes(
    tmp_path, monkeypatch, member, retained, damage
):
    name = BASE + member
    raw = (ROOT / name).read_bytes()
    path = tmp_path / name
    path.parent.mkdir(parents=True)
    path.write_bytes(raw)
    monkeypatch.setattr(metadata_bytes, 'ROOT', tmp_path)
    assert hashlib.sha256(metadata_bytes.pre_catalogue_bytes(path)).hexdigest() == retained, (
        'Every adversary starts at the genuine complete accepted source/caller boundary'
    )
    if damage == 'schema':
        changed = raw.replace(b'_edi.schema_version 2', b'_edi.schema_version 3', 1)
    elif damage == 'metadata':
        changed = raw.replace(b'HRPT', b'WRONG', 1)
    elif damage == 'duplicate':
        changed = raw + (
            b'_metadata.name duplicate\n'
            if member == 'project.edi'
            else b'_instrument.name HRPT\n'
        )
    elif damage == 'missing':
        lines = raw.splitlines(keepends=True)
        tag = b'_metadata.name ' if member == 'project.edi' else b'_instrument.facility '
        changed = b''.join(line for line in lines if not line.startswith(tag))
    else:
        changed = raw + b'_unowned.numeric 1.25\n'
    assert changed != raw, 'The negative really alters its intended source channel'
    path.write_bytes(changed)
    with pytest.raises(AssertionError, match='complete committed description-migration input'):
        metadata_bytes.pre_catalogue_bytes(path)


@pytest.mark.parametrize('damage', ['profile', 'measured', 'row-order'])
def test_full_experiment_source_guard_refuses_genuine_scientific_row_changes(
    tmp_path, monkeypatch, damage
):
    name = BASE + 'experiments/hrpt.edi'
    raw = (ROOT / name).read_bytes()
    path = tmp_path / name
    path.parent.mkdir(parents=True)
    path.write_bytes(raw)
    monkeypatch.setattr(metadata_bytes, 'ROOT', tmp_path)
    assert hashlib.sha256(metadata_bytes.pre_catalogue_bytes(path)).hexdigest() == INPUTS[1][1], (
        'The whole real experiment is accepted before every scientific/data/order adversary'
    )
    lines = raw.splitlines(keepends=True)
    if damage == 'profile':
        line = next(line for line in lines if line.startswith(b'_peak.broad_gauss_u '))
        changed = change_first_digit(raw, line)
    else:
        first = max(i for i, line in enumerate(lines) if line.startswith(b'_data.')) + 1
        if damage == 'measured':
            changed = change_first_digit(raw, lines[first])
        else:
            lines[first], lines[first + 1] = lines[first + 1], lines[first]
            changed = b''.join(lines)
    assert changed != raw, 'Every source negative actually reaches its independent raw channel'
    path.write_bytes(changed)
    with pytest.raises(AssertionError, match='complete committed description-migration input'):
        metadata_bytes.pre_catalogue_bytes(path)


def test_description_reversal_has_no_unnamed_path_or_metadata_wildcard():
    raw = b'_edi.schema_version 3\n_metadata.purpose refinement\n_cell.length_a 4.125\n'
    assert metadata_bytes.pre_description_bytes('unreviewed/project.edi', raw) == raw, (
        'Only the two individually reviewed source paths participate in this reversal'
    )
