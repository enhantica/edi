""": every executing CLI variant uses declared conditions and its old pins.

Audit real subprocess launches and the project bytes present at the launch boundary.
The numerical authority remains each committed expected.json (labelled regression pins).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
CLI = ROOT / 'docs/user/cli'
SEEDS = (
    'pd-neut-tof_si-sepd_start-2',
    'pd-neut-tof_si-sepd_start-5',
    'pd-neut-tof_ncaf-wish-2bank_start-3',
)
PROJECTS = [
    row['id']
    for row in yaml.safe_load((CLI / 'projects.yml').read_text())['projects']
    if row['executing'] or row['id'] in SEEDS
]
AUDITED = """
import json, pathlib, runpy, sys
log, runner, root, project_id = sys.argv[1:]
sys.argv = [runner, '--root', root, '--project', project_id]
def audit(event, arguments):
    if event != 'subprocess.Popen':
        return
    argv = arguments[1]
    if isinstance(argv, (list, tuple)) and 'fit' in argv:
        project = pathlib.Path(argv[argv.index('fit') + 1])
        entry = dict(argv=list(argv), analysis=(project / 'analysis/analysis.edi').read_text())
        with open(log, 'a') as stream:
            stream.write(json.dumps(entry) + '\\n')
sys.addaudithook(audit)
runpy.run_path(runner, run_name='__main__')
"""


# A transport-only control: visit the complete original manifest without fitting.
# The intentionally incomplete record CANNOT satisfy numerical pins. Real numerical
# agreement is proved separately for every unchanged pinned variant below.
TRANSPORT_AUDITED = AUDITED.replace(
    'sys.addaudithook(audit)',
    """import subprocess, types
real_run = subprocess.run
def transport(argv, **kwargs):
    if list(argv[:4]) != [sys.executable, '-m', 'edi', 'fit']:
        return real_run(argv, **kwargs)
    audit('subprocess.Popen', (None, argv))
    return types.SimpleNamespace(returncode=0, stdout='status=done\\n', stderr='')
subprocess.run = transport""",
)


def run_project(tmp_path, project_id, *, corrupt=False, variant_index=None, transport_only=False):
    target = tmp_path / 'docs/user/cli' / project_id
    shutil.copytree(CLI / project_id, target)
    expected_path = target / 'expected.json'
    expected = json.loads(expected_path.read_text())
    if variant_index is not None:
        units = []
        if 'quantities' in expected:
            units.append({'quantities': expected['quantities']})
        units.extend(
            {'variants': {name: block}} for name, block in expected.get('variants', {}).items()
        )
        if 'edi' in expected:
            units.append({'edi': expected['edi']})
        expected = {
            **{k: v for k, v in expected.items() if k not in {'quantities', 'variants', 'edi'}},
            **units[variant_index],
        }
        expected_path.write_text(json.dumps(expected))
    if corrupt:
        blocks = list(expected.get('variants', {}).values())
        assert len(blocks) > 1, ' escape control must reach a later non-default variant'
        blocks[-1]['quantities']['rwp']['value'] = 1e50
        expected_path.write_text(json.dumps(expected))
    (target.parent / 'projects.yml').write_text(
        yaml.safe_dump({'schema': 1, 'projects': [{'id': project_id, 'executing': True}]})
    )
    analysis_before = (target / 'project/analysis/analysis.edi').read_bytes()
    log = tmp_path / 'launches.jsonl'
    result = subprocess.run(
        [
            sys.executable,
            '-c',
            TRANSPORT_AUDITED if transport_only else AUDITED,
            str(log),
            str(ROOT / 'tools/checks/cli_projects.py'),
            str(tmp_path),
            project_id,
        ],
        cwd=ROOT,
        env={**os.environ, 'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1'},
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert log.is_file(), ' CLI runner must reach the child-fit boundary: ' + result.stderr
    calls = [json.loads(line) for line in log.read_text().splitlines()]
    assert (target / 'project/analysis/analysis.edi').read_bytes() == analysis_before, (
        ' per-variant conditions must be written into a disposable copy'
    )
    return result, calls, expected


def declared(text, field):
    values = [
        line.split(maxsplit=1)[1].strip().strip('"')
        for line in text.splitlines()
        if line.startswith(f'_minimizer.{field} ')
    ]
    assert len(values) == 1, (
        ' launched variant must contain exactly one declared minimizer condition'
    )
    return values[0]


def expected_descents(expected):
    return (
        (['default'] if 'quantities' in expected else [])
        + [name.replace('-', '_') for name in expected.get('variants', {})]
        + (['default'] if 'edi' in expected else [])
    )


VARIANTS = [
    (project_id, index)
    for project_id in PROJECTS
    for index, _ in enumerate(
        expected_descents(json.loads((CLI / project_id / 'expected.json').read_text()))
    )
]


@pytest.mark.parametrize(('project_id', 'variant_index'), VARIANTS)
def test_every_executing_project_runs_every_pinned_variant_from_project_data(
    tmp_path, project_id, variant_index
):
    result, calls, expected = run_project(tmp_path, project_id, variant_index=variant_index)
    assert result.returncode == 0, (
        ' every executing project must reproduce its committed regression pins: '
        + result.stdout
        + result.stderr
    )
    descents = expected_descents(expected)
    assert len(calls) == len(descents), (
        ' runner must execute all pinned variants, including a family without ladder'
    )
    call, selected = calls[0], descents[0]
    assert not set(call['argv']) & {
        '--descent',
        '--list-descents',
        '--chi-square-tolerance',
        '--max-iter',
    }, ' runner must pass conditions in analysis.edi, never as fit CLI switches'
    if selected != 'default':
        assert declared(call['analysis'], 'descent') == selected, (
            ' each launched copy must declare its own pinned variant descent'
        )
    if project_id in SEEDS:
        assert float(declared(call['analysis'], 'chi_square_tolerance')) == 1e-4, (
            ' switched-on seeds must run at their originally pinned tolerance'
        )


@pytest.mark.parametrize('project_id', PROJECTS)
def test_complete_manifest_dispatches_every_declared_variant(tmp_path, project_id):
    result, calls, expected = run_project(tmp_path, project_id, transport_only=True)
    assert result.returncode != 0, (
        ' transport-only records must never masquerade as numerical pin evidence'
    )
    descents = expected_descents(expected)
    assert len(calls) == len(descents), (
        ' complete-manifest traversal must reach every pinned variant'
    )
    for call, selected in zip(calls, descents, strict=True):
        assert not set(call['argv']) & {
            '--descent',
            '--list-descents',
            '--chi-square-tolerance',
            '--max-iter',
        }, ' complete-manifest traversal must carry all conditions in project data'
        if selected != 'default':
            assert declared(call['analysis'], 'descent') == selected, (
                ' complete-manifest traversal must declare each selected descent'
            )
        if project_id in SEEDS:
            assert float(declared(call['analysis'], 'chi_square_tolerance')) == 1e-4, (
                ' complete-manifest traversal must retain the seed tolerance'
            )


def test_later_variant_corruption_is_not_hidden_by_an_earlier_pass(tmp_path):
    result, calls, expected = run_project(tmp_path, 'pd-neut-cwl_cosio-d20_start-1', corrupt=True)
    assert result.returncode != 0, ' runner must reject drift in a later non-default variant'
    final_variant = next(reversed(expected['variants']))
    assert (
        final_variant in result.stdout + result.stderr and 'rwp' in result.stdout + result.stderr
    ), ' later-variant refusal must name the failing variant and quantity'
    assert len(calls) == len(expected['variants']), (
        ' corruption exercise must actually reach the last variant'
    )
