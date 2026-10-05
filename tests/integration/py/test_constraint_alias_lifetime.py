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
