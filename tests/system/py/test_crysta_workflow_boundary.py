"""Public workflow checks for the crysta job and SDK subject."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
WORKFLOWS = ROOT / '.github/workflows'
SDK_CALL = './.github/workflows/crysta-sdk.yml'

# The accepted verification closure covers the harness and both installer manifests.
CRYSTA_INPUTS = {
    '.github',
    'tools/ci',
    'pixi.toml',
    'pixi.lock',
    'pyproject.toml',
    'tools/installer/pixi.toml',
    'tools/installer/pixi.lock',
    'cmake',
    'CMakeLists.txt',
    'conftest.py',
    'tools/testing',
    'tools/checks/python_surface_superset.py',
    'tests/conftest.py',
    'tests/model_calculation.py',
    'tests/fit-sites.yml',
    'tests/system/py/test_e02_fullprof_parity.py',
    'tests/system/py/test_c06_t6_fitting_corpus.py',
    'tests/fixtures',
    'lib/edi',
    'data',
}


def _workflow(name):
    path = WORKFLOWS / name
    assert path.is_file(), f'{name} must exist for the crysta job boundary'
    return yaml.load(path.read_text(encoding='utf-8'), Loader=yaml.BaseLoader)


def test_sdk_producer_is_called_with_one_explicit_crysta_subject():
    sdk = _workflow('crysta-sdk.yml')['on']['workflow_call']
    subject = sdk.get('inputs', {}).get('crysta-sha', {})
    assert subject.get('required') == 'true' and subject.get('type') == 'string', (
        'The SDK workflow requires the caller to supply its crysta commit'
    )
    for publisher in ('ci.yml', 'pages.yml', 'installers.yml', 'coverage.yml'):
        jobs = _workflow(publisher)['jobs']
        dedicated = [job for job in jobs.values() if job.get('uses') == SDK_CALL]
        assert len(dedicated) == 1, f'{publisher} has one explicit SDK producer call'
        call = dedicated[0]
        assert call.get('with', {}).get('crysta-sha') and call.get('needs'), (
            f'{publisher} must pass the commit from its prerequisite pin job to the SDK producer'
        )


def test_crysta_job_group_receives_subject_and_reports_it_in_each_job():
    workflow = _workflow('crysta.yml')
    subject = workflow['on']['workflow_call'].get('inputs', {}).get('crysta-sha', {})
    assert subject.get('required') == 'true' and subject.get('type') == 'string', (
        'The reusable crysta gate cannot choose a different implicit pin'
    )
    tests = [
        job
        for job in workflow['jobs'].values()
        if 'runs-on' in job and not job.get('name', '').startswith('crysta SDK')
    ]
    assert tests, 'The reusable workflow must execute the migrated crysta gates'
    for job in tests:
        steps = job.get('steps', [])
        named = [n for n, s in enumerate(steps) if s.get('name') == 'The crysta commit under test']
        assert len(named) == 1, f'Each crysta job has one subject witness step: {job.get("name")}'
        gates = [n for n, step in enumerate(steps) if 'pixi run' in step.get('run', '')]
        assert not gates or named[0] < min(gates), (
            f'{job.get("name")} emits the subject before executing a pixi gate'
        )


def test_skip_input_covers_files_the_edi_verification_reads():
    path = ROOT / 'tools/ci/crysta-inputs.txt'
    assert path.is_file(), 'The skip boundary needs a committed closed verification input list'
    entries = [
        line.strip()
        for line in path.read_text(encoding='utf-8').splitlines()
        if line.strip() and not line.lstrip().startswith('#')
    ]
    assert len(entries) == len(set(entries)) and set(entries) == CRYSTA_INPUTS, (
        'The skip list must preserve the reviewed verification and workflow inputs exactly'
    )


def test_diagnostic_dispatch_is_a_distinct_non_pin_workflow():
    workflow = _workflow('crysta-diagnostic.yml')
    trigger = workflow['on']
    assert set(trigger) == {'workflow_dispatch'}, (
        'The diagnostic crysta workflow runs manually outside pull request and main evidence'
    )
    assert {'crysta-sha', 'set'} <= set(trigger['workflow_dispatch']['inputs']), (
        'Dispatch accepts a subject distinct from the pin and the requested gate set'
    )
    calls = [
        spec
        for spec in workflow['jobs'].values()
        if spec.get('uses') in {SDK_CALL, './.github/workflows/crysta.yml'}
    ]
    assert calls and all(
        'inputs.crysta-sha' in spec.get('with', {}).get('crysta-sha', '') for spec in calls
    ), 'Each diagnostic workflow call forwards the manually supplied commit'
