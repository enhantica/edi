"""Whole-codebase magnetic consumer census, including the paired engine source."""

import json
import os
from pathlib import Path

import pytest

from tests.fixtures.magnetic_pnma import token_census, token_inputs

ROOT = Path(__file__).resolve().parents[3]
ENGINE_ROOT = (
    Path(os.environ['CRYSTA_CONSUMER_SRC']) if os.environ.get('CRYSTA_CONSUMER_SRC') else None
)
HOME = 'magnetic_pnma'


@pytest.fixture(scope='module')
def magnetic_reader_graph():
    sources = token_census.source_tree(ROOT, ENGINE_ROOT)
    return sources, token_census.census(sources)


def test_every_magnetic_field_and_consumer_has_qualified_route_witnesses(magnetic_reader_graph):
    sources, graph = magnetic_reader_graph
    nodes, _, roots, reached = graph
    assert roots, 'The census discovers production magnetic readers before judging them'
    # Exact field/function inventory replaces family-level registrations.

    consumer_nodes, _, consumers = token_census.field_consumers(sources, nodes)
    expected_consumers = json.loads(
        (Path(__file__).parents[2] / 'fixtures' / HOME / 'token-consumers.json').read_text()
    )
    normalized = token_census.normalized_consumers(
        consumer_nodes, consumers, expected_consumers['aliases']
    )
    assert normalized == expected_consumers['consumers'], (
        'Every new magnetic field or downstream consumer requires per-field route witnesses: '
        + repr({
            k: v for k, v in normalized.items() if expected_consumers['consumers'].get(k) != v
        })
    )
    exercised = {(route, case.tag) for case in token_inputs.cases() for route in case.routes}
    required_fields = {tag for fields in normalized.values() for tag in fields}
    assert required_fields <= {tag for _, tag in exercised}, (
        'Every discovered field, including additions inside existing readers, has actual input witnesses: '  # noqa: E501 — explicit lexical cases and consumer obligations
        + repr(sorted(required_fields - {tag for _, tag in exercised}))
    )
    for tag, routes in expected_consumers['field_routes'].items():
        assert all((route, tag) in exercised for route in routes), (
            'Every reviewed field has a qualified behaviour witness on each input route: ' + tag
        )
    names = {nodes[key]['name'] for key in reached}
    expected = {'read_magnetic', 'parse_parameter', 'read_number'}
    assert expected <= names, (
        'Generic helpers without magnetic tag literals belong to the census: '
        + repr(sorted(expected - names))
    )


def test_every_magnetic_value_path_reaches_the_decoder_and_strict_number_boundary(
    magnetic_reader_graph,
):
    sources, graph = magnetic_reader_graph
    failures = token_census.violations(sources, graph)
    assert not failures, (
        'ADR-0108 review-20 sites and new instances share strict decoding; only the pinned '
        'pre-task quoted_no_value, unknown_cif, decode_id_view and unquote_cif bodies/calls '
        'are follow-ups (7cadf1c72):\n' + '\n'.join(failures)
    )
