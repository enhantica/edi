"""S1 complete helper budgets through real loader/private generated-resource binding.

Original trusted manifest/content inputs are independently UTF-8 encoded here; no
loader-generated value supplies an expected bound. These returned-value gates do
not claim dynamic proof of pre-copy allocation ordering or canonical packaging.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
_spec = importlib.util.spec_from_file_location(
    'skill_budget_protocol', ROOT / 'tests/integration/py/test_e11_t5_assistant_protocol.py'
)
protocol = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(protocol)
LIMIT = 1048576  # Accepted ADR0037 Limits::context_bytes, not a measured runtime capacity.


def encoded(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode()


def fixture(contents):
    entries, resources = [], []
    for index, content in enumerate(contents):
        identity = 'budget-' + str(index)
        digest = hashlib.sha256(content.encode()).hexdigest()
        entries.append({
            'id': identity,
            'version': '1.0.0',
            'title': 'Original trusted budget fixture',
            'summary': 'Non-scientific test content',
            'path': identity + '/SKILL.md',
            'sha256': digest,
            'requires': [],
            'capabilities': ['inspect_project'],
            'references': [],
        })
        resources.append({'id': identity, 'sha256': digest, 'content': content})
    return entries, resources


def selected_value(content):
    entries, _ = fixture([content])
    return [{**{key: entries[0][key] for key in ['id', 'version', 'sha256']}, 'content': content}]


def catalog_value(contents):
    entries, _ = fixture(contents)
    return {
        'selected_id': entries[0]['id'],
        'skills': [
            {**entry, 'content': content, 'available': True, 'blocked_reason': ''}
            for entry, content in zip(entries, contents, strict=True)
        ],
    }


def fill(size, alphabet):
    pieces = {'ascii': 'x', 'escaped': '"\\\n', 'utf8': 'Å🧪'}
    token = pieces[alphabet]
    width = len(encoded(token)) - 2
    repeat, tail = divmod(size, width)
    value = token * repeat + 'x' * tail
    assert len(encoded(value)) - 2 == size, (
        'S1: fixture encoded content extent is independently exact'
    )
    return value


@pytest.fixture
def loader():
    binary = Path(os.environ['EDI_ASSISTANT_SKILL_BUDGET_PROBE'])
    assert binary.is_file(), 'S1 SETUP: actual linked loader component must exist before behavior'
    actor = protocol.Host(binary, reply_timeout=5)
    try:
        yield actor
    finally:
        actor.close()


def observe(loader, contents, operation, *, patch=None):
    entries, resources = fixture(contents)
    if patch is not None:
        patch(entries, resources)
    return loader.command(
        operation,
        index_json=encoded({
            'schema': 'edi.assistant.skills/1',
            'skills': entries,
        }).decode(),
        resources=resources,
        selected='budget-0',
        has_selected_files=True,
        tools=[{'name': 'inspect_project'}],
    )


@pytest.mark.parametrize('alphabet', ['ascii', 'escaped', 'utf8'])
@pytest.mark.parametrize('delta', [-1, 0, 1], ids=['below', 'exact', 'over-one'])
def test_selected_skill_complete_array_budget_includes_framing_and_encoding(
    loader, alphabet, delta
):
    baseline = len(encoded(selected_value('')))
    content = fill(LIMIT + delta - baseline, alphabet)
    expected = selected_value(content)
    assert len(encoded(expected)) == LIMIT + delta, (
        'S1: independent complete array extent reaches boundary'
    )
    observed = observe(loader, [content], 'context')
    if delta > 0:
        assert (
            observed['observation'] == 'threw_refusal' and observed['code'] == 'resource_exhausted'
        ), (
            'S1: complete selected-skill array over capacity refuses, including framing bytes'
        )
    else:
        assert observed['observation'] == 'returned' and observed['result'] == expected, (
            'S1: exact/below-capacity selected arrays preserve all actual original UTF-8 content'
        )
        assert observed['encoded_bytes'] == LIMIT + delta, (
            'S1: actual helper serialization matches independent complete-value accounting'
        )


@pytest.mark.parametrize('delta', [-1, 0, 1], ids=['below', 'exact', 'over-one'])
def test_complete_multi_resource_catalog_preserves_capacity_and_outer_wrapper(loader, delta):
    base = len(encoded(catalog_value(['', ''])))
    remaining = LIMIT + delta - base
    contents = ['a' * (remaining // 2), 'b' * (remaining - remaining // 2)]
    expected = catalog_value(contents)
    assert len(encoded(expected)) == LIMIT + delta, (
        'S1: full catalog metadata/array/result extent is exact'
    )
    observed = observe(loader, contents, 'catalog')
    if delta > 0:
        assert (
            observed['observation'] == 'threw_refusal' and observed['code'] == 'resource_exhausted'
        ), 'S1: outer complete catalog over capacity refuses without dropping a resource'
    else:
        assert observed['observation'] == 'returned' and observed['result'] == expected, (
            'S1: ordinary multiple full resources remain legal through exact complete capacity'
        )
        assert observed['encoded_bytes'] == LIMIT + delta, (
            'S1: outer catalog wrappers consume actual bytes'
        )


@pytest.mark.parametrize('fault', ['missing-content', 'hash-mismatch', 'raw-over-capacity'])
def test_invalid_generated_resource_bond_refuses_before_successful_selection(loader, fault):
    def mutate(_entries, resources):
        if fault == 'missing-content':
            resources[0]['content'] = ''
        elif fault == 'hash-mismatch':
            resources[0]['sha256'] = '0' * 64
        else:
            resources[0]['content'] = 'x' * (LIMIT + 1)

    observed = observe(loader, ['original trusted text'], 'context', patch=mutate)
    assert observed['observation'] == 'threw_refusal', (
        'S1: missing/unbonded/oversized generated content cannot produce a selected payload'
    )
    expected = 'resource_exhausted' if fault == 'raw-over-capacity' else 'invalid_argument'
    assert observed['code'] == expected, (
        'S1: actual typed refusal distinguishes identity from capacity'
    )


def test_ordinary_three_resource_catalog_retains_all_distinct_originals(loader):
    contents = ['First original Å', 'Second original 🧪', 'Third original "quoted" text']
    observed = observe(loader, contents, 'catalog')
    assert observed['observation'] == 'returned' and observed['result'] == catalog_value(
        contents
    ), (
        'S1: ordinary multi-resource inputs retain complete metadata/content without a lower cap'
    )


def test_bootstrap149_unknown_capability_remains_typed_refusal_with_valid_originals(loader):
    # Existing generated-resource input seam; the unknown name has no handler or grant.
    contents = ['Original bounded shipped-style guidance Å']
    for operation in ['context', 'catalog']:
        positive = observe(loader, contents, operation)
        assert positive['observation'] == 'returned', (
            'BOOTSTRAP: ordinary supported capability remains legal through the actual loader'
        )

        def unknown(entries, _resources):
            entries[0]['capabilities'].append('original_unregistered_capability')

        negative = observe(loader, contents, operation, patch=unknown)
        assert negative == {'observation': 'threw_refusal', 'code': 'invalid_argument'}, (
            'BOOTSTRAP: unknown bundled capabilities fail closed with identity refusal, '
            'not fabricated handlers, capacity errors, or a partial selected payload'
        )
