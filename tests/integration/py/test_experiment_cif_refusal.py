"""Existing experiment CIF factories stay live; native-only discovery stays unchanged."""

import importlib
import warnings

import gemmi
import pytest

from tests.fixtures import cif_accounting as account
from tests.fixtures import experiment_cif_refusal as case
from tests.fixtures import structure_cif_refusal as native
from tests.integration.py import experiment_cif_refusal_checks as checks


@pytest.fixture
def api():
    return importlib.import_module(account.API)


def add_experiment(project, api, method, argument):
    if account.API == 'edi':
        return getattr(project.experiments, method)(argument)
    return project.experiments.add(
        getattr(api.ExperimentFactory, method.removeprefix('add_'))(argument)
    )


@pytest.mark.parametrize('style', case.FACTORY_STYLES)
@pytest.mark.parametrize('route', ['text', 'path-cif', 'path-edi', 'path-upper'])
def test_experiment_factories_preserve_main_cif_admission(tmp_path, api, style, route):
    text = case.text(style)
    assert len(gemmi.cif.read_string(text)) >= 1, (
        'Each experiment refusal witness is independently parseable CIF'
    )
    suffix = {'text': '.cif', 'path-cif': '.cif', 'path-edi': '.edi', 'path-upper': '.CIF'}[route]
    path = tmp_path / ('input' + suffix)
    path.write_text(text)
    before = native.snapshot(tmp_path)
    factory = (
        api.ExperimentFactory.from_cif_str
        if route == 'text'
        else api.ExperimentFactory.from_cif_path
    )
    argument = text if route == 'text' else path
    if style == 'main-classic':
        checks.main_values(factory(argument))
    else:
        with pytest.raises((ValueError, RuntimeError)) as caught:
            factory(argument)
        checks.reason(str(caught.value))
    assert native.snapshot(tmp_path) == before, (
        'An experiment factory refusal leaves all input and output bytes intact'
    )


@pytest.mark.parametrize('style', case.FACTORY_STYLES)
@pytest.mark.parametrize('method', ['add_from_cif_str', 'add_from_cif_path', 'add_from_edi_path'])
def test_experiment_collection_preserves_main_cif_admission_and_model(
    tmp_path, capfd, api, style, method
):
    project = api.Project.load(native.project(tmp_path))
    project.save_as(tmp_path / 'before')
    before = native.saved_model(tmp_path / 'before')
    count = len(project.experiments)
    path = tmp_path / 'input.edi'
    path.write_text(case.text(style))
    if style == 'main-classic':
        argument = case.text(style) if method.endswith('str') else path
        add_experiment(project, api, method, argument)
        checks.main_values(project.experiments['main_cwl'])
        project.save_as(tmp_path / 'after')
        after = native.saved_model(tmp_path / 'after')
        del after['experiments/main_cwl.edi']
        assert after == before, (
            'An accepted experiment CIF leaves every pre-existing native model byte intact'
        )
        assert len(project.experiments) == count + 1, (
            'The supported collection entrance adds one accepted experiment as on main'
        )
        assert path.read_text() == case.text(style), 'An accepted CIF never rewrites its input'
        return
    capfd.readouterr()
    with warnings.catch_warnings(record=True) as notices:
        warnings.simplefilter('always')
        argument = case.text(style) if method.endswith('str') else path
        with pytest.raises((ValueError, RuntimeError)) as caught:
            add_experiment(project, api, method, argument)
    checks.reason(str(caught.value))
    checks.no_warnings(notices, capfd.readouterr().err)
    assert len(project.experiments) == count, (
        'A refused collection addition retains every existing experiment'
    )
    project.save_as(tmp_path / 'after')
    assert native.saved_model(tmp_path / 'after') == before, (
        'Every native structure, experiment and analysis byte survives experiment refusal'
    )
    assert path.read_text() == case.text(style), 'Refusing an experiment never rewrites its CIF'


@pytest.mark.parametrize('style', case.STYLES)
@pytest.mark.parametrize('layout', case.LAYOUTS)
def test_project_experiment_cif_discovery_preserves_main_selection_and_refusal(
    tmp_path, api, style, layout
):
    source = case.poisoned_project(tmp_path, style, layout)
    before = native.snapshot(source)
    if layout == 'native-suffix':
        with pytest.raises((ValueError, RuntimeError)) as caught:
            api.Project.load(source)
        checks.reason(str(caught.value))
    else:
        control = tmp_path / 'control'
        control.mkdir()
        api.Project.load(native.project(control)).save_as(tmp_path / 'before')
        project = api.Project.load(source)
        project.save_as(tmp_path / 'after')
        after = native.saved_model(tmp_path / 'after')
        assert {
            path: data for path, data in after.items() if path.endswith('.edi')
        } == native.saved_model(tmp_path / 'before'), (
            'Main discovers native .edi files only, ignoring same-stem and uppercase CIF sidecars'
        )
        assert len(project.experiments) == 1, 'Main does not import a sidecar as a new experiment'
        assert {path: data for path, data in after.items() if not path.endswith('.edi')} == {
            path: data
            for path, data in before.items()
            if path.startswith('experiments/') and not path.endswith('.edi')
        }, 'Main retains ignored experiment CIF sidecars byte-for-byte as saved project assets'
    assert native.snapshot(source) == before, (
        'Main-compatible experiment discovery preserves every native and CIF input byte'
    )


def test_native_experiment_control_still_loads_and_saves(tmp_path, api):
    project = api.Project.load(native.project(tmp_path))
    assert len(project.experiments) == 1, 'Native experiment loading remains a live valid control'
    project.save_as(tmp_path / 'saved')
    values = account.cells((tmp_path / 'saved/experiments/bank.edi').read_text())
    assert values[account.key('_instrument.setup_wavelength')] == ['1.54'], (
        'The native experiment preserves its independently authored wavelength through save'
    )
