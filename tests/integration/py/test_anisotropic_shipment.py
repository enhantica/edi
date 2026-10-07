"""The anisotropic Y2O3 page ships with its independent reference and CLI project."""

import hashlib
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
NAME = 'pd-neut-cwl_y2o3_beta-adp'


def test_y2o3_reference_is_vendored_byte_identically_and_named():
    reference = ROOT / 'knowledge/verification/fullprof'
    hashes = json.loads(
        (ROOT / 'tests/fixtures/anisotropic_adps/fullprof-sha256.json').read_text()
    )
    for name, digest in hashes.items():
        path = reference / NAME / name
        assert path.is_file(), 'The Y2O3 page must ship every independent FullProf reference file'
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, (
            'The shipped FullProf reference must match its independent upstream bytes'
        )
    assert NAME in (reference / 'PROVENANCE.md').read_text(), (
        'The FullProf provenance record must name the anisotropic Y2O3 reference'
    )


def test_y2o3_page_and_cli_project_are_registered():
    page = ROOT / 'docs/dev/verification/pd-neut-cwl_Y2O3_beta-adp.py'
    assert page.is_file(), 'The anisotropic Y2O3 verification page must join notebook-tests'
    projects = yaml.safe_load((ROOT / 'docs/user/cli/projects.yml').read_text())
    entries = [entry for entry in projects['projects'] if entry['id'] == NAME]
    assert len(entries) == 1, 'The anisotropic Y2O3 CLI project must have exactly one registry row'
    assert entries[0].get('executing') is True, (
        'The anisotropic Y2O3 CLI project must join the executing shipment set'
    )
    assert (ROOT / 'docs/user/cli' / NAME / 'project').is_dir(), (
        'The registered anisotropic CLI project must have runnable project data'
    )
