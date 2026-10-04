"""Saved CLI constraints and the executing external-reference notebook."""

import ast
import re
import runpy
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
MATERIALIZE = runpy.run_path(str(ROOT / 'tests/fixtures/constraint_expressions/project.py'))[
    'materialize'
]


@pytest.mark.parametrize(
    'case', ['pd-neut-cwl_cosio-d20_scan-3f', 'pd-neut-cwl_cosio-d20_scan-324f']
)
def test_cosio_scan_projects_restore_the_constraint_and_execute(case):
    folder = ROOT / 'docs/user/cli' / case / 'project'
    analysis = (folder / 'analysis/analysis.edi').read_text()
    assert '_alias.parameter_unique_name' in analysis, (
        'each CoSiO scan must declare both Biso aliases'
    )
    assert re.search(r'biso_Co2\s*=\s*biso_Co1', analysis), (
        'each CoSiO scan must restore the removed equality'
    )
    assert '.atom_site.Co1.adp_iso' in analysis and '.atom_site.Co2.adp_iso' in analysis, (
        'the tie must target both actual CoSiO sites'
    )
    registry = (ROOT / 'docs/user/cli/projects.yml').read_text()
    payload = yaml.safe_load(registry)
    rows = payload.get('projects', payload) if isinstance(payload, dict) else payload
    assert any(row.get('id') == case and row.get('executing') is True for row in rows), (
        'both restored scan projects must remain in the executing registry'
    )
    atom_file = next((folder / 'structures').glob('*.edi'))
    co1 = next(line for line in atom_file.read_text().splitlines() if line.startswith('Co1 '))
    assert '(' in co1.split()[-1], 'restoring the tie must leave the Co1 Biso leader free'


def test_tied_biso_notebook_executes_its_fullprof_comparison_and_fit():
    page = ROOT / 'docs/dev/verification/pd-neut-cwl_cosio-d20_biso-tied.py'
    assert page.is_file(), 'the tied-Biso verification notebook must be delivered'
    tree = ast.parse(page.read_text())
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
    names = [ast.unparse(call.func) for call in calls]
    assert any(name.endswith('assert_patterns_agree') for name in names), (
        'the page must compare the fixed twin with its independent FullProf profile'
    )
    assert any(name.endswith('constraints.create') for name in names), (
        'the page must declare the live constraint through the public API'
    )
    assert any(name.endswith('.fit') for name in names), 'the page must execute a constrained fit'
    assert '0.67350078' in page.read_text(), (
        'the page must retain the independently fitted FullProf Biso reference'
    )
    assert list(
        (ROOT / 'knowledge/verification/fullprof/pd-neut-cwl_cosio-d20_biso-tied').glob('*.prf')
    ), 'the notebook must consume a committed FullProf profile'
    assert page.stem in (ROOT / 'docs/dev/verification/index.md').read_text(), (
        'the notebook must remain in the verification collection'
    )


def test_cli_warns_and_ignores_a_loaded_dependent_free_flag(tmp_path):
    directory = MATERIALIZE(
        tmp_path / 'project',
        [('a', 'phase.atom_site.A.adp_iso'), ('b', 'phase.atom_site.B.adp_iso')],
        ['b = 2*a + 1'],
        dependent_free=True,
    )
    result = subprocess.run(
        [sys.executable, '-m', 'edi', 'calc', str(directory), '--verbosity', 'compact'],
        text=True,
        capture_output=True,
        check=False,
        timeout=20,
    )
    assert result.returncode == 0, (
        'a dependent free bracket must not prevent CLI calculation: ' + result.stderr
    )
    assert 'crysta.domain.dependent_free_ignored' in result.stderr, (
        'the CLI must forward the structured dependent-free warning'
    )
    assert '(1)' not in (directory / 'structures/phase.edi').read_text(), (
        'the CLI must not invent an uncertainty for a dependent'
    )


@pytest.mark.parametrize('expression', ['b = a.__class__', 'b = 1/0'])
def test_cli_refuses_an_invalid_loaded_relation(tmp_path, expression):
    directory = MATERIALIZE(
        tmp_path / 'project',
        [('a', 'phase.atom_site.A.adp_iso'), ('b', 'phase.atom_site.B.adp_iso')],
        [expression],
    )
    result = subprocess.run(
        [sys.executable, '-m', 'edi', 'calc', str(directory), '--verbosity', 'compact'],
        text=True,
        capture_output=True,
        check=False,
        timeout=20,
    )
    assert result.returncode != 0, 'the CLI must never calculate an invalid declared relation'
    assert 'crysta.domain.constraint_' in result.stderr, (
        'the CLI refusal must preserve the engine diagnostic code'
    )
