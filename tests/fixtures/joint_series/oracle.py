"""Boundary predicates shared by live observations and defect controls."""

import math
from decimal import Decimal
from pathlib import Path

import gemmi
import numpy as np
import pytest


def outcome(row):
    assert row['fit_result.success'] == 'True', 'A seeded point must complete successfully'
    chi = float(row['fit_result.reduced_chi_square'])
    assert chi > 0, 'A seeded fit must have a positive joint statistic'
    assert math.isfinite(chi), 'A seeded fit must report a finite positive joint statistic'
    assert row['fit_result.termination'] in {'chi_converged', 'step_small'}, (
        'A seeded fit must stop by a successful declared convergence rule'
    )


def numeric_error(actual, expected, *, tolerance=0.03):
    assert actual is not None, 'A determined derived quantity must retain its standard uncertainty'
    assert math.isfinite(float(actual)), 'Derived uncertainty must be finite'
    assert float(actual) == pytest.approx(expected, rel=tolerance, abs=1e-10), (
        'Derived uncertainty must numerically match full independent covariance propagation'
    )


def token_pair(token):
    assert '(' in token, 'A saved uncertain value must contain its error'
    assert token.endswith(')'), 'A saved uncertain value must include its standard uncertainty'
    value, digits = token[:-1].split('(')
    error = Decimal(digits)
    if digits.isdigit():
        error *= Decimal(10) ** Decimal(value).as_tuple().exponent
    return float(value), float(error)


def category(text, tag, expected, sigma):
    block = gemmi.cif.read_string(text).sole_block()
    tokens = list(block.find_values(tag))
    assert tokens, 'Every derived category must persist its value and uncertainty column'
    row = -1
    if tag == '_linked_structure.weight_fraction':
        names = list(block.find_values('_linked_structure.structure_id'))
        assert 'other' in names, 'The tied derived category must identify its phase row'
        row = names.index('other')
    value, error = token_pair(tokens[row])
    assert value == pytest.approx(expected, rel=0.002, abs=0.002), (
        'Saved category values must match the independent expression'
    )
    numeric_error(error, sigma, tolerance=0.055)


def link(text, project_dir, external, patterns):
    block = gemmi.cif.read_string('data_analysis\n' + text).sole_block()
    directory = block.find_value('_sequential_fit.data_dir')
    assert directory is not None, 'A saved linked series must retain its folder reference'
    directory = gemmi.cif.as_string(directory)
    assert (Path(project_dir) / directory).resolve() == Path(external).resolve(), (
        'The saved folder reference must resolve to the actual external measured directory'
    )
    actual = {
        str(row[0]): gemmi.cif.as_string(row[1])
        for row in block.find([
            '_sequential_fit_experiment.experiment_id',
            '_sequential_fit_experiment.file_pattern',
        ])
    }
    assert actual == patterns, 'Every saved pattern must remain associated with its own experiment'
    for pattern in actual.values():
        assert list(Path(external).glob(pattern)), (
            'Every persisted experiment pattern must reach the external data'
        )


def starts(actual, template, successful, *, chained, chunks=None):
    assert len(actual) == len(successful), (
        'Every fitted joint point must publish its actual start vector'
    )
    wanted = [template, *successful[:-1]] if chained else [template] * len(successful)
    if chained and chunks is not None:
        wanted, offset, start = [], 0, template
        for count in chunks:
            wanted.extend([start] * count)
            offset += count
            start = successful[offset - 1]
    for observed, expected in zip(actual, wanted, strict=True):
        np.testing.assert_allclose(
            observed,
            expected,
            rtol=1e-8,
            atol=1e-10,
            err_msg='Start vectors must follow the declared previous-successful or template rule',
        )


def series_cells(row, name, value, sigma):
    assert {name, name + '.uncertainty'} <= row.keys(), (
        'Every derived series value must have its own numerical uncertainty column'
    )
    assert float(row[name]) == pytest.approx(value, rel=1e-6, abs=1e-9), (
        'A derived series value must belong to the current point and category'
    )
    numeric_error(float(row[name + '.uncertainty']), sigma)
