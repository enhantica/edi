"""Original actual-model metadata, complete capacity and prospective recovery.

No engine computation or scientific fitted-result expectation is generated here.
A finite control supplies unchanged context wrappers solely for complete-byte
composition, while original exclusion rows and all validity facts are independent.
"""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
_spec = importlib.util.spec_from_file_location(
    'metadata_budget', ROOT / 'tests/system/py/test_e11_t5_skill_resource_bounds.py'
)
budget = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(budget)
loader = budget.loader


def original_resources(*, large=False):
    entries, resources = budget.fixture([
        'L' * 950000 if large else 'Original project guidance',
        'Original smaller intake',
    ])
    for row, resource, identity in zip(
        entries, resources, ['project-assistance', 'fullprof-intake'], strict=True
    ):
        row['id'] = resource['id'] = identity
        row['path'] = identity + '/SKILL.md'
    return entries, resources


def model(loader, fault='none', exclusions=0, *, recovery=False, mutate=None):
    entries, resources = original_resources(large=recovery)
    index = {'schema': 'edi.assistant.skills/1', 'skills': entries}
    if mutate:
        index = mutate(index)
    observed = loader.command(
        'model_recovery' if recovery else 'model_context',
        fault=fault,
        exclusions=exclusions,
        index_json=budget.encoded(index).decode() if not isinstance(index, str) else index,
        resources=resources,
    )
    assert observed['observation'] == 'model_returned', (
        'S1/SK3/SK4: real model/Controller observation returns without an escaping host failure'
    )
    assert observed['before'] == observed['after'], (
        'S1/SK3/SK4: disclosure/refusal/recovery never mutates the original scientific model'
    )
    return observed


def dataset(context):
    return next(row for row in context['datasets'] if row['id'] == 'dataset-A')


def explicit_invalid(context, control):
    if context.get('error'):
        return True
    row = dataset(context)
    if row.get('data_status') == 'invalid':
        return True
    original_diagnostics = budget.encoded(control.get('diagnostics', []))
    return budget.encoded(context.get('diagnostics', [])) != original_diagnostics


def test_real_nested_exclusions_charge_each_complete_serialized_row_once(loader):
    control = model(loader)['context']
    assert 'error' not in control, 'S1: valid small real-model control admits context first'
    expected = copy.deepcopy(control)
    count = 12000
    rows = [{'id': 'region-' + str(i), 'first': 1.25, 'second': 2.75} for i in range(count)]
    dataset(expected)['excluded_regions'] = rows
    extent = len(budget.encoded(expected))
    assert budget.LIMIT // 2 < extent < budget.LIMIT, (
        'S1: independently composed complete context fits the existing cap despite '
        'nested-row double charge'
    )
    actual = model(loader, exclusions=count)['context']
    assert actual == expected, (
        'S1: legal nested exclusions preserve original identities/endpoints and '
        'complete context at true capacity'
    )


@pytest.mark.parametrize(
    'fault', ['weight', 'origin', 'x-min', 'x-max', 'exclusion-first', 'exclusion-second']
)
def test_nonfinite_present_metadata_is_explicitly_invalid_not_absent(loader, fault):
    control = model(loader)['context']
    assert not control.get('error') and dataset(control)['data_status'] == 'present', (
        'SK3: original finite measured dataset is a valid independent control'
    )
    actual = model(loader, fault)['context']
    assert explicit_invalid(actual, control), (
        'SK3: nonfinite present weight/exclusion/background must be refused or '
        'explicitly diagnosed, never relabelled absent'
    )


@pytest.mark.parametrize(
    'fault',
    ['axis-mode', 'calc-sigma-length', 'calc-sigma-nonfinite', 'calc-observation-nonfinite'],
)
def test_axis_mode_and_calculation_only_cannot_hide_invalid_observed_columns(loader, fault):
    control = model(loader)['context']
    actual = model(loader, fault)['context']
    assert explicit_invalid(actual, control), (
        'SK3: actual beam/axis agreement and genuine empty-observation grid '
        'semantics constrain present status'
    )


def test_genuine_calculation_only_empty_observations_and_optional_absence_remain_valid(loader):
    observed = model(loader, 'calculation-grid')['context']
    assert 'error' not in observed, 'SK3: true empty-observation calculation grid remains legal'
    row = dataset(observed)
    assert row['data_status'] == 'present' and row['calculation_only'], (
        'SK3: valid real calculation-only grid remains truthfully present without '
        'fit-readiness inference'
    )
    assert row['observations']['intensity_count'] == row['observations']['sigma_count'] == 0, (
        'SK3: original empty observation vectors remain empty'
    )
    assert all(row['background'][key] is None for key in ['origin', 'x_min', 'x_max']), (
        'SK3: genuinely absent optional metadata remains distinct from invalid present numbers'
    )


def test_new_metadata_identity_obeys_existing_identity_capacity(loader):
    observed = model(loader, 'long-id')['context']
    assert observed.get('error'), (
        'S1: metadata identity above existing id_bytes refuses before publishing '
        'oversized identity'
    )


def test_prospective_smaller_skill_recovers_without_validating_old_oversized_selection(loader):
    observed = model(loader, exclusions=4000, recovery=True)
    recovery = observed['recovery']
    assert recovery['small_selection']['ok'] and recovery['attached']['ok'], (
        'SK4: actual ordinary small selection and real project attachment establish '
        'recovery control'
    )
    assert 'error' not in recovery['small_context'] and recovery['large_selection']['ok'], (
        'SK4: same real project fits small guidance and large guidance is '
        'independently valid projectless'
    )
    assert recovery['large_context'].get('error'), (
        'SK4: actual old selection plus attached project reaches complete-context refusal'
    )
    assert recovery['catalog']['ok'], (
        'SK4: bounded catalog remains independently available during project-context refusal'
    )
    assert recovery['recovered']['ok'] and observed['context'] == recovery['small_context'], (
        'SK4: prospective smaller selection restores identical valid real context atomically'
    )


@pytest.mark.parametrize('fault', ['unknown-long', 'unknown-control', 'duplicate'])
def test_controller_resource_error_is_typed_bounded_and_never_echoes_untrusted_keys(loader, fault):
    marker = 'PRIVATE_RESOURCE_KEY_' + (
        'secret\\"\n\t' * 120 if fault == 'unknown-control' else 'z' * 800
    )

    def mutate(index):
        if fault == 'duplicate':
            text = budget.encoded(index).decode()
            return text[:-1] + ',' + json.dumps(marker) + ':0,' + json.dumps(marker) + ':1}'
        index[marker] = 'PRIVATE_RESOURCE_VALUE_DO_NOT_ECHO'
        return index

    context = model(loader, mutate=mutate)['context']
    assert context.get('error') and context['error']['code'] == 'edi.assistant.invalid_argument', (
        'SK5: malformed trusted-resource shape preserves actual typed '
        'invalid-argument classification'
    )
    message = context['error']['message']
    assert (
        len(message.encode()) <= 512
        and marker not in message
        and 'PRIVATE_RESOURCE' not in message
    ), (
        'SK5: public context refusal remains bounded app-owned text without rejected '
        'key/value leakage'
    )
