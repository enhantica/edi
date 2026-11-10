"""F6: admit a whole background declaration before decoding it."""

import runpy

import edi as engine
import numpy as np
import pytest
from test_c13_t6_background import FIXTURE, MATERIALIZE, REFERENCE

WITNESSES = runpy.run_path(str(FIXTURE / 'declarations.py'))
DAMAGES = WITNESSES['DAMAGES']
DAMAGE = WITNESSES['damage_declaration']
MODELS = ('polynomial', 'chebyshev', 'line-segment')


def materialize(tmp_path, model):
    kind = 'line-segment' if model == 'historical-line-segment' else model
    row = {
        **REFERENCE['cases']['lab6'],
        'type': kind,
        'origin': 75.0,
        'x_min': 20.0,
        'x_max': 140.0,
    }
    x = np.linspace(20, 140, 31)
    directory = MATERIALIZE(
        tmp_path, row, x, np.zeros_like(x), kind=kind, coefficients=[10.0, 20.0]
    )
    file = directory / 'experiments/experiment.edi'
    text = file.read_text()
    if model == 'historical-line-segment':
        text = text.replace('_background.type line-segment\n', '')
    return directory, file, text, kind, x


@pytest.mark.parametrize('model', MODELS)
@pytest.mark.parametrize('route', ['project', 'text-factory', 'file-factory'])
@pytest.mark.parametrize('damage', DAMAGES)
def test_whole_background_declaration_refuses_ambiguity(tmp_path, model, route, damage):
    directory, file, text, kind, _ = materialize(tmp_path, model)
    if model == 'historical-line-segment' and damage in {'repeat-type', 'repeat-unknown-type'}:
        # Type-less prior art still needs TWO selectors for this duplicate witness.
        text += '_background.type line-segment\n'
    damaged = DAMAGE(text, kind, damage)
    assert damaged != text, ' F6 each shape witness must change the original declaration'
    file.write_text(damaged)
    routes = {
        'project': (engine.Project.load, directory),
        'text-factory': (engine.ExperimentFactory.from_cif_str, damaged),
        'file-factory': (engine.ExperimentFactory.from_cif_path, file),
    }
    load, argument = routes[route]
    with pytest.raises((ValueError, RuntimeError), match=r'(?i)background'):
        load(argument)


@pytest.mark.parametrize('model', MODELS)
def test_unambiguous_background_load_calculate_and_save_remain_valid(tmp_path, model):
    directory, file, text, kind, x = materialize(tmp_path / 'input', model)
    file.write_text(text)
    # The factory controls prove the malformed witness is not failing because
    # that route rejects every ordinary document, including type-less prior art.
    for experiment in (
        engine.ExperimentFactory.from_cif_str(text),
        engine.ExperimentFactory.from_cif_path(file),
    ):
        assert experiment is not None, ' F6 valid file/text factories must construct a model'
    project = engine.Project.load(directory)
    if kind == 'line-segment':
        expected = 10 + 25 * (x - x[0]) / (x[-1] - x[0])
    elif kind == 'polynomial':
        expected = 10 + 20 * (x / 75 - 1)
    else:
        expected = 10 + 20 * (2 * x - 20 - 140) / (140 - 20)
    for generation in range(3):
        project.analysis.calculate()
        actual = np.asarray(project.experiment.data.intensity_bkg)
        assert np.allclose(actual, expected, rtol=0, atol=1e-10), (
            ' F6 admitted declarations must retain the independent background through saves'
        )
        if generation < 2:
            destination = tmp_path / f'saved-{generation}'
            project.save_as(destination)
            project = engine.Project.load(destination)
