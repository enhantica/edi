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
TRANSITIONS = {
    (row['kind'], row['path']): row['changes']
    for row in json.loads(
        gzip.decompress((BASE / 'rounded-save-transitions.json.gz').read_bytes())
    )['rows']
}


@pytest.mark.parametrize('row', PINS['rows'], ids=lambda row: row['kind'] + ':' + row['path'])
def test_main_reader_model_regression_pin_changes_only_published_parameter_state(tmp_path, row):
    api = importlib.import_module(case.API)
    factory = api.StructureFactory if row['kind'] == 'structure' else api.ExperimentFactory
    obj = factory.from_cif_path(reference.source_path(row['path']))
    project = case.attach(api, row['kind'], obj)
    project.save_as(tmp_path / 'saved')
    folder = tmp_path / 'saved' / ('structures' if row['kind'] == 'structure' else 'experiments')
    files = list(folder.glob('*.edi'))
    assert len(files) == 1, 'The regression observer reads exactly its one imported entity'
    actual = reference.normalized(files[0].read_text())
    expected = row['values']
    # Labelled regression pins: ADR-0092 rounds saved values and recalculates
    # current results; ADR-0106 fixes published parameters and infers absent letters.
    expected = dict(expected)
    for name, transition in TRANSITIONS.get((row['kind'], row['path']), {}).items():
        assert expected.get(name) == transition['before'], (
            'Every saved-field transition names its frozen pre-rounding value: ' + name
        )
        if transition['after'] is None:
            expected.pop(name)
        else:
            expected[name] = transition['after']
    published = Path(row['path']).suffix.lower() == '.cif'
    assert set(actual) == set(expected), (
        'The regression pin retains exactly the declared saved model fields'
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
                'values outside the declared rounded-save and published-state '
                'transitions: '
            ) + name


def test_reader_regression_pin_population_is_not_empty():
    control = '#\\#CIF_2.0\ndata_control\nloop_\n_x\n_y\n1 [1.0 2.0]\n2 [. .]\n'
    assert reference.saved_columns(control) == {
        '_x': ['1', '2'],
        '_y': ['[1.0 2.0]', '[. .]'],
    }, 'The saved-model observer keeps each CIF2 list in exactly one loop cell'
    quoted = control + "_note 'literal [brackets]'\n# ignored [brackets]\n"
    assert reference.saved_columns(quoted)['_note'] == ["'literal [brackets]'"], (
        'List observation leaves quoted scalar brackets and comments intact'
    )
    for broken in (control.replace('2 [. .]', '2'), control.replace('[. .]', '[. .')):
        with pytest.raises(ValueError, match=r'Wrong number|Unterminated'):
            reference.saved_columns(broken)
    assert PINS['rows'], 'The frozen reader baseline must contain real tracked entity documents'
    assert any(Path(row['path']).suffix.lower() == '.cif' for row in PINS['rows']), (
        'The baseline includes successfully read published CIF structures'
    )
