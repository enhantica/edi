"""Resolve the explicit CI matrix before checking the declared runner contract."""

import re

RUNNERS = {
    'Linux': ['self-hosted', 'Linux', 'X64'],
    'macOS': ['self-hosted', 'macOS', 'ARM64'],
}

HOSTED = {
    'ubuntu-24.04': ['github-hosted', 'Linux', 'X64'],
    'macos-15': ['github-hosted', 'macOS', 'ARM64'],
}


def _declared_runner(selected):
    if isinstance(selected, str):
        assert selected in HOSTED, 'E01: hosted jobs use an exact declared standard runner'
        return HOSTED[selected]
    assert selected in RUNNERS.values(), 'E01: each job uses a declared OS and architecture'
    return selected


def self_hosted_runners(job):
    matrix = job.get('strategy', {}).get('matrix')
    selected = job.get('runs-on')
    if matrix is None:
        return [_declared_runner(selected)]
    assert isinstance(matrix, dict) and set(matrix) == {'include'}, (
        'E01: runner matrices use explicit include rows; unsupported expansion fails closed'
    )
    rows = matrix['include']
    assert isinstance(rows, list) and rows, 'E01: a runner matrix has concrete nonempty rows'
    assert isinstance(selected, str), 'E01: matrix runs-on uses a row binding'
    binding = re.fullmatch(r'\$\{\{\s*matrix\.([\w-]+)\s*\}\}', selected or '')
    assert binding, 'E01: runs-on must select the runner from each concrete matrix row'
    result = []
    for row in rows:
        assert isinstance(row, dict), 'E01: each runner row is a mapping'
        runner = _declared_runner(row.get(binding[1]))
        assert row.get('platform') in RUNNERS and runner[1:] == RUNNERS[row['platform']][1:], (
            'E01: each platform executes on its own OS and architecture'
        )
        result.append(runner)
    return result


def platform_job(jobs, area, platform):
    candidates = [
        job
        for key, job in jobs.items()
        if key in {area, area + '-macos'}
        if any(
            runner[1] == ('macOS' if platform == 'osx-arm64' else 'Linux')
            for runner in self_hosted_runners(job)
        )
    ]
    assert len(candidates) == 1, 'each native/core platform selects exactly one real workflow job'
    return candidates[0]
