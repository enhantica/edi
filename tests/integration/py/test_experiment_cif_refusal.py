"""CIF experiment factories and project members follow the content contract."""

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
        checks.imported_values(factory(argument))
    assert native.snapshot(tmp_path) == before, (
        'An experiment factory refusal leaves all input and output bytes intact'
    )


@pytest.mark.parametrize('style', case.FACTORY_STYLES)
@pytest.mark.parametrize('method', ['add_from_cif_str', 'add_from_cif_path', 'add_from_edi_path'])
def test_experiment_collection_preserves_main_cif_admission_and_model(
    tmp_path, api, style, method
):
    project = api.Project.load(native.project(tmp_path))
    project.save_as(tmp_path / 'before')
    before = native.saved_model(tmp_path / 'before')
    count = len(project.experiments)
    path = tmp_path / 'input.edi'
    path.write_text(case.text(style))
    argument = case.text(style) if method.endswith('str') else path
    add_experiment(project, api, method, argument)
    name = 'main_cwl' if style == 'main-classic' else 'cif_experiment'
    (checks.main_values if style == 'main-classic' else checks.imported_values)(
        project.experiments[name]
    )
    project.save_as(tmp_path / 'after')
    after = native.saved_model(tmp_path / 'after')
    del after['experiments/' + name + '.edi']
    assert after == before, 'CIF import preserves all pre-existing native model bytes'
    assert len(project.experiments) == count + 1, 'CIF import adds exactly one experiment'
    assert path.read_text() == case.text(style), 'CIF import never rewrites the input'


@pytest.mark.parametrize('style', case.STYLES)
@pytest.mark.parametrize('layout', case.LAYOUTS)
def test_project_experiment_cif_discovery_preserves_main_selection_and_refusal(
    tmp_path, api, style, layout, capfd
):
    control = tmp_path / 'control'
    control.mkdir()
    api.Project.load(native.project(control)).save_as(tmp_path / 'before')
    source = case.poisoned_project(tmp_path, style, layout)
    before = native.snapshot(source)
    capfd.readouterr()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        project = api.Project.load(source)
    notes = [str(w.message) for w in caught] + capfd.readouterr().err.splitlines()
    if layout == 'shadow':
        assert len(project.experiments) == 1, (
            'I12 reads the native member once when CIF is shadowed'
        )
        assert any('bank.cif' in n and 'not read' in n for n in notes), (
            'I12 names the shadowed experiment CIF in the load report'
        )
    else:
        assert len(project.experiments) == 2, 'I12 discovers lower and uppercase CIF members'
        checks.imported_values(project.experiments['cif_experiment'])
    project.save_as(tmp_path / 'after')
    after = native.saved_model(tmp_path / 'after')
    if layout != 'shadow':
        assert 'experiments/cif_experiment.edi' in after, (
            'I12 regenerates the CIF member as a native entity'
        )
        del after['experiments/cif_experiment.edi']
    assert after == native.saved_model(tmp_path / 'before'), (
        'I12 preserves pre-existing entity bytes and regenerates CIF members without sidecars'
    )
    assert not any(p.suffix.lower() == '.cif' for p in (tmp_path / 'after').rglob('*')), (
        'I12 saves no lower or uppercase CIF entity documents'
    )
    assert native.snapshot(source) == before, 'I12 discovery leaves every source byte intact'


def test_native_experiment_control_still_loads_and_saves(tmp_path, api):
    project = api.Project.load(native.project(tmp_path))
    assert len(project.experiments) == 1, 'Native experiment loading remains a live valid control'
    project.save_as(tmp_path / 'saved')
    values = account.cells((tmp_path / 'saved/experiments/bank.edi').read_text())
    assert values[account.key('_instrument.setup_wavelength')] == ['1.54'], (
        'The native experiment preserves its independently authored wavelength through save'
    )
