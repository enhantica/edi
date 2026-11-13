"""The retired-slot projection preserves every other prechange codec byte."""

import copy
import hashlib
import json
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[2] / 'fixtures/assistant_dev_integration'
ORIGINAL = '8b300f35b31f9f5b9bf54a5af9e4e470255f8983817ef4f463b91d46707d7800'
RETIRED = b'    put_optional_parameter(out, experiment.absorption.abscor2, scope);\n'
FOLLOWING = b'    put_optional_parameter(out, experiment.absorption.mu_r, scope);'


def verify(data, receipt):
    if (
        receipt['before_sha256'] != ORIGINAL
        or hashlib.sha256(data).hexdigest() != receipt['after_sha256']
    ):
        raise ValueError('The projected codec retains its independently frozen source identity')
    if RETIRED in data or data.count(FOLLOWING) != 1:
        raise ValueError('Only the single retired optional slot may leave the active-domain codec')
    restored = data.replace(FOLLOWING, RETIRED + FOLLOWING)
    if hashlib.sha256(restored).hexdigest() != ORIGINAL:
        raise ValueError('Every other frozen codec byte must survive the retired-slot projection')


def test_retired_slot_projection_reconstructs_the_complete_original_codec():
    data = (HERE / 'prechange_stamp_codec.inc').read_bytes()
    receipt = json.loads((HERE / 'retired-absorption-codec.json').read_text())
    verify(data, receipt)
    assert b'experiment.absorption.abscor1' in data and FOLLOWING in data, (
        'Both active absorption fields remain in the independent stamp-byte reference'
    )


@pytest.mark.parametrize('escape', ['active-field', 'source-hash', 'reintroduced-slot'])
def test_frozen_codec_projection_refuses_unrelated_source_or_field_changes(escape):
    data = (HERE / 'prechange_stamp_codec.inc').read_bytes()
    receipt = copy.deepcopy(json.loads((HERE / 'retired-absorption-codec.json').read_text()))
    if escape == 'source-hash':
        receipt['before_sha256'] = '0' * 64
    elif escape == 'active-field':
        data = data.replace(b'experiment.absorption.abscor1', b'experiment.absorption.mu_r')
        receipt['after_sha256'] = hashlib.sha256(data).hexdigest()
    else:
        data = data.replace(FOLLOWING, RETIRED + FOLLOWING)
        receipt['after_sha256'] = hashlib.sha256(data).hexdigest()
    with pytest.raises(ValueError, match=r'source identity|single retired|Every other'):
        verify(data, receipt)
