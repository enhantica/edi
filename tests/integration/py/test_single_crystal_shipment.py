"""The single-crystal examples execute through the registered CLI checker."""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
FITTING = ROOT / 'tests/fixtures/single_crystal/fitting'
REFERENCES = json.loads((FITTING / 'fullprof.json').read_text())['cases']
PROJECTS = tuple(record['project_id'] for record in REFERENCES.values())


@pytest.mark.parametrize('name', PROJECTS)
def test_single_crystal_project_is_registered_and_executes(name):
    registry = yaml.safe_load((ROOT / 'docs/user/cli/projects.yml').read_text())['projects']
    rows = [row for row in registry if row['id'] == name]
    assert len(rows) == 1 and rows[0].get('executing') and not rows[0].get('offline'), (
        'Each single-crystal example must belong to the normal CI executing set exactly once'
    )
    directory = ROOT / 'docs/user/cli' / name
    assert (directory / 'project').is_dir() and (directory / 'expected.json').is_file(), (
        'An executing single-crystal project must ship its input tree and expected values'
    )
    expected = json.loads((directory / 'expected.json').read_text())
    assert expected, 'The single-crystal expected values must be nonempty'
    oracle = json.loads((FITTING / 'fullprof' / name / 'expected.json').read_text())
    for quantity, reference in oracle['quantities'].items():
        actual = expected.get('quantities', {}).get(quantity, {})
        assert actual.get('kind') == 'reference', (
            'CLI scale, objective and participation counts must be independent references'
        )
        assert actual.get('value') == pytest.approx(reference['value'], rel=0, abs=1e-12), (
            'CLI expected values must equal the frozen measured-data FullProf fitting twin'
        )
        for bound in ('tol_abs', 'tol_rel'):
            if bound in reference:
                assert actual.get(bound) is not None, (
                    'CLI FullProf comparisons must retain every declared numerical bound'
                )
                assert 0 <= actual[bound] <= reference[bound], (
                    'CLI fitting tolerances must not exceed the independent oracle budget'
                )
    spec = importlib.util.spec_from_file_location(
        'single_crystal_cli', ROOT / 'tools/checks/cli_projects.py'
    )
    checker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checker)
    assert name in checker.ci_projects(checker.registry(ROOT)), (
        'The production CLI selector must actually select each single-crystal project'
    )
    completed = subprocess.run(
        [sys.executable, str(ROOT / 'tools/checks/cli_projects.py'), '--project', name],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert completed.returncode == 0, (
        'Each single-crystal project must execute the real CLI fit and meet expected.json: '
        + completed.stdout
        + completed.stderr
    )
