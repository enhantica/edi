"""Whole-byte retention is invariant under host path-key spelling, including refusals."""

import json
from pathlib import Path, PureWindowsPath

import pytest

from tests.fixtures.example_catalogue.retained_bytes import retained_bytes

ROOT = Path(__file__).resolve().parents[3]
PROJECTS = json.loads((ROOT / 'tests/fixtures/c34_t23_cli_projects/project-ids.json').read_text())[
    'source_to_project'
]
SEEDS = (
    'cosio-d20-s1',
    'cosio-d20-s4',
    'lbco-hrpt-s2',
    'lbco-hrpt-s4',
    'si-sepd-s2',
    'si-sepd-s5',
    'cosio-d20-scan-3f',
    'ncaf-wish-2bank-s3',
    'ncaf-wish-3bank-s5',
)


@pytest.mark.parametrize('seed', SEEDS)
@pytest.mark.parametrize('spelling', ['posix', 'windows-path', 'windows-string'])
def test_retained_seed_identity_and_byte_refusal_are_independent_of_host_paths(seed, spelling):
    key = 'docs/user/cli/' + PROJECTS[seed] + '/expected.json'
    raw = (ROOT / key).read_bytes()
    expected = retained_bytes(key, raw)
    native = (
        PureWindowsPath(key)
        if spelling == 'windows-path'
        else key.replace('/', '\\')
        if spelling == 'windows-string'
        else Path(key)
    )
    assert retained_bytes(native, raw) == expected, (
        'Every host path spelling retains the same complete historical source witness'
    )
    with pytest.raises(AssertionError):
        retained_bytes(native, raw + b' ')
