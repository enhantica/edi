""": every executing CLI variant uses declared conditions and its old pins.

Audit real subprocess launches and the project bytes present at the launch boundary.
The numerical authority remains each committed expected.json and its reference/pin labels.
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
    if isinstance(argv, (list, tuple)) and len(argv) > 3 and argv[3] in {'fit', 'calc'}:
        project = pathlib.Path(argv[4])
        files = sorted((project / 'experiments').glob('*.edi'))
        entry = dict(argv=list(argv), analysis=(project / 'analysis/analysis.edi').read_text(),
                     experiments={p.name: p.read_text() for p in files})
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
    if list(argv[:3]) != [sys.executable, '-m', 'edi'] or argv[3] not in {'fit', 'calc'}:
        return real_run(argv, **kwargs)
    audit('subprocess.Popen', (None, argv))
    return types.SimpleNamespace(returncode=0, stdout='status=done\\n', stderr='')
subprocess.run = transport""",
)


def run_project(
    tmp_path,
    project_id,
    *,
    corrupt=False,
    corrupt_status=False,
    variant_index=None,
    transport_only=False,
):
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
        if 'calc' in expected:
            units.append({'calc': expected['calc']})
        expected = {
            **{
                k: v
                for k, v in expected.items()
                if k not in {'quantities', 'variants', 'edi', 'calc'}
            },
            **units[variant_index],
        }
        expected_path.write_text(json.dumps(expected))
    if corrupt_status:
        assert expected['variants']['asymmetry-off']['status'] == 'max_iter', (
            'The status control must begin with the decided LATP iteration-limit outcome'
        )
        expected['variants']['asymmetry-off']['status'] = 'done'
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


def expected_labels(expected):
    return (
        (['default'] if 'quantities' in expected else [])
        + list(expected.get('variants', {}))
        + (['edi'] if 'edi' in expected else [])
        + (['calc'] if 'calc' in expected else [])
    )


def assert_launched_unit(call, selected, expected, project_id):
    assert call['argv'][3] == ('calc' if selected == 'calc' else 'fit'), (
        'Each declared unit must launch calculation or fitting according to its record'
    )
    assert not set(call['argv']) & {
        '--descent',
        '--list-descents',
        '--chi-square-tolerance',
        '--max-iter',
    }, 'Every unit must carry its conditions in project data rather than CLI switches'
    if selected not in {'default', 'edi', 'calc', 'asymmetry-off'}:
        assert declared(call['analysis'], 'descent') == selected.replace('-', '_'), (
            'Each descent variant must declare its own registered descent'
        )
    original = {
        path.name: path.read_text()
        for path in sorted((CLI / project_id / 'project/experiments').glob('*.edi'))
    }
    if selected == 'asymmetry-off':
        assert call['experiments'].keys() == original.keys(), (
            'A project variant must retain every original experiment file'
        )
        coefficients = {f'_peak.asym_beba_{item}' for item in ('a0', 'b0', 'a1', 'b1')}
        found = 0
        for name, text in original.items():
            before = text.splitlines(keepends=True)
            after = call['experiments'][name].splitlines(keepends=True)
            assert len(after) == len(before), 'Asymmetry-off retains every experiment line'
            for source, launched in zip(before, after, strict=True):
                fields = source.split()
                if fields and fields[0] in coefficients:
                    found += 1
                    assert launched.split() == [fields[0], '0'], (
                        'Declared BeBa coefficients must be fixed at zero, without a free flag'
                    )
                else:
                    assert launched == source, (
                        'Asymmetry-off retains every other experiment line byte for byte'
                    )
        assert found > 0, 'The asymmetry-off control must reach declared BeBa coefficients'
        assert [
            line for line in call['analysis'].splitlines() if line.startswith('_minimizer.')
        ] == [
            line
            for line in (CLI / project_id / 'project/analysis/analysis.edi')
            .read_text()
            .splitlines()
            if line.startswith('_minimizer.')
        ], 'A project variant retains all minimizer conditions, including implicit defaults'
    else:
        assert call['experiments'] == original, (
            'A descent, default or calculation unit must preserve every experiment byte'
        )
    if expected.get('template') is True:
        assert '_fitting_mode.type single' in call['analysis'].splitlines(), (
            'A declared scan template comparison must launch a single fit'
        )
        assert not any(
            line.startswith('_sequential_fit.') for line in call['analysis'].splitlines()
        ), 'A template comparison must remove sequential traversal conditions from its copy'


VARIANTS = [
    (project_id, index)
    for project_id in PROJECTS
    for index, _ in enumerate(
        expected_labels(json.loads((CLI / project_id / 'expected.json').read_text()))
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
    descents = expected_labels(expected)
    assert len(calls) == len(descents), (
        ' runner must execute all pinned variants, including a family without ladder'
    )
    call, selected = calls[0], descents[0]
    assert_launched_unit(call, selected, expected, project_id)
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
    descents = expected_labels(expected)
    assert len(calls) == len(descents), (
        ' complete-manifest traversal must reach every pinned variant'
    )
    for call, selected in zip(calls, descents, strict=True):
        assert_launched_unit(call, selected, expected, project_id)
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


def test_project_variant_terminal_status_is_enforced(tmp_path):
    result, calls, expected = run_project(
        tmp_path, 'pd-xray-cwl_latp-bm01_scan', variant_index=1, corrupt_status=True
    )
    assert result.returncode != 0, (
        'A numerically agreeing fit must still refuse the wrong terminal status'
    )
    assert "asymmetry-off: status='max_iter', expected done" in result.stdout + result.stderr, (
        'The decided iteration-limit fit cannot masquerade as convergence'
    )
    assert len(calls) == 1, 'The status control must reach the real asymmetry-off template fit'
    assert_launched_unit(calls[0], 'asymmetry-off', expected, 'pd-xray-cwl_latp-bm01_scan')
