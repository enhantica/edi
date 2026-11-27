# SPDX-License-Identifier: BSD-3-Clause
"""The producer record of a packed crysta SDK and the line each SDK job prints (edi ADR-0083).

    python3 tools/ci/crysta_sdk_record.py write --archives DIR --sha SHA --platform P --recipe R
        right after `crysta_sdk.py surface`, whose archive is the one every consumer takes: writes
        DIR/crysta-sdk-<P>.json, which the cache and the artifact keep beside the archive
    python3 tools/ci/crysta_sdk_record.py show --archives DIR --sha SHA --platform P --recipe R
        in every SDK job, the archive built or restored: checks the record against the archive and
        its manifest, prints
        crysta-ci sdk platform=<P> record=<the record, compact> run=<run id>/<attempt>
        and refuses a record whose tests are not all run and passed

The record holds sha, tree, platform, archive_sha256, cpp_tests and corpus_cases (each
`<passed>/<total>` or `untested`), recipe, and the run, attempt and job that built the archive.
`write` takes the tree from the manifest and checks it against the crysta checkout ($CRYSTA_SRC).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tarfile
from pathlib import Path

from crysta_sdk import MANIFEST, PLATFORMS, archive_name, sha256
from crysta_subject import COMMIT, NUMBER, RefusedError, run_of

DIGEST = re.compile(r'[0-9a-f]{64}')
COUNT = re.compile(r'(0|[1-9][0-9]*)/([1-9][0-9]*)|untested')
KEYS = (
    'sha',
    'tree',
    'platform',
    'archive_sha256',
    'cpp_tests',
    'corpus_cases',
    'recipe',
    'run',
    'attempt',
    'job',
)
# The name GitHub gives the SDK job: every caller of crysta-sdk.yml calls it as `crysta-sdk`.
JOB = 'crysta-sdk / crysta SDK · {platform}'


def record_path(archives: Path, platform: str) -> Path:
    return archives / f'crysta-sdk-{platform}.json'


def archive_of(archives: Path, sha: str, platform: str) -> tuple[Path, str]:
    """The archive and its digest, which its checksum file has to state."""
    archive = archives / archive_name(sha, platform)
    digest = sha256(archive)
    checksum = archive.with_name(archive.name + '.sha256').read_text(encoding='ascii')
    if checksum != f'{digest}  {archive.name}\n':
        raise RefusedError(f'the checksum file does not state the digest of {archive.name}')
    return archive, digest


def manifest_of(archive: Path, sha: str, platform: str) -> dict:
    """The archive's manifest, which has to name the commit and platform asked for."""
    with tarfile.open(archive) as held:
        member = held.extractfile(held.getmember(MANIFEST))
        if member is None:
            raise RefusedError('the SDK manifest is not a file')
        manifest = json.loads(member.read())
    if manifest.get('source_sha') != sha or manifest.get('platform') != platform:
        raise RefusedError(
            f'the SDK is of {manifest.get("source_sha")!r} on {manifest.get("platform")!r}, '
            f'not {sha} on {platform}'
        )
    if not COMMIT.fullmatch(str(manifest.get('source_tree'))):
        raise RefusedError('the SDK manifest names no tree')
    return manifest


def count(manifest: dict, tier: str) -> str:
    """A tier's result as `<passed>/<total>`, or `untested`."""
    held = (manifest.get('tested') or {}).get(tier) or {}
    if held.get('untested') is True:
        return 'untested'
    passed, total = held.get('passed'), held.get('total')
    if type(passed) is not int or type(total) is not int or not 0 <= passed <= total or total < 1:
        raise RefusedError(f'the SDK manifest records no {tier} result')
    return f'{passed}/{total}'


def asked(args: argparse.Namespace) -> None:
    """Refuse a commit or recipe that is not a full id."""
    if not COMMIT.fullmatch(args.sha) or not DIGEST.fullmatch(args.recipe):
        raise RefusedError('the commit or the recipe is not a full id')


def write(args: argparse.Namespace) -> Path:
    """Write the record of the archive as it is now."""
    asked(args)
    archive, digest = archive_of(args.archives, args.sha, args.platform)
    manifest = manifest_of(archive, args.sha, args.platform)
    checkout = os.environ.get('CRYSTA_SRC')
    if not checkout:
        raise RefusedError('no crysta checkout: CRYSTA_SRC is unset')
    tree = subprocess.run(
        ['git', '-C', checkout, 'rev-parse', '--verify', f'{args.sha}^{{tree}}'],
        capture_output=True,
        text=True,
        check=False,
    )
    if tree.returncode or tree.stdout.strip() != manifest['source_tree']:
        raise RefusedError('the SDK manifest names another tree than the checkout')
    run, attempt = run_of().split('/')
    record = {
        'sha': args.sha,
        'tree': manifest['source_tree'],
        'platform': args.platform,
        'archive_sha256': digest,
        'cpp_tests': count(manifest, 'cpp_tier'),
        'corpus_cases': count(manifest, 'corpus'),
        'recipe': args.recipe,
        'run': int(run),
        'attempt': int(attempt),
        'job': JOB.format(platform=args.platform),
    }
    path = record_path(args.archives, args.platform)
    path.write_text(json.dumps(record, separators=(',', ':')) + '\n', encoding='ascii')
    return path


def checked(args: argparse.Namespace) -> dict:
    """The record, if it is the one of this archive, commit, platform and recipe."""
    asked(args)
    record = json.loads(record_path(args.archives, args.platform).read_bytes())
    if not isinstance(record, dict) or tuple(record) != KEYS:
        raise RefusedError(f'the record does not hold exactly {", ".join(KEYS)}')
    archive, digest = archive_of(args.archives, args.sha, args.platform)
    manifest = manifest_of(archive, args.sha, args.platform)
    expected = {
        'sha': args.sha,
        'tree': manifest['source_tree'],
        'platform': args.platform,
        'archive_sha256': digest,
        'cpp_tests': count(manifest, 'cpp_tier'),
        'corpus_cases': count(manifest, 'corpus'),
        'recipe': args.recipe,
    }
    if differing := [key for key, value in expected.items() if record[key] != value]:
        raise RefusedError(f'the record differs from the archive in {", ".join(differing)}')
    producer = (type(record['run']), type(record['attempt']), str(record['job']))
    if producer != (int, int, JOB.format(platform=args.platform)) or not all(
        NUMBER.fullmatch(str(record[key])) for key in ('run', 'attempt')
    ):
        raise RefusedError('the record names no producing run, attempt and job')
    return record


def show(args: argparse.Namespace) -> list[str]:
    """Print the record's line; what keeps the SDK from counting, after it."""
    record = checked(args)
    compact = json.dumps(record, separators=(',', ':'))
    print(f'crysta-ci sdk platform={args.platform} record={compact} run={run_of()}')
    return [
        f'{key} is {record[key]}: not every test ran and passed'
        for key in ('cpp_tests', 'corpus_cases')
        if (found := COUNT.fullmatch(record[key])) is None
        or found[0] == 'untested'
        or found[1] != found[2]
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('write', 'show'))
    parser.add_argument('--archives', required=True, type=Path)
    parser.add_argument('--sha', required=True)
    parser.add_argument('--platform', required=True, choices=PLATFORMS)
    parser.add_argument('--recipe', required=True)
    args = parser.parse_args()
    try:
        if args.command == 'write':
            print(f'crysta-sdk-record: wrote {write(args).name}')
            return 0
        problems = show(args)
    except (RefusedError, OSError, ValueError, KeyError, tarfile.TarError) as refusal:
        print(f'crysta-sdk-record: REFUSED: {refusal}', file=sys.stderr)
        return 1
    for problem in problems:
        print(f'crysta-sdk-record: REFUSED: {problem}', file=sys.stderr)
    return 1 if problems else 0


if __name__ == '__main__':
    raise SystemExit(main())
