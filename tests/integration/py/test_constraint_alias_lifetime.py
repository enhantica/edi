"""Alias-first handles obey ordinary row ownership and detachment (ADR-0024)."""

import runpy
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
MATERIALIZE = runpy.run_path(str(ROOT / 'tests/fixtures/constraint_expressions/project.py'))[
    'materialize'
]
TARGETS = [
    ('site', 'phase.atom_site.A.adp_iso', 0.3),
    ('cell', 'phase.cell.length_a', 4.1),
    ('instrument', 'bank.instrument.setup_wavelength', 1.54),
    ('profile', 'bank.peak.broad_gauss_w', 0.15),
    ('scale', 'bank.linked_structure.phase.scale', 1.0),
    ('background', 'bank.background.1.intensity', 3.0),
]
CHILD = r"""
import gc
import sys
import edi
from tests.fixtures.constraint_expressions.project import unlink_structure

project = edi.Project.load(sys.argv[1])
handle = project.analysis.aliases['held'].param
expected = float(sys.argv[4])
assert handle is not None, 'the alias must resolve before any ordinary wrapper exists'
assert abs(handle.value - expected) < 1e-13, 'alias-first reads must match the declared value'
if sys.argv[3] == 'destroy':
    del project
else:
    kind = sys.argv[2]
    if sys.argv[3] == 'replace':
        if kind in ('site', 'cell'):
            project.structures.add(edi.Project.load(sys.argv[1]).structure)
        else:
            project.experiments.add(edi.Project.load(sys.argv[1]).experiment)
    elif kind == 'site':
        project.structure.atom_sites.remove('A')
    elif kind == 'cell':
        unlink_structure(project, 'phase')
        project.structures.remove('phase')
    elif kind == 'background':
        project.experiments.remove('bank')
    else:
        project.experiments.remove('bank')
gc.collect()
assert abs(handle.value - expected) < 1e-13, 'held alias storage must remain readable'
if sys.argv[3] != 'destroy':
    assert not handle.is_attached(), 'alias handles must inherit row attachment'
if not handle.is_attached():
    try:
        handle.value = expected + 0.125
    except RuntimeError as refusal:
        assert 'detached' in str(refusal).lower(), 'writes must report detached-row refusal'
    else:
        raise AssertionError('alias-first writes must not bypass detached-row refusal')
else:
    handle.value = expected + 0.125
    assert abs(handle.value - expected - 0.125) < 1e-13, (
        'a retained owner must support safe writes'
    )
"""


@pytest.mark.parametrize(('kind', 'target', 'expected'), TARGETS, ids=[v[0] for v in TARGETS])
@pytest.mark.parametrize('exit_route', ['remove', 'replace', 'destroy'])
def test_alias_first_handle_owns_storage_and_obeys_detachment(
    tmp_path, kind, target, expected, exit_route
):
    directory = MATERIALIZE(tmp_path, [('held', target)])
    result = subprocess.run(
        [sys.executable, '-c', CHILD, str(directory), kind, exit_route, str(expected)],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, (
        'alias-first access must preserve owned readable storage and detached-row refusal: '
        + result.stdout
        + result.stderr
    )


RETAINED_CHILD = r"""
import gc
import sys
import edi
from tests.fixtures.constraint_expressions.project import unlink_structure

project = edi.Project.load(sys.argv[1])
kind, route, flag = sys.argv[2:]
held = project.structures[0] if kind in ('site', 'cell') else project.experiments[0]
handle = project.analysis.aliases['held'].param
assert not handle.symmetry_constrained, 'the retained-owner control has no symmetry follower'
assert handle.user_constrained, 'the retained-owner control begins with a declared dependent'
if route == 'destroy':
    del project
elif route == 'remove':
    collection = project.structures if kind in ('site', 'cell') else project.experiments
    if kind in ('site', 'cell'):
        unlink_structure(project, held.name)
    collection.remove(held.name)
elif route == 'replace':
    replacement = edi.Project.load(sys.argv[1])
    if kind in ('site', 'cell'):
        item = replacement.structures[0]
        unlink_structure(replacement, item.name)
        replacement.structures.remove(item.name)
        project.structures.add(item)
    else:
        item = replacement.experiments[0]
        replacement.experiments.remove(item.name)
        project.experiments.add(item)
elif route == 'transfer':
    collection = project.structures if kind in ('site', 'cell') else project.experiments
    if kind in ('site', 'cell'):
        unlink_structure(project, held.name)
    collection.remove(held.name)
    new_owner = edi.Project.load(sys.argv[1])
    new_owner.analysis.constraints.remove('held')
    destination = new_owner.structures if kind in ('site', 'cell') else new_owner.experiments
    destination.add(held)
    del project
else:
    assert route == 'live', 'the owner-lifetime control route must be explicit'
gc.collect()
try:
    result = getattr(handle, flag)
except (ValueError, RuntimeError) as refusal:
    assert route != 'live', 'live retained owners must permit dependence reads'
    words = ('owner', 'project', 'detach', 'alias', 'parameter', 'unknown')
    assert any(word in str(refusal).lower() for word in words), (
        'an unavailable owner must refuse dependence by name')
else:
    assert isinstance(result, bool), 'dependence reads must return a safe Boolean'
    if flag == 'symmetry_constrained':
        assert not result, 'no lifetime route can invent a symmetry constraint'
    elif route == 'live':
        assert result, 'the retained live owner must preserve the declared dependence'
    elif route != 'destroy':
        assert not result, 'detached or transferred storage must not consult its former project'
"""


@pytest.mark.parametrize(('kind', 'target', 'expected'), TARGETS, ids=[v[0] for v in TARGETS])
@pytest.mark.parametrize('exit_route', ['live', 'destroy', 'remove', 'replace', 'transfer'])
@pytest.mark.parametrize('flag', ['user_constrained', 'symmetry_constrained'])
def test_retained_container_dependence_follows_only_its_live_owner(
    tmp_path, kind, target, expected, exit_route, flag
):
    directory = MATERIALIZE(tmp_path, [('held', target)], [f'held = {expected}'])
    result = subprocess.run(
        [sys.executable, '-c', RETAINED_CHILD, str(directory), kind, exit_route, flag],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, (
        'retained containers must never leave dependence reads with a dead project: '
        + result.stdout
        + result.stderr
    )
