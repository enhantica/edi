# SPDX-License-Identifier: BSD-3-Clause
"""Find a completed native producer at HEAD for documentation, without waiting for CI."""

from __future__ import annotations

import json
import operator
import os
import subprocess
from pathlib import Path
from urllib.parse import urlencode


def api(path: str) -> list[dict]:
    """Read every page; an API failure is not proof that no artifact exists."""
    result = subprocess.run(
        ['gh', 'api', '--paginate', '--slurp', path], check=True, capture_output=True, text=True
    )
    return json.loads(result.stdout)


def find(repository: str, sha: str, platform: str) -> str:
    """Return the newest completed matching producer, or empty when none has an archive."""
    runs = []
    query = urlencode({'head_sha': sha, 'status': 'completed', 'per_page': 100})
    for workflow in ('ci.yml', 'installers.yml'):
        for page in api(f'repos/{repository}/actions/workflows/{workflow}/runs?{query}'):
            runs.extend(
                run
                for run in page['workflow_runs']
                if run['head_sha'] == sha
                and run['status'] == 'completed'
                and run['head_repository']['full_name'] == repository
            )
    for run in sorted(runs, key=operator.itemgetter('id'), reverse=True):
        for page in api(f'repos/{repository}/actions/runs/{run["id"]}/artifacts?per_page=100'):
            for artifact in page['artifacts']:
                if artifact['name'] == f'edi-native-{platform}' and not artifact['expired']:
                    return str(run['id'])
    return ''


def main() -> None:
    """Select only the checked-out commit and publish the optional producer run to Actions."""
    sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    run = find(os.environ['GITHUB_REPOSITORY'], sha, 'linux-64')
    with Path(os.environ['GITHUB_OUTPUT']).open('a', encoding='utf-8') as output:
        output.write(f'run-id={run}\n')
    print(
        f'Native documentation build: reuse run {run}'
        if run
        else 'No matching native artifact; build locally'
    )


if __name__ == '__main__':
    main()
