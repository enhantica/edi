"""Closed-form preservation controls for source-only oracle adaptations."""

import copy
import hashlib

import pytest

from tests.fixtures.e04_t1 import adapt_descriptive_inputs as adapter


def authored_inputs():
    project = 'input/project'
    name = project + '/experiments/bank.edi'
    before = b'_peak.broad_gauss_u 2.75\n_experiment_type.beam_mode "constant wavelength"\n'
    after = before + b'_experiment_type.radiation_probe "neutron"\n'
    digest = hashlib.sha256(before).hexdigest()
    oracle = {
        'profiles': ['declared-family'],
        'examples': [{'free': 17}],
        'corpus': [
            {
                'project': project,
                'experiment': 'bank',
                'sha256': digest,
                'scalars': {
                    '_peak.broad_gauss_u': {'value': 2.75, 'free': True, 'uncertainty': 0.125},
                    '_experiment_type.beam_mode': 'constant wavelength',
                },
                'range': [12.5, 31.25, 0.75, 26],
            }
        ],
        'projects': [
            {
                'id': 'registered',
                'path': project,
                'files': {'experiments/bank.edi': digest},
                'datasets': [{'file': 'first.dat'}, {'file': 'second.dat'}],
                'loaderWarning': 'retained warning',
            }
        ],
    }
    display = {'sources': {name: digest}, 'cases': [{'tag': 'retained', 'fields': [2.75]}]}
    return oracle, display, {name: (before, after)}


def test_descriptive_adaptation_retains_every_scientific_display_and_inventory_witness():
    oracle, display, inputs = authored_inputs()
    original = copy.deepcopy((oracle, display))
    new, shown = adapter.adapt(oracle, display, inputs)
    assert (oracle, display) == original, (
        'Source adaptation must leave the independently frozen old witnesses intact'
    )
    expected = copy.deepcopy(oracle)
    digest = hashlib.sha256(next(iter(inputs.values()))[1]).hexdigest()
    expected['corpus'][0]['sha256'] = digest
    expected['corpus'][0]['scalars']['_experiment_type.radiation_probe'] = 'neutron'
    expected['projects'][0]['files']['experiments/bank.edi'] = digest
    assert new == expected, (
        'Descriptive adaptation changes only declared scalar values and their exact source hashes'
    )
    assert shown == {
        'sources': {'input/project/experiments/bank.edi': digest},
        'cases': [{'tag': 'retained', 'fields': [2.75]}],
    }, 'Every frozen rendered value, identity and case order must remain exact'
    assert adapter.adapt(new, shown, inputs) == (new, shown), (
        'Regenerating the same independently archived descriptors must be byte-stable'
    )


@pytest.mark.parametrize(
    'damage', ['science', 'old-hash', 'old-value', 'old-extra', 'duplicate', 'unexpected-field']
)
def test_descriptive_adaptation_refuses_nonpresentation_and_wrong_old_witnesses(damage):
    oracle, display, inputs = authored_inputs()
    name = next(iter(inputs))
    before, after = inputs[name]
    adapter.adapt(oracle, display, inputs)
    if damage == 'science':
        inputs[name] = before, after.replace(b'2.75', b'2.76')
    elif damage == 'old-hash':
        oracle['corpus'][0]['sha256'] = '0' * 64
    elif damage == 'old-value':
        oracle['corpus'][0]['scalars']['_experiment_type.beam_mode'] = 'time-of-flight'
    elif damage == 'old-extra':
        oracle['corpus'][0]['scalars']['_experiment_type.sample_form'] = 'powder'
    elif damage == 'duplicate':
        inputs[name] = before, after + b'_experiment_type.radiation_probe "neutron"\n'
    else:
        inputs[name] = before, after + b'_metadata.unknown "new"\n'
    with pytest.raises(AssertionError):
        adapter.adapt(oracle, display, inputs)
