"""Sparse reordered powers distinguish order-derived ids from positional numbering."""

import edi as engine
import pytest

from tests.fixtures.background_estimate.term_ids import (
    COEFFICIENTS,
    FREE,
    IDS,
    ORDERS,
    materialize,
    saved_rows,
)


def snapshot(project):
    rows = project.experiment.background_terms
    assert all(hasattr(row, 'id') for row in rows), (
        'Every public polynomial and Chebyshev term must expose its editable row id'
    )
    return [(str(row.id), row.order, row.coef.value, row.coef.free) for row in rows]


@pytest.mark.parametrize('kind', ['polynomial', 'chebyshev'])
def test_explicit_term_ids_and_sparse_row_layout_roundtrip_exactly(tmp_path, kind):
    source = materialize(tmp_path / 'input', kind, explicit=True)
    project = engine.Project.load(source)
    expected_ids = IDS
    expected = list(zip(expected_ids, ORDERS, COEFFICIENTS, FREE, strict=True))
    assert snapshot(project) == expected, (
        'Explicit ids, sparse powers, coefficients, free flags and row layout must survive load'
    )
    for index in range(2):
        destination = tmp_path / ('saved-' + str(index))
        project.save_as(destination)
        rows = saved_rows(destination)
        assert [row.get('_background.id') for row in rows] == expected_ids, (
            'Every saved series row must carry its explicit id'
        )
        project = engine.Project.load(destination)
        assert snapshot(project) == expected, (
            'Repeated saves must preserve ids, powers, values, free flags and row order'
        )


@pytest.mark.parametrize('kind', ['polynomial', 'chebyshev'])
def test_public_term_id_edit_saves_without_changing_order_or_coefficient(tmp_path, kind):
    source = materialize(tmp_path / 'input', kind)
    project = engine.Project.load(source)
    expected = snapshot(project)
    project.experiment.background_terms[0].id = 'renamed-high'
    destination = tmp_path / 'saved'
    project.save_as(destination)
    expected[0] = ('renamed-high', *expected[0][1:])
    assert snapshot(engine.Project.load(destination)) == expected, (
        'A public term id edit must survive save/load without changing the term power or value'
    )


@pytest.mark.parametrize('kind', ['polynomial', 'chebyshev'])
def test_missing_term_id_column_is_refused_with_a_clear_name(tmp_path, kind):
    source = materialize(tmp_path / 'input', kind, explicit=False)
    with pytest.raises(ValueError, match=r'(?i)id|background') as refused:
        engine.Project.load(source)
    message = str(refused.value).lower()
    assert 'background' in message, 'A missing term id refusal must name its background category'
    assert 'id' in message, 'A missing term id refusal must name the id field'
    assert any(word in message for word in ['missing', 'required', 'must', 'need']), (
        'The missing-id refusal must state that ids are required, with no loader fallback'
    )


@pytest.mark.parametrize('kind', ['polynomial', 'chebyshev'])
def test_fullprof_input_factory_emits_required_ids_without_changing_coefficients(tmp_path, kind):
    import numpy as np  # noqa: PLC0415

    from tests.fixtures.c13_t6_background.project import materialize as make  # noqa: PLC0415

    row = {
        'project': 'pd-neut-cwl-control',
        'type': kind,
        'origin': 47.125,
        'x_min': 17,
        'x_max': 86,
        'coefficients': [8.125, 17.25, -2.75],
    }
    source = make(tmp_path, row, np.array([20.0, 40.0, 80.0]), np.array([1.0, 2.0, 3.0]))
    text = (source / 'experiments/experiment.edi').read_text()
    assert '_background.id\n_background.order\n_background.coef\n' in text, (
        'The independent-input factory must explicitly declare every required term id'
    )
    assert '1 0 8.125\n2 1 17.25\n3 2 -2.75\n' in text, (
        'Declaring required ids must preserve all powers, coefficients and former row identities'
    )
