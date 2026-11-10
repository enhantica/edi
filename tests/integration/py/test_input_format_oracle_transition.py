"""Keep independently archived byte provenance for each owner-ratified input change."""

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from tests.fixtures.cwl_family.historical import original_tokens
from tests.fixtures.loop_parameter_ids import adapt_input_oracles as generator
from tests.fixtures.metadata_transition.source_bytes import read_previous
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
        else read_previous(path)
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


@pytest.mark.parametrize(
    ('name', 'declaration'),
    [
        (
            'docs/user/cli/pd-neut-cwl_cosio-d20/project/analysis/analysis.edi',
            b'_minimizer.stop_rule shift_su\n',
        ),
        (
            'docs/user/cli/pd-neut-cwl_cosio-d20_scan/project/experiments/d20.edi',
            b'_peak.broad_lorentz_y 0.0114\n',
        ),
    ],
)
@pytest.mark.parametrize('damage', ['value', 'duplicate', 'missing', 'unowned'])
def test_decided_input_transition_retains_all_other_bytes(name, declaration, damage):
    from tests.fixtures.metadata_transition import task_inputs  # noqa: PLC0415

    raw = (ROOT / name).read_bytes()
    row = task_inputs.rows()[name]
    assert task_inputs.previous_bytes(name, raw) == task_inputs.archived(row['before_sha256']), (
        'Each accepted input transition recovers its complete independently committed source'
    )
    assert raw.count(declaration) == 1, 'Each transition witness reaches its single declared field'
    if damage == 'value':
        replacement = declaration.replace(b'shift_su', b'chi_square').replace(b'0.0114', b'0.0115')
        changed = raw.replace(declaration, replacement)
    elif damage == 'duplicate':
        changed = raw + declaration
    elif damage == 'missing':
        changed = raw.replace(declaration, b'')
    else:
        changed = raw + b'_unowned.numeric 1.25\n'
    assert changed != raw, 'The input transition adversary must alter the actual source bytes'
    with pytest.raises(AssertionError, match='entire independently archived source'):
        task_inputs.previous_bytes(name, changed)
