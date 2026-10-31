"""Main-reader regression pins retain the models the published files already gave."""

import gzip
import importlib
import json
import math
import re
from pathlib import Path

import pytest

from tests.fixtures import cif_import_cases as case
from tests.fixtures.cif_import_baseline import generate_readers as reference

BASE = Path(__file__).resolve().parents[2] / 'fixtures/cif_import_baseline'
PINS = json.loads(gzip.decompress((BASE / 'readers-before.json.gz').read_bytes()))


@pytest.mark.parametrize('row', PINS['rows'], ids=lambda row: row['kind'] + ':' + row['path'])
def test_main_reader_model_regression_pin_changes_only_published_parameter_state(tmp_path, row):
    api = importlib.import_module(case.API)
    factory = api.StructureFactory if row['kind'] == 'structure' else api.ExperimentFactory
    obj = factory.from_cif_path(case.ROOT / row['path'])
    project = case.attach(api, row['kind'], obj)
    project.save_as(tmp_path / 'saved')
    folder = tmp_path / 'saved' / ('structures' if row['kind'] == 'structure' else 'experiments')
    files = list(folder.glob('*.edi'))
    assert len(files) == 1, 'The regression observer reads exactly its one imported entity'
    actual = reference.normalized(files[0].read_text())
    expected = row['values']
    published = Path(row['path']).suffix.lower() == '.cif'
    assert set(actual) == set(expected), (
        'The reader regression pin retains every pre-existing saved model field'
    )
    for name, values in expected.items():
        found = actual[name]
        assert len(found) == len(values), (
            'The reader regression pin retains every row of every model column'
        )
        for before, after in zip(values, found, strict=True):
            if published:
                original = re.sub(r'\([^)]*\)', '', before)
                current = re.sub(r'\([^)]*\)', '', after)
            else:
                original, current = before, after
            try:
                equal = math.isclose(float(current), float(original), rel_tol=1e-12, abs_tol=1e-12)
            except ValueError:
                equal = current == original
            assert equal, (
                'The main-reader regression pin preserves scientific model '
                'values; only published free flags and uncertainties may '
                'change: '
            ) + name


def test_reader_regression_pin_population_is_not_empty():
    assert PINS['rows'], 'The frozen reader baseline must contain real tracked entity documents'
    assert any(Path(row['path']).suffix.lower() == '.cif' for row in PINS['rows']), (
        'The baseline includes successfully read published CIF structures'
    )
