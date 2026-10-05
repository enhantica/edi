"""Regenerate 's visible NCAF fixtures from the recorded crysta dependency."""

from __future__ import annotations

import hashlib
import json
import runpy
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = Path(__file__).resolve().parent
RECORDED_SHA = (ROOT / 'build/crysta-src/CRYSTA_SOURCE_SHA').read_text().strip()
CRYSTA_SOURCE = ROOT / 'build/crysta-src'
CRYSTA_PREFIX = ROOT / 'build/crysta-prefix'
SOURCE_PROJECT = CRYSTA_SOURCE / 'tools/spikes/ncaf_5bank_edi_converged_jorgensen'
PROJECT = FIXTURE / 'project'
PUBLISHED_CIF = FIXTURE / 'published_cod_1000236.cif'

CIF_TWIN = """data_ncaf
_audit_creation_method              ' structural twin of the frozen NCAF EDI project'
_chemical_formula_sum               'Al2 Ca3 F14 Na2'
_cell_formula_units_Z               4
_cell_length_a                      10.250256
_cell_length_b                      10.250256
_cell_length_c                      10.250256
_cell_angle_alpha                   90
_cell_angle_beta                    90
_cell_angle_gamma                   90
_space_group_IT_number              199
_space_group_name_H-M_alt           'I 21 3'

loop_
_atom_site_label
_atom_site_type_symbol
_atom_site_symmetry_multiplicity
_atom_site_Wyckoff_symbol
_atom_site_fract_x
_atom_site_fract_y
_atom_site_fract_z
_atom_site_occupancy
_atom_site_B_iso_or_equiv
Ca1 Ca 12 b 0.4664(10) 0 0.25 1 0.93284(10)
Al1 Al 8 a 0.25193(10) 0.25193(10) 0.25193(10) 1 0.81973(10)
Na1 Na 8 a 0.08526(10) 0.08526(10) 0.08526(10) 1 2.27039(10)
F1 F 24 c 0.13761(10) 0.30558(10) 0.11963(10) 1 0.94591(10)
F2 F 24 c 0.36233(10) 0.36318(10) 0.18704(10) 1 1.44298(10)
F3 F 8 a 0.46106(10) 0.46106(10) 0.46106(10) 1 0.94745(10)
"""


def run(*command: str, cwd: Path | None = None) -> str:
    result = subprocess.run(
        command,
        cwd=cwd or ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_source() -> None:
    source_sha = run('git', 'rev-parse', 'HEAD', cwd=CRYSTA_SOURCE)
    installed_sha = (CRYSTA_PREFIX / '.crysta-sha').read_text().strip()
    if source_sha != RECORDED_SHA or installed_sha != RECORDED_SHA:
        raise RuntimeError(
            'crysta identity mismatch: '
            f'recorded={RECORDED_SHA}, source={source_sha}, installed={installed_sha}'
        )


def copy_project() -> None:
    if PROJECT.exists():
        shutil.rmtree(PROJECT)
    for relative in ('analysis/analysis.edi', 'structures/ncaf.edi'):
        destination = PROJECT / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SOURCE_PROJECT / relative, destination)
        if relative == 'structures/ncaf.edi':
            canonicalize = runpy.run_path(str(ROOT / 'tests/fixtures/ncaf_free_flags.py'))[
                'canonicalize'
            ]
            destination.write_text(canonicalize(destination.read_text()))
    for source in sorted((SOURCE_PROJECT / 'experiments').glob('*.edi')):
        destination = PROJECT / 'experiments' / source.name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)


def generate_crysta_reference() -> None:
    with tempfile.TemporaryDirectory(prefix='edi--oracle-') as temporary:
        build = Path(temporary) / 'build'
        run(
            'cmake',
            '-S',
            str(FIXTURE / 'oracle'),
            '-B',
            str(build),
            f'-DCMAKE_PREFIX_PATH={CRYSTA_PREFIX}',
            '-DCMAKE_BUILD_TYPE=Release',
        )
        run('cmake', '--build', str(build), '--parallel', '2')
        snapshot = run(str(build / 'crysta_snapshot'), str(PROJECT))
    parsed = json.loads(snapshot)
    (FIXTURE / 'crysta_reference.json').write_text(
        json.dumps(parsed, indent=2, sort_keys=True) + '\n'
    )


def write_manifest() -> None:
    frozen_files = sorted(path for path in PROJECT.rglob('*') if path.is_file()) + [
        FIXTURE / 'ncaf.cif',
        PUBLISHED_CIF,
        FIXTURE / 'crysta_reference.json',
    ]
    manifest = {
        'schema': 2,
        'crysta': {
            'source_sha': RECORDED_SHA,
            'source_path': 'tools/spikes/ncaf_5bank_edi_converged_jorgensen',
            'loader': 'crysta::load_project',
        },
        'published_structure': {
            'authors': 'G. Courbion and G. Férey',
            'journal': 'Journal of Solid State Chemistry 76 (1988) 426-431',
            'doi': '10.1016/0022-4596(88)90239-3',
            'cod_id': 1000236,
            'cod_revision': 130149,
            'cod_sha256': 'fef30351157a406336d44b35a416bfd848810b54112077b733b0fd7ca6142ae9',
            'source_file': 'published_cod_1000236.cif',
            'source_url': 'https://www.crystallography.net/cod/1000236.cif@130149',
            'role': 'independent published structural-value oracle',
        },
        'cif_twin': {
            'role': 'EDI-derived regression twin for exact representation parity',
            'value_source': 'project/structures/ncaf.edi',
        },
        'files': {str(path.relative_to(FIXTURE)): sha256(path) for path in frozen_files},
    }
    (FIXTURE / 'manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')


def main() -> None:
    verify_source()
    copy_project()
    (FIXTURE / 'ncaf.cif').write_text(CIF_TWIN)
    generate_crysta_reference()
    write_manifest()


if __name__ == '__main__':
    main()
