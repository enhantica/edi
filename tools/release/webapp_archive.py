# SPDX-License-Identifier: BSD-3-Clause
"""Archive the web app the Pages workflow built from the release commit, for the release.

Run as ``python tools/release/webapp_archive.py --repo <repo> --publication publication``.
"""

import argparse
import json
import operator
import subprocess
import tempfile
import zipfile
from pathlib import Path

from promote import extract

ARTIFACT = 'pages-webapp'


def find_artifact(repo: str, commit: str) -> int:
    """The newest retained web app artifact built on main at this commit."""
    pages = json.loads(
        subprocess.check_output([
            'gh',
            'api',
            '--paginate',
            '--slurp',
            f'repos/{repo}/actions/artifacts?name={ARTIFACT}&per_page=100',
        ])
    )
    matches = [
        item
        for page in pages
        for item in page['artifacts']
        if not item['expired']
        and item['workflow_run']['head_sha'] == commit
        and item['workflow_run']['head_branch'] == 'main'
    ]
    if not matches:
        raise RuntimeError(f'No web app was built on main at {commit}; let Pages build it first')
    return max(matches, key=operator.itemgetter('created_at'))['id']


def write_archive(site: Path, archive: Path) -> None:
    """The site as a zip with fixed times, so a retried publication writes the same bytes."""
    files = sorted(path for path in site.rglob('*') if path.is_file())
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED) as target:
        for path in files:
            member = zipfile.ZipInfo(
                'webapp/' + path.relative_to(site).as_posix(), (1980, 1, 1, 0, 0, 0)
            )
            member.compress_type = zipfile.ZIP_DEFLATED
            member.external_attr = 0o644 << 16
            target.writestr(member, path.read_bytes())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--repo', required=True)
    parser.add_argument('--publication', required=True, type=Path)
    args = parser.parse_args()
    release = json.loads((args.publication / 'release.json').read_text(encoding='utf-8'))
    artifact = find_artifact(args.repo, release['commit'])
    with tempfile.TemporaryDirectory() as scratch:
        download = Path(scratch) / 'webapp.zip'
        with download.open('wb') as stream:
            subprocess.run(
                ['gh', 'api', f'repos/{args.repo}/actions/artifacts/{artifact}/zip'],
                stdout=stream,
                check=True,
            )
        extract(download, Path(scratch) / 'site')
        if not (Path(scratch) / 'site/index.html').is_file():
            raise RuntimeError('The web app artifact has no start page')
        name = f'EasyDiffraction-{release["version"]}-webapp.zip'
        write_archive(Path(scratch) / 'site', args.publication / 'assets' / name)
    print(name)


if __name__ == '__main__':
    main()
