"""P3: persisted start state makes a fit reversible."""

from __future__ import annotations

import importlib
import os
import re
from pathlib import Path

import pytest

from conftest import crysta_reference_source

ROOT = Path(__file__).resolve().parents[3]
LIB = importlib.import_module('edi')


def _crysta_root() -> Path:
    candidates = []
    override = os.environ.get('EDI_CRYSTA_CORPUS_ROOT')
    if override:
        candidates.append(Path(override).resolve().parents[1])
    candidates.extend((ROOT, crysta_reference_source()))
    for candidate in candidates:
        if (candidate / 'tests/fitting/manifest.yml').is_file():
            return candidate
    message = "the  start-state gate requires crysta's committed corpus"
    raise AssertionError(message)


def test_start_value_and_uncertainty_round_trip_through_the_single_loader(
    tmp_path: Path,
) -> None:
    source = _crysta_root() / 'tests/fitting/lbco-hrpt-s2/project'
    project = LIB.Project.load(source)
    parameter = project.structure.cell.length_a
    parameter.value = 3.771
    parameter.uncertainty = 0.007
    parameter.start_value = 3.913
    parameter.start_uncertainty = 0.023

    destination = tmp_path / 'round-trip'
    project.save_as(destination)
    texts = [path.read_text(encoding='utf-8') for path in destination.rglob('*.edi')]
    versions = [
        int(match.group(1))
        for text in texts
        for match in re.finditer(r'^_edi\.schema_version\s+(\d+)\s*$', text, re.MULTILINE)
    ]
    assert versions, 'saved .edi files must declare their schema version'
    assert min(versions) >= 3, 'persisted start state requires a schema bump from v2'
    serialized = '\n'.join(texts)
    assert 'start_value' in serialized, (
        'the serialized project must persist the value captured before refinement'
    )
    assert 'start_uncertainty' in serialized, (
        'the serialized project must persist the uncertainty captured before refinement'
    )

    reloaded = LIB.Project.load(destination).structure.cell.length_a
    assert float(reloaded.value) == pytest.approx(3.771), (
        'reloading must preserve the current refined parameter value'
    )
    assert float(reloaded.uncertainty) == pytest.approx(0.007), (
        'reloading must preserve the current refined parameter uncertainty'
    )
    assert float(reloaded.start_value) == pytest.approx(3.913), (
        'reloading must recover the persisted pre-fit parameter value'
    )
    assert float(reloaded.start_uncertainty) == pytest.approx(0.023), (
        'reloading must recover the persisted pre-fit parameter uncertainty'
    )

    second = tmp_path / 'second-round-trip'
    LIB.Project.load(destination).save_as(second)
    twice = LIB.Project.load(second).structure.cell.length_a
    assert float(twice.start_value) == pytest.approx(3.913), (
        'a second save-load cycle must retain the original pre-fit value'
    )
    assert float(twice.start_uncertainty) == pytest.approx(0.023), (
        'a second save-load cycle must retain the original pre-fit uncertainty'
    )
