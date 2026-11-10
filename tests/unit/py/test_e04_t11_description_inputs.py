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
    with pytest.raises(
        AssertionError,
        match='live descriptive input must match its entire independently archived source',
    ):
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
    with pytest.raises(
        AssertionError,
        match='live descriptive input must match its entire independently archived source',
    ):
        metadata_bytes.pre_catalogue_bytes(path)


def test_description_reversal_has_no_unnamed_path_or_metadata_wildcard():
    raw = b'_edi.schema_version 3\n_metadata.purpose refinement\n_cell.length_a 4.125\n'
    assert metadata_bytes.pre_description_bytes('unreviewed/project.edi', raw) == raw, (
        'Only the two individually reviewed source paths participate in this reversal'
    )


# Exact catalogue-source pairs own a newer profile lineage than native.json.
CATALOGUE_INPUTS = [
    (
        'docs/user/cli/pd-neut-cwl_lbco-hrpt/project/experiments/hrpt.edi',
        '502941566652e6acfff532d1c9a4b5b73e7827a66d22d3fb8903078d2d310286',
        'f0c0e3839ffa3b6043992fb768eef3794ced6c869ceb7da52a57b8a387cac3f2',
        'HRPT',
        'PSI',
    ),
    (
        'docs/user/cli/pd-neut-cwl_lbco-hrpt/project/project.edi',
        '55a1f672b1825145203ea9e39399e8cb3f9df106ac390a8b58258a03ba222aa2',
        '5898148607293d5d298bd619d43bf7bda5bb19b808b5d25f16eae690690d89e1',
        'HRPT',
        'PSI',
    ),
    (
        'docs/user/cli/pd-neut-tof_ncaf-wish/project/experiments/wish_1_10.edi',
        '24dd6b5278ac7369ad528da944b324e3a5d0472cd2f448c289faeb57ec78bd27',
        '2b9be49af490454d817f78e200852c640a025a14607efe41ff0b18683c9e918b',
        'WISH',
        'ISIS',
    ),
    (
        'docs/user/cli/pd-neut-tof_ncaf-wish/project/experiments/wish_2_9.edi',
        'cc447addb349b2956750e4e8d4da74e42325acd3be70163c533f2a2b76beca65',
        '2e921f4c31ed9dd39f7a26475cf0798db7fcfe34fcfca2e34479de26d5644012',
        'WISH',
        'ISIS',
    ),
    (
        'docs/user/cli/pd-neut-tof_ncaf-wish/project/experiments/wish_3_8.edi',
        '14265d219fe6a6efa50b4b074d33ac8713ad6cb7d3cd7b013f13085cb976857f',
        'f42e3b7a75128300f69a93d4e1c0628f160ef1c42f998f8b86c2f3227d5ce3c0',
        'WISH',
        'ISIS',
    ),
    (
        'docs/user/cli/pd-neut-tof_ncaf-wish/project/experiments/wish_4_7.edi',
        'a3833fabd3d3c4b59403d5c0d995e7ece5db4e40efcdc208024d1f0fd19c8c5f',
        '21dbc4f9632d817bdba4bb0cc27529535a964ad1805d358454d05ccedebc861c',
        'WISH',
        'ISIS',
    ),
    (
        'docs/user/cli/pd-neut-tof_ncaf-wish/project/experiments/wish_5_6.edi',
        '2db147368b28fac20b85d9dd62479e73cf6c1c620e3d97c7a65224f34a29836d',
        '710d2a36a973081d25cec22d09c159684ed0df8b38a08951fd948f3d8c888556',
        'WISH',
        'ISIS',
    ),
    (
        'docs/user/cli/pd-neut-tof_ncaf-wish/project/project.edi',
        '075fc2c6b70a7588dd716e34b83a9deb965592bf3fa04dfcd77ba602887c465f',
        'e2b045f18bd1be45f64da214a3ec30bdf21a642924f48f21f709ee1e88997af0',
        'WISH',
        'ISIS',
    ),
]


@pytest.mark.parametrize(('name', 'prior', 'current', 'instrument', 'facility'), CATALOGUE_INPUTS)
def test_catalogue_description_pairs_preserve_whole_newer_source(
    name, prior, current, instrument, facility
):
    raw = (ROOT / name).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == current, (
        'Required: catalogue description pairs preserve whole newer source.'
    )
    retained = metadata_bytes.pre_description_bytes(name, raw)
    assert hashlib.sha256(retained).hexdigest() == prior, (
        'Required: catalogue description pairs preserve whole newer source.'
    )
    assert metadata_bytes.pre_catalogue_bytes(ROOT / name) == retained, (
        'Required: catalogue description pairs preserve whole newer source.'
    )
    if name.endswith('/project.edi'):
        fields = {
            '_metadata.purpose': 'refinement',
            '_metadata.dimensionality': '1D',
            '_metadata.instrument': instrument,
            '_metadata.facility': facility,
            '_metadata.polarisation': 'none',
        }
        assert metadata_bytes.records(retained, fields) == fields, (
            'Required: catalogue description pairs preserve whole newer source.'
        )
        assert metadata_bytes.records(raw, fields) == {}, (
            'Required: catalogue description pairs preserve whole newer source.'
        )
    else:
        fields = {
            '_experiment_type.dimensionality': '1d',
            '_experiment_type.polarisation': 'unpolarised',
            '_instrument.name': instrument,
            '_instrument.facility': facility,
        }
        assert metadata_bytes.records(raw, fields) == fields, (
            'Required: catalogue description pairs preserve whole newer source.'
        )
        assert metadata_bytes.records(retained, fields) == {}, (
            'Required: catalogue description pairs preserve whole newer source.'
        )
        assert metadata_bytes.records(retained, {'_peak.type'}) == metadata_bytes.records(
            raw, {'_peak.type'}
        ), 'Catalogue creation already owned its actual CWL/TOF profile spelling'
    assert metadata_bytes.remainder(raw, fields) == metadata_bytes.remainder(retained, fields), (
        'Required: catalogue description pairs preserve whole newer source.'
    )
    assert metadata_bytes.records(raw, {'_edi.schema_version'}) == {'_edi.schema_version': '3'}, (
        'Required: catalogue description pairs preserve whole newer source.'
    )


@pytest.mark.parametrize('pair', CATALOGUE_INPUTS)
@pytest.mark.parametrize('damage', ['schema', 'descriptor', 'duplicate', 'missing', 'science'])
def test_catalogue_whole_pair_refuses_unowned_or_malformed_changes(
    tmp_path, monkeypatch, pair, damage
):
    name, prior, current, instrument, _facility = pair
    raw = (ROOT / name).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == current, (
        'Required: catalogue whole pair refuses unowned or malformed changes.'
    )
    path = tmp_path / name
    path.parent.mkdir(parents=True)
    path.write_bytes(raw)
    monkeypatch.setattr(metadata_bytes, 'ROOT', tmp_path)
    assert hashlib.sha256(metadata_bytes.pre_catalogue_bytes(path)).hexdigest() == prior, (
        'Required: catalogue whole pair refuses unowned or malformed changes.'
    )
    project = name.endswith('/project.edi')
    if damage == 'schema':
        changed = raw.replace(b'_edi.schema_version 3', b'_edi.schema_version 2', 1)
    elif damage == 'descriptor':
        changed = raw.replace(instrument.encode(), b'WRONG-INSTRUMENT', 1)
    elif damage == 'duplicate':
        changed = raw + (
            b'_metadata.name duplicate\n' if project else b'_instrument.facility duplicate\n'
        )
    elif damage == 'missing':
        tag = b'_metadata.name ' if project else b'_instrument.facility '
        changed = b''.join(
            line for line in raw.splitlines(keepends=True) if not line.startswith(tag)
        )
    else:
        changed = raw + b'_unowned.scientific_parameter 1.25\n'
    assert changed != raw, 'Required: catalogue whole pair refuses unowned or malformed changes.'
    path.write_bytes(changed)
    with pytest.raises(
        AssertionError,
        match='live descriptive input must match its entire independently archived source',
    ):
        metadata_bytes.pre_catalogue_bytes(path)


@pytest.mark.parametrize(('name', 'prior', 'current', 'instrument', 'facility'), CATALOGUE_INPUTS)
def test_catalogue_reversal_refuses_cross_source_pair_and_leaves_unlisted_paths_raw(
    name, prior, current, instrument, facility
):
    del prior, current, instrument, facility
    raw = (ROOT / name).read_bytes()
    other = next(row[0] for row in CATALOGUE_INPUTS if row[0] != name)
    with pytest.raises(
        AssertionError,
        match=(
            'A complete committed description-migration input is required '
            'before retaining old bytes'
        ),
    ):
        metadata_bytes.pre_description_bytes(other, raw)
    assert metadata_bytes.pre_description_bytes('unlisted/' + name, raw) == raw, (
        'Required: catalogue reversal refuses cross source pair and leaves unlisted paths raw.'
    )


@pytest.mark.parametrize(
    ('project', 'pin'),
    [
        (
            'docs/user/cli/pd-neut-cwl_lbco-hrpt/project',
            '4bda2cd7b92130d6b331a5abff7f797a865f05d9800a54ee1e5f88c69fb5523c',
        ),
        (
            'docs/user/cli/pd-neut-tof_ncaf-wish/project',
            'b642f5393eb8ecbc41d33a926b0ae13836131cba2cc9d6a1ec921194cd482429',
        ),
    ],
)
def test_catalogue_complete_input_pin_needs_only_its_description_lineage(project, pin):
    digest = hashlib.sha256()
    source = ROOT / project
    for path in sorted(source.rglob('*')):
        if path.is_file():
            digest.update(path.relative_to(source).as_posix().encode() + b'\0')
            digest.update(metadata_bytes.pre_catalogue_bytes(path))
    assert digest.hexdigest() == pin, (
        'No historical profile-token reversal or sampled output may enter this catalogue lineage'
    )


@pytest.mark.parametrize(
    'pair',
    [row for row in CATALOGUE_INPUTS if '/experiments/' in row[0]],
)
@pytest.mark.parametrize('damage', ['profile-number', 'measured-number', 'row-order'])
def test_catalogue_reversal_refuses_real_scientific_and_data_edits(
    tmp_path, monkeypatch, pair, damage
):
    name, prior, current, _instrument, _facility = pair
    raw = (ROOT / name).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == current, (
        'Required: catalogue reversal refuses real scientific and data edits.'
    )
    path = tmp_path / name
    path.parent.mkdir(parents=True)
    path.write_bytes(raw)
    monkeypatch.setattr(metadata_bytes, 'ROOT', tmp_path)
    assert hashlib.sha256(metadata_bytes.pre_catalogue_bytes(path)).hexdigest() == prior, (
        'Required: catalogue reversal refuses real scientific and data edits.'
    )
    lines = raw.splitlines(keepends=True)
    if damage == 'profile-number':
        prefix = b'_peak.broad_gauss_'
        line = next(line for line in lines if line.startswith(prefix))
        changed = change_first_digit(raw, line)
    else:
        first = max(i for i, line in enumerate(lines) if line.startswith(b'_data.')) + 1
        if damage == 'measured-number':
            changed = change_first_digit(raw, lines[first])
        else:
            lines[first], lines[first + 1] = lines[first + 1], lines[first]
            changed = b''.join(lines)
    assert changed != raw, 'Required: catalogue reversal refuses real scientific and data edits.'
    path.write_bytes(changed)
    with pytest.raises(
        AssertionError,
        match='live descriptive input must match its entire independently archived source',
    ):
        metadata_bytes.pre_catalogue_bytes(path)
