"""CIF structure factories and project members follow the content contract."""

import importlib
import warnings

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
    if style != 'multiblock':
        checks.main_values(
            getattr(api.StructureFactory, method)(text if method.endswith('str') else path)
        )
    else:
        with pytest.raises((ValueError, RuntimeError)) as caught:
            getattr(api.StructureFactory, method)(text if method.endswith('str') else path)
        assert '2 structure blocks' in str(caught.value), (
            'A singular CIF structure entrance refuses multiple structure blocks'
        )
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
    if style != 'multiblock':
        getattr(project.structures, method)(argument)
        checks.main_values(project.structures['cif_only'])
    else:
        with pytest.raises((ValueError, RuntimeError)) as caught:
            getattr(project.structures, method)(argument)
        assert '2 structure blocks' in str(caught.value), (
            'A singular CIF structure entrance refuses multiple structure blocks'
        )
    assert len(project.structures) == count + (style != 'multiblock'), (
        'Main-accepted CIF adds one structure; a refused CIF retains every existing structure'
    )
    if style != 'multiblock':
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
    tmp_path, api, style, layout, capfd
):
    control = tmp_path / 'control'
    control.mkdir()
    api.Project.load(case.project(control)).save_as(tmp_path / 'before')
    source = case.poisoned_project(tmp_path, style, layout)
    before = case.snapshot(source)
    capfd.readouterr()
    if style == 'multiblock' and layout != 'shadow':
        with pytest.raises((ValueError, RuntimeError)) as caught:
            api.Project.load(source)
        assert '2 structure blocks' in str(caught.value), (
            'I9 refuses multiple structure blocks in a discovered I12 CIF member'
        )
        assert case.snapshot(source) == before, 'I12 failed discovery preserves every source byte'
        return
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        project = api.Project.load(source)
    notes = [str(w.message) for w in caught] + capfd.readouterr().err.splitlines()
    if layout == 'shadow':
        assert len(project.structures) == 1, (
            'I12 reads the native member once when CIF is shadowed'
        )
        assert any('phase.cif' in n and 'not read' in n for n in notes), (
            'I12 names the shadowed structure CIF in the load report'
        )
    else:
        assert len(project.structures) == 2, 'I12 discovers lower and uppercase CIF members'
        checks.main_values(project.structures['cif_only'])
    project.save_as(tmp_path / 'after')
    after = case.saved_model(tmp_path / 'after')
    if layout != 'shadow':
        assert 'structures/cif_only.edi' in after, (
            'I12 regenerates the CIF member as a native entity'
        )
        del after['structures/cif_only.edi']
    assert after == case.saved_model(tmp_path / 'before'), (
        'I12 preserves pre-existing entity bytes and regenerates CIF members without sidecars'
    )
    assert not any(p.suffix.lower() == '.cif' for p in (tmp_path / 'after').rglob('*')), (
        'I12 saves no lower or uppercase CIF entity documents'
    )
    assert case.snapshot(source) == before, 'I12 discovery leaves every source byte intact'


def test_native_structure_project_control_still_loads_and_saves(tmp_path, api):
    project = api.Project.load(case.project(tmp_path))
    assert len(project.structures) == 1, 'Native project loading remains a live valid control'
    project.save_as(tmp_path / 'saved')
    values = account.cells((tmp_path / 'saved/structures/phase.edi').read_text())
    assert values[account.key('_cell.length_a')] == ['4.1'], (
        'The native structure control preserves its independent lattice length through save'
    )
