"""Check the small independent scan sources and the seeded data transformation."""

import hashlib
import json
from pathlib import Path

from tests.fixtures.ui_responsiveness.generate import reduced_scan

HERE = Path(__file__).resolve().parents[2] / 'fixtures/ui_responsiveness'


def test_scan_source_members_retain_the_owner_archive_identity():
    manifest = json.loads((HERE / 'scan-source.json').read_text())
    assert (
        manifest['archive_sha256']
        == '8a49c250a70181f32424aea38e87edf9054a12aa2916c8e0d60d85946f9cc305'
    ), 'The reduced input must name the independently supplied owner archive'
    assert len(manifest['members']) == 7, (
        'The source consists of six project records and one original template pattern'
    )
    for member, digest in manifest['members'].items():
        assert hashlib.sha256((HERE / 'scan' / member).read_bytes()).hexdigest() == digest, (
            'Every small scan source must preserve its extracted archive bytes'
        )


def test_seeded_reduction_preserves_grid_template_and_view_structure(tmp_path):
    first, second = tmp_path / 'one', tmp_path / 'two'
    for destination in (first, second):
        project = reduced_scan(destination, count=3)
        source = HERE / 'scan/44k_project'
        assert {
            str(p.relative_to(project)): p.read_bytes() for p in project.rglob('*') if p.is_file()
        } == {
            str(p.relative_to(source)): p.read_bytes() for p in source.rglob('*') if p.is_file()
        }, 'Reduction preserves project, structure, analysis, experiment and report records'
    patterns = sorted((first / '44k_data').glob('*.xy'))
    assert len(patterns) == 3, 'The test reduction must stage the requested pattern count'
    original = HERE / 'scan/44k_data/scan-0514_pilatus_integrated_0000.xy'
    assert patterns[0].read_bytes() == original.read_bytes(), (
        'The original template is retained byte for byte'
    )

    def grid(path):
        return [
            float(line.split()[0])
            for line in path.read_text().splitlines()
            if line.strip() and not line.startswith('#')
        ]

    assert all(grid(path) == grid(original) for path in patterns), (
        'Seeded variations retain every original angular bin'
    )
    assert patterns[1].read_bytes() != patterns[2].read_bytes(), (
        'Distinct dataset changes must not be vacuous identical inputs'
    )
    assert all(
        path.read_bytes() == (second / '44k_data' / path.name).read_bytes() for path in patterns
    ), 'The reduced scan must be deterministic for an unchanged seed'
