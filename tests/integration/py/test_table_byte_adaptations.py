"""Closed-form escape controls for retained byte witnesses."""

import hashlib
import json
import zipfile

import pytest

from tests.fixtures.table_display import metadata_bytes, stored_id_bytes


@pytest.mark.parametrize(
    'damage', ['title', 'duplicate', 'missing', 'extra', 'value', 'data', 'file']
)
def test_descriptive_saved_mapping_refuses_every_nonpresentation_change(tmp_path, damage):
    source, old, new = (tmp_path / name for name in ('input', 'old', 'new'))
    for path in (source, old, new):
        path.mkdir()
        (path / 'measured.dat').write_bytes(b'12.5 31.25 0.75\n')
    before = b'_metadata.name fixed\n_metadata.title "old"\n_metadata.description ?\n\n'
    after = before.replace(b'"old"', b'"new"')
    (source / 'project.edi').write_bytes(after)
    (old / 'project.edi').write_bytes(before)
    (new / 'project.edi').write_bytes(after)
    metadata_bytes.check_saved(source, old, new)
    target = new / 'project.edi'
    if damage == 'title':
        target.write_bytes(after.replace(b'"new"', b'"wrong"'))
    elif damage == 'duplicate':
        target.write_bytes(after + b'_metadata.title "new"\n')
    elif damage == 'missing':
        target.write_bytes(after.replace(b'_metadata.title "new"\n', b''))
    elif damage == 'extra':
        target.write_bytes(after + b'_metadata.purpose "verification"\n')
    elif damage == 'value':
        target.write_bytes(after.replace(b'fixed', b'changed'))
    elif damage == 'data':
        (new / 'measured.dat').write_bytes(b'12.5 31.26 0.75\n')
    else:
        (new / 'extra.edi').write_bytes(b'data_unexpected\n')
    with pytest.raises(AssertionError):
        metadata_bytes.check_saved(source, old, new)


@pytest.mark.parametrize('damage', ['key', 'order', 'value', 'missing', 'extra', 'missing-key'])
def test_stored_key_projection_retains_identity_values_order_and_inventory(tmp_path, damage):
    source, saved = tmp_path / 'input', tmp_path / 'saved'
    data = (
        b'data_bank\nloop_\n_background.id\n_background.position\n_background.intensity\n'
        b'left 20.125 3.75\nright 100.5 9.25\n\n'
        b'loop_\n_excluded_region.id\n_excluded_region.start\n_excluded_region.end\n'
        b'gap 1.25 4.5\nend 7.125 9.75\n'
    )
    for path in (source, saved):
        (path / 'experiments').mkdir(parents=True)
        (path / 'experiments/bank.edi').write_bytes(data)
        (path / 'measured.dat').write_bytes(b'12.5 31.25 0.75\n')
    expected = data.replace(b'left ', b'1 ').replace(b'right ', b'2 ')
    expected = expected.replace(b'gap ', b'1 ').replace(b'end ', b'2 ')
    good = stored_id_bytes.ordinal_copy(source, saved, tmp_path / 'control')
    assert (good / 'experiments/bank.edi').read_bytes() == expected, (
        'The retained ordinal projection changes only the declared key lexemes'
    )
    target = saved / 'experiments/bank.edi'
    if damage == 'key':
        target.write_bytes(data.replace(b'left ', b'wrong '))
    elif damage == 'order':
        target.write_bytes(
            data.replace(
                b'left 20.125 3.75\nright 100.5 9.25', b'right 100.5 9.25\nleft 20.125 3.75'
            )
        )
    elif damage == 'value':
        target.write_bytes(data.replace(b'3.75', b'3.76'))
    elif damage == 'missing':
        target.write_bytes(data.replace(b'end 7.125 9.75\n', b''))
    elif damage == 'missing-key':
        target.write_bytes(
            data.replace(b'_background.id\n', b'').replace(b'left ', b'').replace(b'right ', b'')
        )
    else:
        (saved / 'unexpected.dat').write_bytes(b'12.5 31.25 0.75\n')
    if damage in {'key', 'order', 'missing', 'missing-key'}:
        with pytest.raises(AssertionError):
            stored_id_bytes.ordinal_copy(source, saved, tmp_path / 'escape')
    else:
        result = stored_id_bytes.ordinal_copy(source, saved, tmp_path / 'escape')
        actual = {
            p.relative_to(result).as_posix(): p.read_bytes()
            for p in result.rglob('*')
            if p.is_file()
        }
        assert actual != {
            'experiments/bank.edi': expected,
            'measured.dat': b'12.5 31.25 0.75\n',
        }, 'The full byte witness must expose every changed scientific value or inventory entry'


def test_legacy_input_without_a_key_column_requires_generated_saved_keys(tmp_path):
    source, saved = tmp_path / 'input', tmp_path / 'saved'
    before = (
        b'data_bank\nloop_\n_background.position\n_background.intensity\n20.125 3.75\n100.5 9.25\n'
    )
    after = before.replace(b'loop_\n', b'loop_\n_background.id\n')
    after = after.replace(b'20.125 ', b'1 20.125 ').replace(b'100.5 ', b'2 100.5 ')
    for directory, data in ((source, before), (saved, after)):
        (directory / 'experiments').mkdir(parents=True)
        (directory / 'experiments/bank.edi').write_bytes(data)
    control = stored_id_bytes.ordinal_copy(source, saved, tmp_path / 'control')
    assert (control / 'experiments/bank.edi').read_bytes() == after, (
        'Legacy inputs without declared keys generate exactly the one-based stored row keys'
    )
    (saved / 'experiments/bank.edi').write_bytes(after.replace(b'2 100.5', b'9 100.5'))
    with pytest.raises(AssertionError):
        stored_id_bytes.ordinal_copy(source, saved, tmp_path / 'escape')


@pytest.mark.parametrize(
    'damage',
    [
        'scientific',
        'unknown',
        'duplicate',
        'missing',
        'sample',
        'beam',
        'radiation',
        'scattering',
        'fitting',
    ],
)
def test_source_metadata_archive_refuses_rebanked_whitelist_escapes(tmp_path, monkeypatch, damage):
    name = 'docs/user/cli/sample/project/project.edi'
    before = b'_metadata.title "old"\n_cell.length_a 4.125\n'
    after = before.replace(b'"old"', b'"new"')
    if damage == 'scientific':
        after = after.replace(b'4.125', b'4.126')
    elif damage == 'unknown':
        after += b'_metadata.unknown "extra"\n'
    elif damage == 'duplicate':
        after += b'_metadata.title "new"\n'
    elif damage == 'missing':
        after = after.replace(b'_cell.length_a 4.125\n', b'')
    else:
        changed = {
            'sample': b'_experiment_type.sample_form "single crystal"\n',
            'beam': b'_experiment_type.beam_mode "time-of-flight"\n',
            'radiation': b'_experiment_type.radiation_probe "xray"\n',
            'scattering': b'_experiment_type.scattering_type "total"\n',
            'fitting': b'_fitting_mode.type "joint"\n',
        }
        after += changed[damage]
    with zipfile.ZipFile(tmp_path / 'metadata-inputs.zip', 'w') as archive:
        archive.writestr('before/' + name, before)
        archive.writestr('after/' + name, after)
    (tmp_path / 'metadata-inputs.json').write_text(
        json.dumps({
            'files': {name: [hashlib.sha256(data).hexdigest() for data in (before, after)]}
        })
    )
    monkeypatch.setattr(metadata_bytes, 'HERE', tmp_path)
    with pytest.raises(AssertionError):
        metadata_bytes.pair(name)
