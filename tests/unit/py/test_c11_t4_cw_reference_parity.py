"""independent-reference gates at the live, provenance-closed crysta anchor."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

import edi

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / 'tests/fixtures/c11_t4_cw_selection'
CASES = FIXTURE / 'cases'
MANIFEST = FIXTURE / 'manifest.json'
MANIFEST_SHA256 = '6633f325680b478194eccc76335f55e59b64c84b5d7043561b18ee106f40e095'


def _manifest() -> dict[str, Any]:
    adaptation = json.loads(
        (ROOT / 'tests/fixtures/e04_t12_public_release/fixture-metadata.json').read_text()
    )[MANIFEST.relative_to(ROOT).as_posix()]
    assert adaptation['before_sha256'] == MANIFEST_SHA256, (
        'the metadata adaptation must retain the original independent dictionary manifest identity'
    )
    assert hashlib.sha256(MANIFEST.read_bytes()).hexdigest() == adaptation['after_sha256'], (
        'the manifest must equal the complete pinned descriptive-only adaptation'
    )
    return json.loads(MANIFEST.read_text(encoding='utf-8'))


def _project_for_case(tmp_path: Path, case: str) -> Path:
    project = tmp_path / case
    (project / 'structures').mkdir(parents=True)
    (project / 'experiments').mkdir()
    shutil.copy2(FIXTURE / 'structure.edi', project / 'structures/ncaf.edi')
    shutil.copy2(CASES / f'{case}.edi', project / 'experiments/wish_5_6.edi')
    return project


def _remove_tag(source: Path, destination: Path, tag: str) -> None:
    lines = source.read_text(encoding='utf-8').splitlines()
    matches = [index for index, line in enumerate(lines) if line.startswith(tag + ' ')]
    assert len(matches) == 1, f'{source.name}: expected exactly one {tag}'
    del lines[matches[0]]
    destination.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def test_c11_t4_cw_required_registry_is_complete_against_pinned_dictionary(
    tmp_path: Path,
) -> None:
    """Removing any one manifest tag proves it is in edi's CW required set."""
    reference = _manifest()
    provenance = reference['provenance']
    assert provenance == {
        'role': 'independent crysta dictionary/grammar classification oracle',
        'repository': 'crysta',
        'crysta_commit': '501d49eaf484859829ed92a4ac83b7b82dae3f5b',
        'dictionary_path': 'data/dictionary/parameters.yaml',
        'grammar_paths': [
            'src/core/experiment_family.hpp',
            'src/core/experiment_tokens.hpp',
        ],
        'derivation': (
            ' re-ran the  committed case matrix at crysta 501d49ea; the hidden '
            'gate executes that pinned crysta library loader on every committed case'
        ),
        'numeric_role': (
            'nontrivial transport inputs only; no fixture number is a CW-physics oracle'
        ),
    }, 'the CW reference must retain its independently pinned dictionary provenance'
    tags = [
        tag for family_tags in reference['dictionary']['families'].values() for tag in family_tags
    ]
    assert tags == [
        '_peak.broad_gauss_u',
        '_peak.broad_gauss_v',
        '_peak.broad_gauss_w',
        '_peak.broad_lorentz_x',
        '_peak.broad_lorentz_y',
        '_instrument.calib_twotheta_offset',
        '_instrument.setup_wavelength',
    ]
    assert len(tags) == len(set(tags)) == 7

    source = CASES / 'cwl_valid.edi'
    missing_diagnostics: list[str] = []
    for index, tag in enumerate(tags):
        case = f'missing-{index}'
        project = tmp_path / case
        (project / 'structures').mkdir(parents=True)
        (project / 'experiments').mkdir()
        shutil.copy2(FIXTURE / 'structure.edi', project / 'structures/ncaf.edi')
        _remove_tag(source, project / 'experiments/wish_5_6.edi', tag)
        try:
            edi.Project.load(project)
        except edi.IoError as error:
            if tag not in str(error):
                missing_diagnostics.append(f'{tag}: {error}')
        else:
            missing_diagnostics.append(f'{tag}: missing required tag was accepted')
    assert not missing_diagnostics, '\n'.join(missing_diagnostics)
