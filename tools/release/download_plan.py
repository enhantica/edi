# SPDX-License-Identifier: BSD-3-Clause
"""Download prepared release inputs only from a successful matching source run."""

import argparse
import io
import json
import re
import stat
import subprocess
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[2]


def select_plan(run: dict, artifacts: list[dict], commit: str) -> int:
    """Bind a nonexpired preparation artifact to its successful workflow and exact source."""
    if (
        run.get('path') != '.github/workflows/release-plan.yml'
        or run.get('status') != 'completed'
        or run.get('conclusion') != 'success'
        or run.get('head_sha') != commit
        or run.get('event') != 'workflow_dispatch'
    ):
        raise ValueError('Release preparation must succeed at this exact source commit')
    name = f'release-plan-{run["run_attempt"]}'
    matches = [item for item in artifacts if item['name'] == name and not item['expired']]
    if len(matches) != 1 or matches[0]['size_in_bytes'] > 4 * 1024 * 1024:
        raise ValueError('Expected one bounded release-plan artifact for the successful attempt')
    return matches[0]['id']


def unpack_plan(content: bytes, output: Path) -> None:
    """Extract only bounded regular release metadata into a fresh directory."""
    expected = {'plan.json', 'release.json', 'release-history.json', 'notes.md'}
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        members = archive.infolist()
        if {item.filename for item in members} != expected or len(members) != len(expected):
            raise ValueError('Prepared artifact has unexpected or duplicate members')
        for item in members:
            mode = item.external_attr >> 16
            if (
                PurePosixPath(item.filename).name != item.filename
                or item.file_size > 1024 * 1024
                or (stat.S_IFMT(mode) not in {0, stat.S_IFREG})
            ):
                raise ValueError('Prepared artifact members must be bounded regular files')
        output.mkdir(parents=True)
        for item in members:
            (output / item.filename).write_bytes(archive.read(item))


def api(repo: str, path: str, *, binary: bool = False) -> bytes:
    """Read immutable workflow evidence or one artifact through the GitHub CLI."""
    command = ['gh', 'api', f'repos/{repo}/{path}']
    if binary:
        command += ['-H', 'Accept: application/vnd.github+json']
    return subprocess.check_output(command)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', required=True)
    parser.add_argument('--run', required=True, type=int)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', args.repo) or args.run <= 0:
        raise ValueError('Expected a repository and positive workflow run ID')
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    run = json.loads(api(args.repo, f'actions/runs/{args.run}'))
    artifacts = json.loads(api(args.repo, f'actions/runs/{args.run}/artifacts?per_page=100'))
    if artifacts['total_count'] > len(artifacts['artifacts']):
        raise ValueError('Release preparation has an unexpected artifact count')
    identity = select_plan(run, artifacts['artifacts'], commit)
    unpack_plan(api(args.repo, f'actions/artifacts/{identity}/zip', binary=True), args.output)
    print(f'Prepared inputs from run {args.run}, artifact {identity}, source {commit}')


if __name__ == '__main__':
    main()
