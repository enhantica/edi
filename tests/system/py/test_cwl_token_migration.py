"""The migration sweep must also reject newly introduced retired spellings."""

import shutil
import subprocess
from pathlib import Path

import pytest

from tests.fixtures.cwl_family import profiles

ROOT = Path(__file__).resolve().parents[3]


def test_no_tracked_file_keeps_a_retired_cw_token():
    result = subprocess.run(
        [shutil.which('git'), 'ls-files', '-z'], cwd=ROOT, capture_output=True, check=True
    )
    paths = [ROOT / name.decode() for name in result.stdout.split(b'\0') if name]
    hits = profiles.migration_hits(paths, ROOT)
    assert not hits, (
        'Every tracked file outside the exact historical capture and external enum boundary '
        'must migrate retired CW tokens'
    )


def test_retired_token_scan_detects_each_planted_spelling(tmp_path):
    for index, token in enumerate(profiles.RETIRED):
        path = tmp_path / f'planted-{index}.edi'
        path.write_text(f'_peak.type {token}\n')
        assert profiles.retired_hits([path]) == [str(path)], (
            'The migration scan must fail when either retired token is planted in a new file'
        )


@pytest.mark.parametrize('escape', ['changed-input', 'extra-token', 'copied-path'])
def test_retained_capture_exception_requires_exact_bytes_and_location(tmp_path, escape):
    fixture = tmp_path / 'tests/fixtures/cwl_family'
    shutil.copytree(ROOT / 'tests/fixtures/cwl_family/rename_inputs', fixture / 'rename_inputs')
    shutil.copyfile(
        ROOT / 'tests/fixtures/cwl_family/rename-input-sha256.json',
        fixture / 'rename-input-sha256.json',
    )
    historical = fixture / 'rename_inputs/fcj/experiments/bank.edi'
    assert not profiles.migration_hits([historical], tmp_path), (
        'Only the exact retained historical FCJ input is exempt from the token migration'
    )
    if escape == 'changed-input':
        historical.write_text(historical.read_text().replace('.023', '.024', 1))
    elif escape == 'extra-token':
        historical.write_text(historical.read_text() + '\n' + profiles.RETIRED[1] + '\n')
    else:
        copied = fixture / 'rename_inputs/another.edi'
        shutil.copyfile(historical, copied)
        historical = copied
    assert profiles.migration_hits([historical], tmp_path) == [str(historical)], (
        'A changed vehicle, extra retired token or copied path '
        'cannot borrow the historical exemption'
    )


@pytest.mark.parametrize(
    'escape', ['ordinary', 'extra', 'duplicate', 'wrong-backend', 'copied-path']
)
def test_external_profile_literal_is_limited_to_its_reader_boundary(tmp_path, escape):
    fixture = tmp_path / 'tests/fixtures/cwl_family'
    fixture.mkdir(parents=True)
    shutil.copyfile(
        ROOT / 'tests/fixtures/cwl_family/rename-input-sha256.json',
        fixture / 'rename-input-sha256.json',
    )
    path = tmp_path / 'tools/comparison/run_diffraction_lib.py'
    path.parent.mkdir(parents=True)
    source = (ROOT / 'tools/comparison/run_diffraction_lib.py').read_text()
    path.write_text(source)
    assert not profiles.migration_hits([path], tmp_path), (
        'The external reader must retain its own profile and calculator enum literals'
    )
    if escape == 'ordinary':
        path.write_text(source + f"\nPEAK_TYPE = '{profiles.RETIRED[1]}'\n")
    elif escape == 'extra':
        path.write_text(source + f"\nOTHER = '{profiles.RETIRED[0]}'\n")
    elif escape == 'duplicate':
        line = next(line for line in source.splitlines(True) if line.startswith('CALCULATOR ='))
        path.write_text(source + line)
    elif escape == 'wrong-backend':
        path.write_text(source.replace("'crysfml'", "'crysta'"))
    else:
        copied = path.with_name('copied.py')
        copied.write_text(source)
        path = copied
    assert profiles.migration_hits([path], tmp_path) == [str(path)], (
        'The external enum exemption rejects extra tokens, duplicates, changed dispatch and copies'
    )
