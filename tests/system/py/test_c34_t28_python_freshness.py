"""I23: held and saved freshness matches labelled pre-move observations."""

import json
import shutil
from pathlib import Path

import edi
import pytest

from tests.fixtures.c34_t28_baseline import generate_bytes as byte_reference
from tests.fixtures.c34_t28_baseline import generate_freshness as reference

ROOT = Path(__file__).resolve().parents[3]
BASELINE = json.loads((reference.HERE / 'freshness.json').read_text())


def test_python_freshness_inputs_and_route_inventory_stay_bound(tmp_path, monkeypatch):
    committed = reference.corpus_root(ROOT)
    # A prior fit may persist different values into the session scratch. It
    # cannot become the input oracle or the vehicle for these regression pins.
    scratch = tmp_path / 'mutated-corpus'
    scratch.mkdir()
    with monkeypatch.context() as isolated:
        isolated.setenv('EDI_CRYSTA_CORPUS_ROOT', str(scratch))
        assert reference.corpus_root(ROOT) == committed, (
            ' I23 persisted session scratch cannot replace committed freshness inputs'
        )
    assert BASELINE['source_commit'] == reference.BASE, (
        ' I23 Python freshness uses the named pre-move build'
    )
    assert set(BASELINE['routes']) == set(reference.ROUTES), (
        ' I23 every represented Python write route retains its baseline observation'
    )
    assert reference.hashes(reference.HERE / 'freshness-input') == BASELINE['input_sha256'], (
        ' I23 the controlled input bytes cannot drift beneath the observation'
    )
    single = reference.corpus_root(ROOT) / 'cosio-d20-s1/project'
    # Before: raw fit input hash. After : only the declared calculator
    # seed is reversed; every fit/undo input byte still meets the immutable pin.
    assert (
        byte_reference.legacy_input_hashes(single, 'corpus:cosio-d20-s1/project')
        == BASELINE['fit_sha256']
    ), ' I23 fit and undo inputs retain the complete committed corpus case'
    scan = reference.corpus_root(ROOT) / 'cosio-d20-scan-3f/project'
    extension = json.loads(
        (ROOT / 'tests/fixtures/constraint_expressions/byte-pins.json').read_text()
    )['cases']['corpus:cosio-d20-scan-3f/project']
    assert extension['before']['input_sha256'] == BASELINE['scan_sha256'], (
        'the scan model extension must retain the immutable earlier freshness input witness'
    )
    assert set(extension['after_input_sha256']) == set(BASELINE['scan_sha256']), (
        'the scan model extension must retain every sequential frame and file'
    )
    assert reference.input_hashes(scan) == extension['after_input_sha256'], (
        ' I23 every sequential input, including each data frame, stays pinned'
    )


@pytest.mark.parametrize(
    'route', [r for r in reference.ROUTES if r not in {'sequential', 'fit', 'undo'}]
)
def test_python_write_keeps_the_pre_move_freshness_regression_pin(tmp_path, route):
    observed = reference.observe(route, tmp_path / route, ROOT)
    assert observed == BASELINE['routes'][route], (
        ' I23 a Python write preserves the exact old geometry and pattern renewal: ' + route
    )


@pytest.mark.parametrize('route', ['fit', 'undo'])
def test_scale_only_fit_and_undo_preserve_held_geometry(tmp_path, route):
    # ADR-0078 section 7 writes a completed dependent only when its value changes.
    # Retain the old observation; replace only its blanket held-window renewal.
    expected = json.loads(json.dumps(BASELINE['routes'][route]))
    assert expected['after']['held_window_current'] is False, (
        'the pre-feature witness must still record its original blanket geometry renewal'
    )
    expected['after']['held_window_current'] = True
    project, window = reference.prepared(edi, tmp_path / route, route, ROOT)
    before = geometry_inputs(project)
    before_state = reference.state(project, window, tmp_path / 'before')
    scale_before = project.experiment.linked_structure.scale.value
    reference.mutate(project, route)
    assert geometry_inputs(project) == before, (
        'the scale-only fit and undo witness must leave every stored geometry input unchanged'
    )
    assert project.experiment.linked_structure.scale.value != scale_before, (
        'the scale-only witness must actually move or undo its independent scale'
    )
    observed = {
        'before': before_state,
        'after': reference.state(project, window, tmp_path / 'after'),
        'refused': None,
    }
    assert observed == expected, (
        'a scale-only fit or undo keeps held geometry current and preserves every saved unit'
    )


def geometry_inputs(project):
    cell = project.structure.cell
    return tuple(
        getattr(cell, name).value
        for name in (
            'length_a',
            'length_b',
            'length_c',
            'angle_alpha',
            'angle_beta',
            'angle_gamma',
        )
    ) + tuple(
        getattr(site, name).value
        for site in project.structure.atom_sites
        for name in ('fract_x', 'fract_y', 'fract_z', 'occupancy', 'adp_iso')
    )


@pytest.mark.parametrize('route', ['fit', 'undo'])
@pytest.mark.parametrize(('field', 'offset'), [('fract_x', 0.015), ('adp_iso', 0.35)])
def test_geometry_changing_fit_and_undo_stale_held_geometry(tmp_path, route, field, offset):
    # These are input and currentness invariants, never fitted-number regression pins.
    source = reference.corpus_root(ROOT) / 'cosio-d20-s1/project'
    directory = tmp_path / 'input'
    shutil.copytree(source, directory)
    project = edi.Project.load(directory)
    for parameter in project.parameters:
        parameter.free = False
    parameter = getattr(project.structure.atom_sites['Co2'], field)
    parameter.free = True
    parameter.value += offset
    if route == 'undo':
        project.analysis.fit()
    project.analysis.calculate()
    window = project.structure.geometry()
    before = geometry_inputs(project)
    assert window.is_current(), 'the geometry-changing witness must begin with a current window'
    reference.mutate(project, route)
    assert geometry_inputs(project) != before, (
        'each coordinate and ADP fit/undo control must actually change its geometry inputs'
    )
    assert not window.is_current(), (
        'a fit or undo that moves a coordinate or ADP must stale its retained geometry window'
    )
