# SPDX-License-Identifier: BSD-3-Clause
"""Make the public snapshot: one fresh commit of a scrubbed edi `main`.

    python tools/public-release/snapshot.py --source LOCAL_GIT_REPO --output NEW_LOCAL_PATH
        [--ref main] [--message TEXT] [--skip-hidden]

The source repository is only read: its `--ref` (default `main`) is exported with `git archive`,
so no file, ref or index of it changes. The export is scrubbed (`scrub.py`: the whole tree, or with
`--skip-hidden` all but the hidden test tiers, which then stay as the source has them), every
source file is given its SPDX identifier (`spdx.py`), the public workflows replace the private
ones (`apply_preparation`), and the result is committed as the single
commit of a new repository at `--output`, which must not exist yet. The scan (`scan.py`) then reads
the new tree, archive members included: a credential finding, an archive member carrying a
personal or run path, a private citation or a process reference outside a test name, or an archive
it cannot read fails the snapshot (exit 1), and the residue of the scrub's classes is reported for
review. Nothing is pushed: the snapshot is local, and publishing it is a
separate, reviewed step.

Run again on a newer `main`, it yields the newer content scrubbed the same way, so the delta to
review is only what changed in between.
"""

from __future__ import annotations

import argparse
import io
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import scan  # the sibling modules, importable from any working directory
import scrub
import spdx


def _git(*args: str, cwd: Path) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(['git', '-C', str(cwd), *args], capture_output=True, check=True)


def export(source: Path, ref: str, output: Path) -> str:
    """Write `ref`'s tree into `output` without touching `source`; return the exported commit."""
    commit = _git('rev-parse', '--verify', f'{ref}^{{commit}}', cwd=source).stdout.decode().strip()
    archive = _git('archive', '--format=tar', commit, cwd=source).stdout
    output.mkdir(parents=True)
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        tar.extractall(output, filter='data')
    return commit


PREPARED_WORKFLOWS = Path('tools/public-release/github/workflows')


def apply_preparation(output: Path) -> list[str]:
    """Swap in the public repository's workflows; return the workflow files the snapshot carries.

    The source keeps its private CI until the cutover; its public workflows wait under
    `tools/public-release/github/workflows/` and replace `.github/workflows/` in the snapshot.
    """
    prepared = output / PREPARED_WORKFLOWS
    if not prepared.is_dir():
        return []
    workflows = output / '.github' / 'workflows'
    for old in workflows.glob('*.y*ml'):
        old.unlink()
    workflows.mkdir(parents=True, exist_ok=True)
    for new in sorted(prepared.glob('*.y*ml')):
        (workflows / new.name).write_bytes(new.read_bytes())
    shutil.rmtree(output / PREPARED_WORKFLOWS.parent)
    return sorted(p.name for p in workflows.glob('*.y*ml'))


def commit_tree(output: Path, message: str) -> str:
    """Make `output` a repository whose one commit holds the whole tree; return that commit."""
    _git('init', '--quiet', '--initial-branch=main', cwd=output)
    _git('add', '--all', cwd=output)
    spdx_main = ['--tree', str(output)]
    if spdx.main(spdx_main) != 0:
        raise SystemExit('snapshot: the SPDX pass failed')
    _git('add', '--all', cwd=output)
    named = subprocess.run(
        ['git', '-C', str(output), 'config', 'user.name'], capture_output=True, check=False
    )
    identity = (
        [] if named.stdout.strip() else ['-c', 'user.name=edi', '-c', 'user.email=edi@localhost']
    )
    subprocess.run(
        ['git', *identity, '-C', str(output), 'commit', '--quiet', '--message', message],
        check=True,
    )
    return _git('rev-parse', 'HEAD', cwd=output).stdout.decode().strip()


def main(argv: list[str] | None = None) -> int:
    """Command line: export, scrub, mark, commit and scan one snapshot."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--source', required=True, type=Path, help='the local edi repository')
    parser.add_argument('--output', required=True, type=Path, help='a new directory to create')
    parser.add_argument('--ref', default='main', help='the source ref to snapshot (default main)')
    parser.add_argument('--message', default='EasyDiffraction', help='the commit message')
    parser.add_argument(
        '--skip-hidden',
        action='store_true',
        help='leave the hidden test tiers as the source has them',
    )
    args = parser.parse_args(argv)
    if args.output.exists():
        print(
            f'snapshot: {args.output} exists; the snapshot needs a new directory', file=sys.stderr
        )
        return 2
    source_commit = export(args.source, args.ref, args.output)
    changed = scrub.scrub_tree(args.output, skip_hidden=args.skip_hidden)
    workflows = apply_preparation(args.output)
    print(f'workflows: {", ".join(workflows) or "unchanged"}')
    snapshot_commit = commit_tree(args.output, args.message)
    for rel in changed:
        print(f'scrubbed: {rel}')
    try:
        report = scan.analyse(args.output)  # one pass: credentials, members and residue together
    except scan.UnreadableArchiveError as err:
        print(f'snapshot: refused, an archive cannot be read: {err}', file=sys.stderr)
        return 1
    findings, members, residue = report.credentials, report.members, report.residue
    for rel, n, rule in findings:
        print(f'secret found: {rel}:{n} {rule}')
    for name, n, cls in members:
        print(f'archive member: {name}:{n} {cls}')
    for name, per_file in residue.items():
        print(f'residue: {name}: {sum(per_file.values())} line(s) in {len(per_file)} file(s)')
    print(
        f'snapshot: {args.ref} at {source_commit} -> {args.output} commit {snapshot_commit}; '
        f'scrub changed {len(changed)} file(s); {len(findings)} credential finding(s); '
        f'{len(members)} archive-member finding(s)',
        file=sys.stderr,
    )
    return 1 if findings or members else 0


if __name__ == '__main__':
    sys.exit(main())
