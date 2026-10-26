"""CIF factories preserve existing main readers and native-only project discovery."""

import importlib

import gemmi
import pytest

from tests.fixtures import cif_accounting as account
from tests.fixtures import structure_cif_refusal as case
from tests.integration.py import structure_cif_refusal_checks as checks


@pytest.fixture
def api():
    return importlib.import_module(account.API)


@pytest.mark.parametrize('style', ['dot', 'underscore', 'upper', 'multiblock'])
@pytest.mark.parametrize('method', ['from_cif_str', 'from_cif_path'])
def test_structure_factories_preserve_main_cif_admission(tmp_path, api, style, method):
    text = case.text(style)
    assert len(gemmi.cif.read_string(text)) >= 1, (
        'Each refusal witness is independently parseable CIF rather than a syntax failure'
    )
    path = tmp_path / 'input.cif'
    path.write_text(text)
    before = case.snapshot(tmp_path)
    if style == 'underscore':
        checks.main_values(
            getattr(api.StructureFactory, method)(text if method.endswith('str') else path)
        )
    else:
        with pytest.raises((ValueError, RuntimeError)) as caught:
            getattr(api.StructureFactory, method)(text if method.endswith('str') else path)
        checks.reason(str(caught.value))
    assert case.snapshot(tmp_path) == before, 'A factory refusal never writes partial import files'


@pytest.mark.parametrize('style', ['dot', 'underscore', 'upper', 'multiblock'])
@pytest.mark.parametrize('method', ['add_from_cif_str', 'add_from_cif_path'])
def test_structure_collection_preserves_main_cif_admission_and_model(tmp_path, api, style, method):
    project = api.Project.load(case.project(tmp_path))
    project.save_as(tmp_path / 'before')
    before = case.saved_model(tmp_path / 'before')
    count = len(project.structures)
    path = tmp_path / 'input.cif'
    path.write_text(case.text(style))
    argument = case.text(style) if method.endswith('str') else path
    if style == 'underscore':
        getattr(project.structures, method)(argument)
        checks.main_values(project.structures['cif_only'])
    else:
        with pytest.raises((ValueError, RuntimeError)) as caught:
            getattr(project.structures, method)(argument)
        checks.reason(str(caught.value))
    assert len(project.structures) == count + (style == 'underscore'), (
        'Main-accepted CIF adds one structure; a refused CIF retains every existing structure'
    )
    if style == 'underscore':
        project.structures.remove('cif_only')
    project.save_as(tmp_path / 'after')
    after = case.saved_model(tmp_path / 'after')
    assert after == before, (
        'CIF admission preserves every pre-existing structure, experiment and analysis byte'
    )
    assert path.read_text() == case.text(style), 'CIF admission never rewrites its input'


@pytest.mark.parametrize('style', ['dot', 'underscore', 'upper', 'multiblock'])
@pytest.mark.parametrize('layout', ['distinct', 'shadow', 'upper-suffix'])
def test_project_structure_cif_discovery_keeps_main_native_only_selection(
    tmp_path, api, style, layout
):
    control = tmp_path / 'control'
    control.mkdir()
    api.Project.load(case.project(control)).save_as(tmp_path / 'before')
    source = case.poisoned_project(tmp_path, style, layout)
    before = case.snapshot(source)
    project = api.Project.load(source)
    project.save_as(tmp_path / 'after')
    after = case.saved_model(tmp_path / 'after')
    assert {
        path: data for path, data in after.items() if path.endswith('.edi')
    } == case.saved_model(tmp_path / 'before'), (
        'Main ignores sidecar .cif and .CIF files, including a same-stem native sibling'
    )
    assert len(project.structures) == 1, 'Main does not import a sidecar as a new structure'
    assert {path: data for path, data in after.items() if not path.endswith('.edi')} == {
        path: data
        for path, data in before.items()
        if path.startswith('structures/') and not path.endswith('.edi')
    }, 'Main retains ignored CIF sidecars byte-for-byte as saved project assets'
    assert case.snapshot(source) == before, (
        'Native-only discovery leaves all native and sidecar CIF source bytes intact'
    )


def test_native_structure_project_control_still_loads_and_saves(tmp_path, api):
    project = api.Project.load(case.project(tmp_path))
    assert len(project.structures) == 1, 'Native project loading remains a live valid control'
    project.save_as(tmp_path / 'saved')
    values = account.cells((tmp_path / 'saved/structures/phase.edi').read_text())
    assert values[account.key('_cell.length_a')] == ['4.1'], (
        'The native structure control preserves its independent lattice length through save'
    )
