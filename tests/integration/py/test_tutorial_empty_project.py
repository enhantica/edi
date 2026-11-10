"""Named construction and notebook displays must work without phantom model objects."""

import importlib
import importlib.util
from pathlib import Path

import pytest


def api():
    name = 'easydiffraction' if importlib.util.find_spec('easydiffraction') else 'edi'
    return importlib.import_module(name)


def test_public_import_resolves_this_checkout():
    spec = importlib.util.find_spec('easydiffraction')
    assert spec is not None, 'A tutorial must import easydiffraction as edi'
    root = Path(__file__).resolve().parents[3]
    assert Path(spec.origin).resolve().is_relative_to(root), (
        'The tutorial import must exercise this checkout, never diffraction-lib from PyPI'
    )


def test_named_project_starts_empty_and_reading_collections_does_not_create_objects():
    project = api().Project(name='tutorial')
    assert len(project.structures) == 0, (
        'A new named project must have no implicit blank structure'
    )
    assert len(project.experiments) == 0, (
        'A new named project must have no implicit blank experiment'
    )
    assert not list(project.free_parameters), 'An empty project has no fittable model parameters'
    assert len(project.structures) == len(project.experiments) == 0, (
        'Inspecting an empty project must not populate it'
    )


def test_explicit_experiment_starts_without_a_blank_structure_link(tmp_path):
    path = tmp_path / 'measured.dat'
    path.write_text('10 5 1\n11 7 1\n12 6 1\n')
    project = api().Project(name='tutorial')
    project.experiments.add_from_data_path(
        name='bank',
        data_path=path,
        sample_form='powder',
        beam_mode='constant wavelength',
        radiation_probe='neutron',
    )
    bank = project.experiments['bank']
    assert len(bank.linked_structures) == 0, (
        'An explicitly created experiment must not link a phantom structure'
    )


@pytest.mark.parametrize(
    'route',
    [
        'pattern',
        'structure',
        'fit.results',
        'fit.correlations',
        'fit.series',
        'parameters.free',
        'parameters.fittable',
        'parameters.all',
    ],
)
def test_step_display_namespace_has_the_workflow_operations(route):
    project = api().Project(name='tutorial')
    assert hasattr(project, 'display'), (
        'A project must expose notebook charts and tables through display'
    )
    operation = project.display
    for name in route.split('.'):
        assert hasattr(operation, name), f'The tutorial display operation {route} must exist'
        operation = getattr(operation, name)
    assert callable(operation), f'The tutorial display operation {route} must be callable'
