#!/usr/bin/env python3
"""Regenerate 's direct-crysta silicon observed-pattern oracle."""

from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SOURCE = HERE / 'direct_crysta_oracle.cpp'
DONOR = ROOT / 'tests/fixtures/c09_t6_ncaf_5bank_absorption/type_none_project'
SILICON = ROOT / 'tests/fixtures/c12_t3_space_group_code/si_origin_2.edi'
PREFIX = ROOT / 'build/crysta-prefix'
OUTPUT = HERE / 'oracle.json'
REFERENCE_COMMIT = '39ada82c8aef8b4657c4ae8c68e888668db0f38e'
REFERENCE_B_ISO = 0.5315


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        check=True,
        text=True,
        capture_output=True,
    )


def main() -> None:
    installed_sha = (PREFIX / '.crysta-sha').read_text(encoding='utf-8').strip()
    with tempfile.TemporaryDirectory(prefix='-oracle-') as raw:
        work = Path(raw)
        (work / 'CMakeLists.txt').write_text(
            f'''\
cmake_minimum_required(VERSION 3.21)
project(c09_t12_direct_crysta_oracle LANGUAGES CXX)
set(CMAKE_DISABLE_FIND_PACKAGE_Python TRUE)
set(CMAKE_DISABLE_FIND_PACKAGE_Python2 TRUE)
set(CMAKE_DISABLE_FIND_PACKAGE_Python3 TRUE)
find_package(crysta CONFIG REQUIRED)
add_executable(oracle "{SOURCE.as_posix()}")
target_compile_features(oracle PRIVATE cxx_std_20)
target_link_libraries(oracle PRIVATE crysta::crysta)
''',
            encoding='utf-8',
        )
        build = work / 'build'
        _run(
            [
                'cmake',
                '-S',
                str(work),
                '-B',
                str(build),
                '-G',
                'Ninja',
                '-DCMAKE_BUILD_TYPE=Release',
                f'-DCMAKE_PREFIX_PATH={PREFIX}',
            ],
            work,
        )
        _run(['cmake', '--build', str(build), '-j', '2'], work)
        generated = _run([str(build / 'oracle'), str(DONOR)], work)

    rows = [tuple(map(float, line.split())) for line in generated.stdout.splitlines()]
    assert len(rows) == 257
    oracle = {
        'schema': 1,
        'provenance': {
            'crysta_commit': installed_sha,
            'generator': SOURCE.name,
            'generator_sha256': _sha256(SOURCE),
            'role': "crysta round-trip oracle, independent of edi's fit path",
            'independent_reference': {
                'engine': 'easydiffraction v0.19.1+dev12',
                'commit': REFERENCE_COMMIT,
                'project': 'refine-si-sepd',
                'saved_b_iso': '0.5315(43) A^2',
            },
        },
        'silicon': {
            'space_group': 'F d -3 m',
            'coord_system_code': '2',
            'cell_a_angstrom': 5.431,
            'site': ['Si1', 'Si', 'a', 0.125, 0.125, 0.125],
            'target_b_iso_angstrom2': REFERENCE_B_ISO,
            'neutron_b_c_fm': 4.1491,
            'structure_sha256': _sha256(SILICON),
        },
        'grid': [row[0] for row in rows],
        'observed': [row[1] for row in rows],
    }
    OUTPUT.write_text(json.dumps(oracle, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
