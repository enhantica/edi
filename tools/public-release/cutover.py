# SPDX-License-Identifier: BSD-3-Clause
"""The cutover's scripted steps: rehearse a newer snapshot, list the settings, and run the cut.

    python tools/public-release/cutover.py rehearse --source LOCAL_GIT_REPO --previous SNAPSHOT
        --output NEW_LOCAL_PATH [--ref main]
    python tools/public-release/cutover.py settings --repo OWNER/NAME [--org OWNER]
    python tools/public-release/cutover.py cut --date YYYY-MM-DD --snapshot SNAPSHOT
        [--org enhantica] [--repo edi] [--apply]

`rehearse` makes a new snapshot of `--ref` (`snapshot.py`, the hidden test tiers as the source has
them) and lists what changed against the `--previous` snapshot's commit, file by file: the delta a
reviewer reads before the newer snapshot replaces the published one. It refuses (exit 1) when the
snapshot does: a credential, an archive member carrying private residue, or an unreadable archive.

`settings` reads, through the GitHub API (`gh`), what a repository's configuration consists of:
its secrets, variables and environments (names only, never values), its rulesets, its labels and
its Pages configuration, and the organization's secrets and variables visible to it. The output is
the inventory the checklist (`docs/dev/public-release-checklist.md`) recreates on the new
repository.
It only reads; it changes no setting of any repository.

`cut` is the cut window's plan (`docs/dev/public-release-checklist.md`, the cut). Without `--apply`
it only reads: it checks the snapshot (one clean commit; no credential, archive-member finding or
content problem), that the repository is private with no open pull request and the archive name
is free, and it prints every change the cut would make. With `--apply` it makes them, in order, and
stops at the first that fails: rename the repository to `<repo>-archive-<date>`; create a new
private repository under the old name with the old one's settings; push the snapshot as its only
commit; recreate the labels and the main-branch ruleset (the content check required too); create
the `crysta-sdk` environment for `main`; require approval for fork pull requests; and give the new
repository the organization's runner groups, secrets and variables that are granted repository by
repository. The date is the cut's, set by whoever runs it.
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime
import json
import shlex
import subprocess
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import scan  # the sibling modules, importable from any working directory
import snapshot


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(['git', '-C', str(repo), *args], capture_output=True, check=True)
    return result.stdout.decode()


def delta(previous: Path, new: Path) -> list[str]:
    """The files that differ between two snapshots, as `git diff --name-status` lines."""
    _git(new, 'fetch', '--quiet', str(previous.resolve()), 'HEAD:refs/previous/snapshot')
    listed = _git(new, 'diff', '--name-status', 'refs/previous/snapshot', 'HEAD')
    return [line for line in listed.splitlines() if line]


def rehearse(args: argparse.Namespace) -> int:
    """Snapshot `--ref` anew and print its delta against the previous snapshot."""
    code = snapshot.main([
        '--source',
        str(args.source),
        '--output',
        str(args.output),
        '--ref',
        args.ref,
        '--skip-hidden',
    ])
    if code not in {0, 1}:
        return code
    changes = delta(args.previous, args.output)
    for line in changes:
        print(f'delta: {line}')
    print(f'cutover: {len(changes)} file(s) differ from the previous snapshot', file=sys.stderr)
    if code:
        print(
            'cutover: refused: the new snapshot carries a credential or an archive-member finding',
            file=sys.stderr,
        )
    return code


def _api(path: str, jq: str) -> list[str]:
    result = subprocess.run(
        ['gh', 'api', '--paginate', path, '--jq', jq], capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        return [f'<unreadable: {result.stderr.strip() or result.returncode}>']
    return [line for line in result.stdout.splitlines() if line]


def settings(args: argparse.Namespace) -> int:
    """Print the repository's configuration inventory as JSON (names, never values)."""
    repo, org = args.repo, args.org or args.repo.split('/')[0]
    inventory = {
        'repository': repo,
        'secrets': _api(f'repos/{repo}/actions/secrets', '.secrets[].name'),
        'variables': _api(f'repos/{repo}/actions/variables', '.variables[].name'),
        'environments': _api(f'repos/{repo}/environments', '.environments[].name'),
        'rulesets': _api(f'repos/{repo}/rulesets', '.[] | "\\(.id) \\(.name) \\(.enforcement)"'),
        'labels': _api(
            f'repos/{repo}/labels', '.[] | "\\(.name)\\t\\(.color)\\t\\(.description)"'
        ),
        'pages': _api(f'repos/{repo}/pages', '"\\(.build_type) \\(.html_url)"'),
        'org_secrets': _api(
            f'orgs/{org}/actions/secrets', '.secrets[] | "\\(.name) \\(.visibility)"'
        ),
        'org_variables': _api(
            f'orgs/{org}/actions/variables', '.variables[] | "\\(.name) \\(.visibility)"'
        ),
    }
    print(json.dumps(inventory, indent=1))
    return 0


class CutRefusedError(Exception):
    """A check or a step of the cut failed: nothing after it runs."""


class Plan:
    """The cut's steps: reads always run; a change is printed, and made only with --apply."""

    def __init__(self, *, apply: bool) -> None:
        self.apply = apply

    @staticmethod
    def read(*argv: str, missing_ok: bool = False) -> str | None:
        """Run a read; its output, or None when ``missing_ok`` and it is not found."""
        result = subprocess.run(argv, capture_output=True, text=True, check=False)
        if result.returncode:
            if missing_ok and 'Not Found' in result.stderr:
                return None
            raise CutRefusedError(f'{shlex.join(argv)}: {result.stderr.strip()[:300]}')
        return result.stdout

    def change(self, what: str, argv: list[str], body: object = None) -> str:
        """Make one change (with --apply) or show it; return its output."""
        shown = shlex.join(argv) + (f' <<< {json.dumps(body)}' if body is not None else '')
        print(f'{"cut" if self.apply else "would"}: {what}: {shown}')
        if not self.apply:
            return ''
        result = subprocess.run(
            argv,
            input=None if body is None else json.dumps(body),
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode:
            raise CutRefusedError(f'{what}: {result.stderr.strip()[:300]}')
        return result.stdout


def _gh_json(*path: str, missing_ok: bool = False) -> object:
    out = Plan.read('gh', 'api', *path, missing_ok=missing_ok)
    return None if out is None else json.loads(out or 'null')


def _check_snapshot(snapshot: Path) -> str:
    """The snapshot's one commit, once it proves publishable; refuses otherwise."""
    git = ('git', '-C', str(snapshot))
    if Plan.read(*git, 'rev-list', '--count', 'HEAD').strip() != '1':
        raise CutRefusedError(f'{snapshot}: the snapshot must be exactly one commit')
    if Plan.read(*git, 'status', '--porcelain'):
        raise CutRefusedError(f'{snapshot}: the snapshot has uncommitted changes')
    try:
        report = scan.analyse(snapshot)
    except scan.UnreadableArchiveError as err:
        raise CutRefusedError(f'{snapshot}: an archive cannot be read: {err}') from err
    if report.credentials or report.members:
        raise CutRefusedError(f'{snapshot}: credential or archive-member findings')
    check = subprocess.run(
        [sys.executable, str(Path(__file__).with_name('content_check.py')), '--base', 'root'],
        cwd=snapshot,
        capture_output=True,
        text=True,
        check=False,
    )
    if check.returncode:
        raise CutRefusedError(f'{snapshot}: the content check refuses it:\n{check.stdout[-2000:]}')
    return Plan.read(*git, 'rev-parse', 'HEAD').strip()


REPO_SETTINGS = (
    'description',
    'homepage',
    'has_issues',
    'has_projects',
    'has_wiki',
    'allow_squash_merge',
    'allow_merge_commit',
    'allow_rebase_merge',
    'delete_branch_on_merge',
)
APP_CREDENTIALS = {'secrets': 'ENHANTICA_APP_KEY', 'variables': 'ENHANTICA_APP_ID'}
RULESET_NAME = 'main protection'
CONTENT_CHECK = 'content check'


def _ruleset(source: dict) -> dict:
    """The ruleset to create: the old one's rules, a plain name, and the content check required."""
    rules = []
    for old_rule in source['rules']:
        rule = {k: v for k, v in old_rule.items() if k in {'type', 'parameters'} and v is not None}
        checks = rule.get('parameters', {}).get('required_status_checks')
        if checks is not None and CONTENT_CHECK not in {c['context'] for c in checks}:
            checks.append({'context': CONTENT_CHECK})
        rules.append(rule)
    keep = ('target', 'enforcement', 'conditions', 'bypass_actors')
    return {'name': RULESET_NAME, **{k: source[k] for k in keep if k in source}, 'rules': rules}


@dataclasses.dataclass
class Cut:
    """What the checks read: the facts the changes are made from."""

    org: str
    repo: str
    archive: str
    snapshot: Path
    old: dict
    labels: list
    rulesets: list
    groups: list
    shared: dict


def _preflight(args: argparse.Namespace) -> Cut:
    """Read and check everything the cut needs; refuse at the first precondition that fails."""
    org, repo = args.org, args.repo
    archive = f'{repo}-archive-{datetime.date.fromisoformat(args.date).isoformat()}'
    commit = _check_snapshot(args.snapshot)
    print(f'cut: snapshot {args.snapshot} commit {commit}: publishable')
    old = _gh_json(f'repos/{org}/{repo}')
    if not old['private']:
        raise CutRefusedError(f'{org}/{repo} is public: the cut is into a private repository')
    if _gh_json(f'repos/{org}/{archive}', missing_ok=True) is not None:
        raise CutRefusedError(f'{org}/{archive} exists already')
    open_prs = _gh_json(f'repos/{org}/{repo}/pulls?state=open&per_page=100')
    if open_prs:
        raise CutRefusedError(f'{org}/{repo} has {len(open_prs)} open pull request(s): freeze it')
    found = Cut(
        org=org,
        repo=repo,
        archive=archive,
        snapshot=args.snapshot,
        old=old,
        labels=_gh_json(f'repos/{org}/{repo}/labels?per_page=100'),
        rulesets=[
            _gh_json(f'repos/{org}/{repo}/rulesets/{r["id"]}')
            for r in _gh_json(f'repos/{org}/{repo}/rulesets')
        ],
        groups=_gh_json(f'orgs/{org}/actions/runner-groups')['runner_groups'],
        shared={
            kind: _gh_json(f'orgs/{org}/actions/{kind}/{name}')
            for kind, name in APP_CREDENTIALS.items()
        },
    )
    for group in found.groups:
        public = 'allowed' if group['allows_public_repositories'] else 'not allowed'
        print(
            f'cut: runner group {group["name"]}: visibility {group["visibility"]}, '
            f'public repositories {public}'
        )
    for kind, item in found.shared.items():
        print(f'cut: organization {kind[:-1]} {item["name"]}: visibility {item["visibility"]}')
    return found


def _mutation(method: str, path: str) -> list[str]:
    return ['gh', 'api', '-X', method, path, '--input', '-']


# The refs the crysta-sdk environment admits: pushes to main, and pull requests, whose runs use
# their merge ref. A fork's pull request is admitted too: GitHub gives it no secrets, and its jobs
# skip every step that needs the token.
ENVIRONMENT_REFS = ('main', 'refs/pull/*/merge')


def _labels(plan: Plan, labels_path: str, wanted: list[dict]) -> None:
    """Make the new repository's labels the old one's: update shared ones, create the rest.

    GitHub gives a new repository default labels, and names match ignoring case.
    """
    present = _gh_json(f'{labels_path}?per_page=100') if plan.apply else None
    existing = {label['name'].lower(): label['name'] for label in present or []}
    names = {label['name'].lower() for label in wanted}
    for key, name in sorted(existing.items()):
        if key not in names:
            path = f'{labels_path}/{urllib.parse.quote(name, safe="")}'
            plan.change('remove a default label', ['gh', 'api', '-X', 'DELETE', path])
    for label in wanted:
        fields = {k: label[k] for k in ('color', 'description') if label.get(k) is not None}
        name = existing.get(label['name'].lower())
        if name is None:
            what = 'create a label' if plan.apply else 'create the label, or update it if present'
            body = {'name': label['name'], **fields}
            plan.change(what, _mutation('POST', labels_path), body)
        else:
            path = f'{labels_path}/{urllib.parse.quote(name, safe="")}'
            body = {'new_name': label['name'], **fields}
            plan.change('update a label', _mutation('PATCH', path), body)


def _changes(plan: Plan, cut: Cut) -> None:
    """The cut's changes, in order; each shown, and made only with --apply."""
    org, repo, old = cut.org, cut.repo, cut.old
    plan.change(
        'rename the repository', _mutation('PATCH', f'repos/{org}/{repo}'), {'name': cut.archive}
    )
    settings_body = {k: old[k] for k in REPO_SETTINGS if old.get(k) is not None}
    body = {'name': repo, 'private': True, **settings_body}
    plan.change('create the private repository', _mutation('POST', f'orgs/{org}/repos'), body)
    url = f'https://github.com/{org}/{repo}.git'
    push = ['git', '-C', str(cut.snapshot), 'push', url, 'HEAD:refs/heads/main']
    plan.change('push the snapshot as main', push)
    new_id = str(_gh_json(f'repos/{org}/{repo}')['id']) if plan.apply else '<new repository id>'
    _labels(plan, f'repos/{org}/{repo}/labels', cut.labels)
    for ruleset in cut.rulesets:
        plan.change(
            'create the ruleset',
            _mutation('POST', f'repos/{org}/{repo}/rulesets'),
            _ruleset(ruleset),
        )
    environment = f'repos/{org}/{repo}/environments/crysta-sdk'
    branches = {'protected_branches': False, 'custom_branch_policies': True}
    plan.change(
        'create the crysta-sdk environment',
        _mutation('PUT', environment),
        {'deployment_branch_policy': branches},
    )
    for ref in ENVIRONMENT_REFS:
        plan.change(
            f'admit {ref}',
            _mutation('POST', f'{environment}/deployment-branch-policies'),
            {'name': ref, 'type': 'branch'},
        )
    plan.change(
        'require approval for fork pull requests',
        _mutation('PUT', f'repos/{org}/{repo}/actions/permissions/fork-pr-contributor-approval'),
        {'approval_policy': 'all_external_contributors'},
    )
    for group in cut.groups:
        if group['visibility'] == 'selected':
            path = f'orgs/{org}/actions/runner-groups/{group["id"]}/repositories/{new_id}'
            plan.change(f'grant runner group {group["name"]}', ['gh', 'api', '-X', 'PUT', path])
    for kind, item in cut.shared.items():
        if item['visibility'] == 'selected':
            path = f'orgs/{org}/actions/{kind}/{item["name"]}/repositories/{new_id}'
            plan.change(f'grant {item["name"]}', ['gh', 'api', '-X', 'PUT', path])


def cut(args: argparse.Namespace) -> int:
    """Check the cut's preconditions and print, or with --apply make, every change it needs."""
    try:
        _changes(Plan(apply=args.apply), _preflight(args))
    except (CutRefusedError, ValueError, KeyError, TypeError) as err:
        print(f'cut: refused: {err}', file=sys.stderr)
        return 1
    done = 'done' if args.apply else 'checked; run again with --apply to cut'
    print(f'cut: {done}', file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    """Command line: `rehearse` or `settings`."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest='command', required=True)
    rehearse_cmd = commands.add_parser('rehearse', help='snapshot anew and list the delta')
    rehearse_cmd.add_argument('--source', required=True, type=Path)
    rehearse_cmd.add_argument('--previous', required=True, type=Path)
    rehearse_cmd.add_argument('--output', required=True, type=Path)
    rehearse_cmd.add_argument('--ref', default='main')
    settings_cmd = commands.add_parser('settings', help="list a repository's settings")
    settings_cmd.add_argument('--repo', required=True)
    settings_cmd.add_argument('--org')
    cut_cmd = commands.add_parser('cut', help='check, or with --apply run, the cut')
    cut_cmd.add_argument('--date', required=True, help="the cut's date, YYYY-MM-DD")
    cut_cmd.add_argument('--snapshot', required=True, type=Path, help='the gated snapshot')
    cut_cmd.add_argument('--org', default='enhantica')
    cut_cmd.add_argument('--repo', default='edi')
    cut_cmd.add_argument('--apply', action='store_true', help='make the changes (default: check)')
    args = parser.parse_args(argv)
    commands_run = {'rehearse': rehearse, 'settings': settings, 'cut': cut}
    return commands_run[args.command](args)


if __name__ == '__main__':
    sys.exit(main())
