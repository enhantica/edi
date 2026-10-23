"""Apply the bounded owner event changes to independently captured CI inputs."""

import yaml

POLICY = '2026-10-19 owner records 682968ba1/7552dbd4b; packet items 6 and 8'


def apply_event_policy(snapshot):
    if snapshot['repo'] != 'edi':
        return snapshot
    workflow = yaml.safe_load(snapshot['files']['.github/workflows/ci.yml'])
    jobs = workflow['jobs']
    for name in ('system', 'app-wasm'):
        if name in jobs:
            jobs[name]['if'] = jobs[name]['if'].replace(
                'github.event.pull_request.head.repo.fork == false',
                "github.event_name != 'pull_request'",
            )
    if 'system-time' in jobs:
        jobs['system-time']['if'] = jobs['system-time']['if'].replace(
            "github.event_name == 'pull_request'", "github.event_name == 'push'"
        )
        for step in jobs['system-time']['steps']:
            if 'run' in step:
                step['run'] = step['run'].replace(
                    '${{ github.event.pull_request.head.sha }}', '${{ github.sha }}'
                )
    timed = {
        'Tests (declared group, C++ unit, unit and integration)',
        'Tests (declared group, system part)',
        "The app group's Python tests (tests/integration/app)",
        'Execute every notebook',
        'Execute the notebooks',
    }
    for job in jobs.values():
        for step in job.get('steps', []):
            title = step.get('name')
            if title == 'The two-thread witness (ThreadSanitizer)':
                step['if'] = "matrix.platform == 'Linux' && github.event_name != 'pull_request'"
            if title == "The app group's Python tests (tests/integration/app)":
                step['if'] = "github.event_name != 'pull_request'"
            if title in timed or step.get('run') in {
                'pixi run notebook-tests',
                'pixi run notebook-exec-ci',
            }:
                step.setdefault('env', {})['PYTEST_ADDOPTS'] = '--durations=0 --durations-min=1'
            if title == 'Tests (declared group, system part)':
                step['env']['EDI_RUN_NIGHTLY_ONLY'] = (
                    "${{ github.event_name == 'schedule' || "
                    "(github.event_name == 'workflow_dispatch' && inputs.core_only != true) }}"
                )
    snapshot['files']['.github/workflows/ci.yml'] = yaml.safe_dump(workflow, sort_keys=False)
    snapshot['event_policy'] = POLICY
    return snapshot
