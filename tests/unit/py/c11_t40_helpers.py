"""Shared hidden-test helpers for the  schema epoch."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any

from conftest import corpus_case_dir

ROOT = Path(__file__).resolve().parents[3]
REFERENCE = ROOT / 'tests/fixtures/c11_t40_diffraction_lib_reference/oracle.json'
CW_FIXTURE = ROOT / 'tests/fixtures/c11_t4_cw_selection'

TAG_RENAMES = {
    '_peak.broad_gauss_size_g': '_peak.broad_gauss_size',
    '_peak.broad_gauss_strain_g': '_peak.broad_gauss_strain',
    '_peak.broad_lorentz_size_l': '_peak.broad_lorentz_size',
    '_peak.broad_lorentz_strain_l': '_peak.broad_lorentz_strain',
}


def oracle() -> dict[str, Any]:
    return json.loads(REFERENCE.read_text(encoding='utf-8'))


def descriptor(surface: str, name: str) -> dict[str, Any]:
    matches = [
        row
        for row in oracle()['descriptors']
        if row['surface'] == surface and row['attribute'] == name
    ]
    assert len(matches) == 1, (surface, name, matches)
    return matches[0]


def _to_schema_2(text: str) -> str:
    text = text.replace('_edi.schema_version 1', '_edi.schema_version 2')
    for old, new in TAG_RENAMES.items():
        text = text.replace(old, new)
    return text


def _metadata_data_rows(text: str) -> str:
    lines = text.splitlines(keepends=True)
    positions = [
        index for index, line in enumerate(lines) if line.strip() == '_data.time_of_flight'
    ]
    assert len(positions) == 1, 'The metadata vehicle retains exactly one original TOF data loop'
    start = positions[0]
    assert start > 0 and lines[start - 1].strip() == 'loop_', (
        'The metadata vehicle must reach the actual measured-data loop header'
    )
    while start < len(lines) and lines[start].startswith('_data.'):
        start += 1
    end = start
    while end < len(lines) and lines[end].strip() and not lines[end].startswith(('_', 'loop_')):
        end += 1
    rows = lines[start:end]
    assert len(rows) > 3, 'The metadata vehicle must begin with a nontrivial measured pattern'
    selected = [rows[0], rows[len(rows) // 2], rows[-1]]
    assert len(set(selected)) == 3, (
        'The metadata walk keeps distinct original rows spanning the complete observed interval'
    )
    return ''.join(lines[:start] + selected + lines[end:])


def make_schema_2_project(
    tmp_path: Path, *, cell_only_free: bool = False, metadata_only: bool = False
) -> Path:
    destination = tmp_path / 'schema-2-project'
    shutil.copytree(corpus_case_dir('si-sepd-s2') / 'project', destination)
    for path in destination.rglob('*.edi'):
        text = _to_schema_2(path.read_text(encoding='utf-8'))
        if path.parent.name == 'experiments':
            # Whole-value substitution: the surviving corpus declares this tag as `0.5(1)`,
            # `0.` or `0.0000`, so a prefix replace would splice (`7.30(21).5(1)`).
            text = re.sub(
                r'_peak\.broad_gauss_sigma_0 +\S+',
                '_peak.broad_gauss_sigma_0 7.30(21)',
                text,
                count=1,
            )
            text = text.replace(
                '_absorption.type none',
                '_absorption.type cylinder\n_absorption.abscor1 0.05\n_absorption.abscor2 0.0',
                1,
            )
        if cell_only_free:
            text = re.sub(r'(?<=\d)\([^\n()]*\)', '', text)
            if path.parent.name == 'structures':
                text = text.replace(
                    '_cell.length_a 10.250256',
                    '_cell.length_a 10.250256(5)',
                    1,
                )
        if metadata_only and path.parent.name == 'experiments':
            text = _metadata_data_rows(text)
        path.write_text(text, encoding='utf-8')
    return destination


def make_schema_2_case(tmp_path: Path, case: str) -> Path:
    destination = tmp_path / f'schema-2-{case}'
    structures = destination / 'structures'
    experiments = destination / 'experiments'
    structures.mkdir(parents=True)
    experiments.mkdir()
    structure = _to_schema_2((CW_FIXTURE / 'structure.edi').read_text(encoding='utf-8'))
    experiment = _to_schema_2((CW_FIXTURE / 'cases' / f'{case}.edi').read_text(encoding='utf-8'))
    (structures / 'ncaf.edi').write_text(structure, encoding='utf-8')
    (experiments / 'wish_5_6.edi').write_text(experiment, encoding='utf-8')
    return destination


def experiment_path(project: Path) -> Path:
    experiments = sorted((project / 'experiments').glob('*.edi'))
    assert len(experiments) == 1
    return experiments[0]


def tree_bytes(root: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in sorted(root.rglob('*'))
        if path.is_file()
    }
