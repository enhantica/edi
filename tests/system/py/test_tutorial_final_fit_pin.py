"""Gate 3: each executed staged notebook ends at its labelled regression pin."""

import pytest

from tests.fixtures.tutorial_cases.contract import interfaces_for
from tests.fixtures.tutorial_cases.notebook_fit import execute, local_collection
from tests.fixtures.tutorial_cases.pins import compare_regression_pin, machine_values, pinned_start
from tests.integration.py.test_tutorial_fit_stages import FITTING


@pytest.fixture(scope='module')
def collection_factory(tmp_path_factory):
    cached = []

    def get():
        if not cached:
            cached.append(local_collection(tmp_path_factory.mktemp('tutorial-collection')))
        return cached[0]

    return get


@pytest.mark.parametrize('case', [case for case in FITTING if 'python' in interfaces_for(case)])
def test_last_real_notebook_fit_equals_its_committed_regression_pin(
    case, tmp_path, collection_factory
):
    quantities = pinned_start(case)
    observations = execute(case, tmp_path / 'kernel', collection_factory())
    compare_regression_pin(machine_values(observations[-1]['machine']), quantities)
