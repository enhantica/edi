"""real migration, preserving pre-task bounds and independent references."""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
PINS = json.loads((ROOT / 'tests/fixtures/c14_t4_neutron/page_pins.json').read_text())


@pytest.mark.parametrize('page', PINS['pages'])
def test_page_migration_executes_unchanged_reference_pins(page):
    result = subprocess.run(
        [sys.executable, str(ROOT / 'tests/system/manual/c14_t4_page_migration.py'), page],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=25,
    )
    assert result.returncode == 0, (
        ' actual page must use its source and satisfy unchanged FullProf pins: '
        + result.stdout[-1000:]
        + result.stderr[-2000:]
    )
    # The removed TCH + BeBa subject's historical bounds stay archived; every
    # retained model still executes its original unchanged bounds.
    evidence = (
        'replacement-model checks'
        if page == 'pd-neut-cwl_PbSO4_beba-asymmetry'
        else 'unchanged agreement pins'
    )
    assert 'migration and ' + evidence + ' verified' in result.stdout, (
        ' page execution must reach the post-calculation migration assertions'
    )


@pytest.mark.parametrize(
    'name',
    [
        'pd-neut-cwl_lab6-echidna_fcj-asymmetry',
        'pd-neut-cwl_pbso4_beba-asymmetry',
        'pd-neut-tof_fe_pseudo-voigt',
    ],
)
def test_cli_builder_migrates_the_saved_project(tmp_path, name):
    spec = importlib.util.spec_from_file_location(
        'c14_t4_builder', ROOT / 'tools/cli_projects/build_c11_t57_projects.py'
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    project = module.BUILDERS[name]()
    for structure in project.structures:
        assert not dict(structure.scattering_lengths_fm), (
            ' CLI builder must remove natural-element override maps'
        )
    project.save_as(tmp_path / 'saved')
    emitted = '\n'.join(p.read_text() for p in (tmp_path / 'saved/experiments').glob('*.edi'))
    assert '_scattering_source.neutron_scattering_length' in emitted, (
        ' CLI builder must persist the source in the generated experiment'
    )
