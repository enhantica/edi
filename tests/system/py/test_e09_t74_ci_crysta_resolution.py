"""development hub  units 8/10 adapted under  D5/ADR-0017.

The prior  harness virtualizes compilation only. Expected selected commits
are prescribed independently by a branch ref response and a main ref, never by the resolver.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tests.fixtures.e09_t75_commands import COMMANDS, assert_no_swallowed_refusal


class RemoteFixture:
    """Independent Git heads; no numerical extension or retired float build harness."""

    def __init__(self, root):
        self.root = root
        self.edi = root / 'edi'
        self.sibling = root / 'sibling'
        self.edi.mkdir(parents=True)
        self.sibling.mkdir()
        self.git = shutil.which('git')
        assert self.git, ' source identity fixture requires real local Git'
        self._git('init', '-q')
        file = self.sibling / 'source.txt'
        file.write_text('independent source A\n')
        self._git('add', 'source.txt')
        self._git('commit', '-qm', 'Source A')
        self._git('branch', '-M', 'main')
        self.first = self._git('rev-parse', 'HEAD').strip()
        file.write_text('independent source B\n')
        self._git('add', 'source.txt')
        self._git('commit', '-qm', 'Source B')
        self.second = self._git('rev-parse', 'HEAD').strip()
        (root / 'bin').mkdir()
        (root / 'scratch').mkdir()
        self.env = {
            k: v
            for k, v in os.environ.items()
            if not k.startswith((
                'HUB_',
                'RELAY_',
                'GIT_',
                'CRYSTA_',
                'GITHUB_',
                'GH_',
                'EDI_',
                'RUNNER_',
            ))
        }
        self.env.update(
            PATH=str(root / 'bin') + ':' + str(Path(sys.executable).parent) + ':' + os.defpath,
            FLOAT_TEST_ROOT=str(root),
            TMPDIR=str(root / 'scratch'),
            FLOAT_TEST_GIT=self.git,
        )

    def _git(self, *args):
        return subprocess.check_output(
            [
                self.git,
                '-C',
                str(self.sibling),
                '-c',
                'user.name=Fixture',
                '-c',
                'user.email=fixture@example.invalid',
                *args,
            ],
            text=True,
        )

    def run(self, script, *args, timeout=2):
        result = subprocess.run(
            ['bash', str(self.edi / 'tools/ci' / script), *args],
            cwd=self.edi,
            env=self.env,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )

        assert_no_swallowed_refusal(self.edi.parent, result.returncode == 0)
        return result


PRELUDE = (
    COMMANDS
    + r"""import json, os, sys, subprocess
from pathlib import Path
from urllib.parse import urlsplit

root = Path(os.environ['FLOAT_TEST_ROOT'])
state = json.loads((root / 'ci-state.json').read_text())
args = sys.argv[1:]
name = Path(sys.argv[0]).name
if name == 'sleep':
    if args not in (['5'], ['15']):
        command_refuse('unsupported grant or remote operation')
    with (root / 'backoffs').open('a') as f:
        f.write(' '.join(args) + '\n')
    sys.exit(0)
if name == 'gh':
    command_refuse('unsupported grant or remote operation')
if name == 'curl':
    args = admit_curl(args)
    urls = [x for x in args if x.startswith('https://')]
    method = args[args.index('-X') + 1] if '-X' in args else 'GET'
    if (
        urls != ['https://api.github.com/installation/repositories']
        or method != 'GET'
        or any(x in args for x in ('--data', '-d', '-I', '--head', '--request'))
    ):
        command_refuse('unsupported grant or remote operation')
    if 'Authorization: Bearer fixture-token-not-a-secret' not in args:
        command_refuse('unsupported grant or remote operation')
    with (root / 'grants').open('a') as f:
        f.write(json.dumps(args) + '\n')
    emit_curl(
        json.dumps({
            'total_count': 1,
            'repositories': [{'full_name': 'enhantica/crysta'}],
        }).encode()
    )
    sys.exit(0)
if name != 'git':
    command_refuse('unsupported grant or remote operation')
with (root / 'all-git').open('a') as f:
    f.write(json.dumps(args) + '\n')
if args[:3] == ['-c', 'http.https://github.com/.extraheader=', 'clone']:
    expected = ['-q', '--bare', '--filter=tree:0', '--single-branch', '--branch', 'main',
        'https://x-access-token:fixture-token-not-a-secret@github.com/enhantica/crysta']
    destination = Path(args[-1])
    valid_place = (destination.name == 'c'
        and destination.parent.parent == Path(os.environ['TMPDIR']))
    if args[3:-1] != expected or not valid_place:
        command_refuse('unsupported currency clone')
    (root / 'currency-clone').write_text(str(destination))
    sys.exit(subprocess.run([os.environ['FLOAT_TEST_GIT'], 'clone', '-q', '--bare',
        '--single-branch', '--branch', 'main', str(root / 'sibling'), str(destination)],
        check=False).returncode)
if args[:1] == ['-C'] and (root / 'currency-clone').exists():
    expected = ['-C', (root / 'currency-clone').read_text(),
        'merge-base', '--is-ancestor', state['pin'], 'main']
    if args != expected:
        command_refuse('unsupported currency ancestry observation')
    sys.exit(subprocess.run([os.environ['FLOAT_TEST_GIT'], *args], check=False).returncode)
op = next((x for x in args if x in ('ls-remote', 'fetch')), None)
if op is None:
    command_refuse('unsupported grant or remote operation')
i = args.index(op)
prefix = args[:i]
values = args[i + 1 :]
want_prefix = ['-c', 'http.https://github.com/.extraheader=']
if op == 'fetch':
    want_prefix += ['-C', str(root / 'fetched-source')]
if prefix != want_prefix or len(values) != 2:
    command_refuse('unsupported grant or remote operation')
url = urlsplit(values[0])
if (
    url.scheme != 'https'
    or url.hostname != 'github.com'
    or url.path != '/enhantica/crysta'
    or url.query
    or url.fragment
    or url.port not in (None, 443)
    or url.username != 'x-access-token'
    or url.password != 'fixture-token-not-a-secret'
):
    command_refuse('unsupported grant or remote operation')
ref = values[1]
if op == 'ls-remote' and ref == 'refs/heads/paired-topic':
    with (root / 'lookups').open('a') as f:
        f.write(json.dumps(args) + '\n')
    answer = state['lookup']
    if answer == 'none':
        sys.exit(0)
    if answer == 'error':
        print('fixture branch lookup denied', file=sys.stderr)
        sys.exit(17)
    if answer == 'inaccessible':
        print(
            {
                'denied': 'Repository not found',
                'wrong-repo': 'Authentication failed',
                'malformed': 'could not read Username',
            }[state['probe']],
            file=sys.stderr,
        )
        sys.exit(128)
    row = state['branch'] + '\t' + ref
    if answer == 'ambiguous':
        print(row + '\n' + row + '-other')
    elif answer == 'wrong-ref':
        print(row + '-other')
    elif answer == 'noncommit':
        print(state['branch'] + '\trefs/tags/paired-topic')
    elif answer == 'bad-sha':
        print('not-a-commit\t' + ref)
    else:
        print(row)
    sys.exit(0)
if (op == 'ls-remote' and ref != 'refs/heads/main') or (op == 'fetch' and ref != state['pin']):
    command_refuse('unsupported grant or remote operation')
journal = root / 'attempts'
history = journal.read_text().splitlines() if journal.exists() else []
with journal.open('a') as f:
    f.write(op + '\n')
if op == state['operation'] and history.count(op) < state['failures']:
    print('remote: Repository not found (fixture auth failure)', file=sys.stderr)
    sys.exit(128)
if op == 'ls-remote':
    print(state['pin'] + '\t' + ref)
    sys.exit(0)
sys.exit(
    subprocess.run(
        [os.environ['FLOAT_TEST_GIT'], *prefix, 'fetch', str(root / 'sibling'), ref], check=False
    ).returncode
)
"""
)


def harness(tmp_path, *, lookup='none', probe='readable', operation='ls-remote', failures=0):
    build = RemoteFixture(tmp_path)
    # Preserve new CI helper dependencies when production factors the resolver.
    shutil.copytree(
        Path(__file__).resolve().parents[3] / 'tools/ci',
        build.edi / 'tools/ci',
        dirs_exist_ok=True,
    )
    state = {
        'lookup': lookup,
        'probe': probe,
        'operation': operation,
        'failures': failures,
        'branch': build.second,
        'pin': build.second if lookup == 'present' or operation == 'fetch' else build.first,
    }
    (tmp_path / 'ci-state.json').write_text(json.dumps(state))
    (build.edi / 'pixi.toml').write_text(
        ''.join(
            '[target.'
            + platform
            + '.activation.env]\nCRYSTA_SDK_TAG = "build-'
            + state['pin']
            + '"\nCRYSTA_SDK_SHA256 = "'
            + '7' * 64
            + '"\n'
            for platform in ('linux-64', 'osx-arm64')
        )
    )
    for name in ('git', 'gh', 'curl', 'sleep', 'cmake', 'ninja', 'make', 'cc', 'c++'):
        executable = tmp_path / 'bin' / name
        executable.write_text(f'#!{sys.executable}\n' + PRELUDE)
        executable.chmod(0o755)
    build.env.update({
        'CI': 'true',
        'GITHUB_ACTIONS': 'true',
        'GITHUB_EVENT_NAME': 'pull_request',
        'GITHUB_HEAD_REF': 'paired-topic',
        'GITHUB_REF_NAME': '74/merge',
        'GITHUB_REPOSITORY': 'enhantica/edi',
        'GITHUB_TOKEN': 'fixture-token-not-a-secret',
        'GH_TOKEN': 'fixture-token-not-a-secret',
    })
    event = tmp_path / 'event.json'
    event.write_text(json.dumps({'pull_request': {'head': {'ref': 'paired-topic'}}}))
    build.env['GITHUB_EVENT_PATH'] = str(event)
    return build


def lines(path):
    return path.read_text().splitlines() if path.exists() else []


BRANCH_LOOKUP = [
    '-c',
    'http.https://github.com/.extraheader=',
    'ls-remote',
    'https://x-access-token:fixture-token-not-a-secret@github.com/enhantica/crysta',
    'refs/heads/paired-topic',
]


def assert_source_lookups(tmp_path):
    actual = [json.loads(line) for line in lines(tmp_path / 'all-git')]
    #  adds bounded main ancestry/tree reads after the one branch observation.
    assert [call for call in actual if 'ls-remote' in call] == [BRANCH_LOOKUP], (
        ' review-13 F1: source lookup must be exactly one authenticated '
        'git ls-remote for the paired branch ref'
    )
    assert not lines(tmp_path / 'gh-calls'), (
        ' ordinary paired-branch resolution must work without gh on the runner'
    )


@pytest.mark.parametrize('lookup', ['present', 'none', 'error'])
def test_ci_pairing_retains_the_pin_and_refuses_lookup_errors(tmp_path, lookup):
    build = harness(tmp_path, lookup=lookup)
    pinned = build.run('crysta-source.sh')
    assert pinned.returncode == 0, ' seq42 changes must read its pin without remote currency'
    outcome = build.run('crysta-source.sh', '--currency')
    if lookup == 'error':
        assert outcome.returncode != 0, (
            ' a failed paired-branch lookup must refuse instead of building crysta main'
        )
        assert not (build.edi / 'build/crysta-prefix/.crysta-sha').exists(), (
            ' a failed branch lookup must not attest an installed main build'
        )
        assert 'fixture branch lookup denied' in outcome.stdout + outcome.stderr, (
            ' refusal must retain the remote lookup error'
        )
        assert_source_lookups(tmp_path)
        return
    expected = build.second if lookup == 'present' else build.first
    assert outcome.returncode == 0, f' unit 8: prescribed CI source must build: {outcome.stderr}'
    assert pinned.stdout.strip() == expected, (
        ' ADR-0017 pairing retains its independent pin without floating to main'
    )
    assert not (build.edi / 'build/crysta-prefix/.crysta-sha').exists(), (
        ' ADR-0017 pairing compiles and installs no crysta source'
    )
    if lookup == 'present':
        assert_source_lookups(tmp_path)
    if lookup == 'none':
        assert 'unpaired' in outcome.stdout + outcome.stderr, (
            ' an empty successful branch lookup proves absence before main is selected'
        )


@pytest.mark.parametrize('probe', ['denied', 'wrong-repo', 'malformed'])
def test_ci_unreadable_crysta_branch_refuses_before_main(tmp_path, probe):
    build = harness(tmp_path, lookup='inaccessible', probe=probe)
    outcome = build.run('crysta-source.sh', '--currency')
    assert outcome.returncode != 0, (
        ' an unreadable crysta remote cannot prove branch absence or select main'
    )
    assert not (build.edi / 'build/crysta-prefix/.crysta-sha').exists(), (
        ' an inaccessible branch must leave no installed source attestation'
    )
    assert 'branch lookup' in outcome.stdout + outcome.stderr, (
        ' the refusal must name the branch lookup that failed'
    )
    assert len(lines(tmp_path / 'lookups')) == 3, (
        ' unit 10: authentication failures still receive three bounded attempts'
    )


@pytest.mark.parametrize('lookup', ['ambiguous', 'wrong-ref', 'noncommit', 'bad-sha'])
def test_ci_branch_lookup_refuses_ambiguous_or_invalid_refs(tmp_path, lookup):
    build = harness(tmp_path, lookup=lookup)
    outcome = build.run('crysta-source.sh', '--currency')
    assert outcome.returncode != 0, (
        ' an invalid ls-remote answer is a lookup error, not proven absence'
    )
    assert not (build.edi / 'build/crysta-prefix/.crysta-sha').exists(), (
        ' an invalid branch answer must not install any crysta source'
    )
    assert 'branch lookup' in outcome.stdout + outcome.stderr, (
        ' an invalid branch answer must identify the failing lookup'
    )
    assert_source_lookups(tmp_path)


def test_extra_branch_lookup_counterfactual_turns_pairing_gate_red(tmp_path):
    build = harness(tmp_path, lookup='present')
    script = build.edi / 'tools/ci/crysta-source.sh'
    original = script.read_text()
    needle = '  if ! crysta_remote "branch lookup" ls-remote "$(crysta_url)" "$want"; then'
    assert original.count(needle) == 1, (
        ' review-13 F1: mutant must replace the actual paired-branch lookup once'
    )
    script.write_text(
        original.replace(
            needle,
            '  git ls-remote "$(crysta_url)" refs/heads/unreviewed >/dev/null\n' + needle,
        )
    )
    with pytest.raises(AssertionError, match='unsupported command form'):
        build.run('crysta-source.sh', '--currency')


@pytest.mark.parametrize('operation', ['ls-remote', 'fetch'])
@pytest.mark.parametrize('failures', [2, 99])
@pytest.mark.parametrize('sibling', ['exact', 'absent', 'main-only'])
def test_auth_retry_is_bounded_and_exhaustion_never_substitutes_a_sibling(
    tmp_path, operation, failures, sibling
):
    # Fetch controls select branch B; the main-only sibling carries A, never B.
    build = harness(
        tmp_path,
        lookup='present' if operation == 'fetch' else 'none',
        operation=operation,
        failures=failures,
    )
    if sibling == 'absent':
        build.env['CRYSTA_SRC'] = str(tmp_path / 'missing')
    elif sibling == 'main-only':
        other = tmp_path / 'main-only'
        subprocess.run([build.git, 'init', '-q', str(other)], check=True)
        subprocess.run(
            [
                build.git,
                '-C',
                str(other),
                'fetch',
                '-q',
                '--depth=1',
                str(build.sibling),
                build.first,
            ],
            check=True,
        )
        subprocess.run(
            [build.git, '-C', str(other), 'update-ref', 'refs/remotes/origin/main', build.first],
            check=True,
        )
        build.env['CRYSTA_SRC'] = str(other)
    target = tmp_path / 'fetched-source'
    subprocess.run([build.git, 'init', '-q', str(target)], check=True)
    pin = json.loads((tmp_path / 'ci-state.json').read_text())['pin']
    remote = 'https://x-access-token:fixture-token-not-a-secret@github.com/enhantica/crysta'
    args = (
        ['ls-remote', remote, 'refs/heads/main']
        if operation == 'ls-remote'
        else ['-C', str(target), 'fetch', remote, pin]
    )
    outcome = subprocess.run(
        [
            'bash',
            '-eu',
            '-c',
            (
                'source "$1"; shift; crysta_remote "SDK source fetch" "$@"; '
                'printf "%s\\n" "$CRYSTA_REMOTE_OUT"'
            ),
            'remote-fixture',
            str(build.edi / 'tools/ci/crysta-source.sh'),
            *args,
        ],
        cwd=build.edi,
        env=build.env,
        capture_output=True,
        text=True,
        check=False,
        timeout=2,
    )
    assert (outcome.returncode == 0) == (failures == 2), (
        ' ADR-0017 retries retain the pin; exhaustion cannot substitute any sibling source'
    )
    assert lines(tmp_path / 'attempts').count(operation) == 3, (
        ' unit 10 each auth-failing remote operation gets three attempts'
    )
    assert lines(tmp_path / 'backoffs') == ['5', '15'], (
        ' unit 10 bounded auth backoff remains five then fifteen seconds'
    )
    assert len(lines(tmp_path / 'grants')) == min(failures, 3), (
        ' unit 10 each failed auth attempt must execute the addressed grant listing'
    )
    assert 'token grants' in outcome.stderr, (
        ' unit 10 auth failures must report token repository grants'
    )
    assert 'fixture-token-not-a-secret' not in outcome.stdout + outcome.stderr, (
        ' unit 10 grant diagnostics must redact the token'
    )
    assert not (build.edi / 'build/crysta-prefix/.crysta-sha').exists(), (
        ' ADR-0017 remote source fetch must never install a compiled crysta build'
    )
    if failures == 2 and operation == 'fetch':
        got = subprocess.check_output(
            [build.git, '-C', str(target), 'rev-parse', 'FETCH_HEAD'], text=True
        ).strip()
        assert got == pin, (
            ' ADR-0017 shared fetch must address exactly the independently pinned source'
        )


@pytest.mark.parametrize(
    'defect',
    [
        'resource',
        'operation',
        'attached-method',
        'long-method',
        'attached-data',
        'attached-form',
        'unknown-option',
    ],
)
def test_sdk_token_grant_route_refuses_another_resource_or_operation(tmp_path, defect):
    build = harness(tmp_path)
    command = [
        str(tmp_path / 'bin/curl'),
        '-fsS',
        '-H',
        'Authorization: Bearer fixture-token-not-a-secret',
        '-H',
        'Accept: application/vnd.github+json',
        'https://api.github.com/installation/repositories',
    ]
    control = subprocess.run(
        command, env=build.env, capture_output=True, text=True, check=False, timeout=2
    )
    assert control.returncode == 0, ' token-grant route must first admit its exact addressed GET'
    mutant = (
        command[:-1] + ['https://api.github.com/repos/other/crysta']
        if defect == 'resource'
        else command
        + {
            'operation': ['-X', 'POST'],
            'attached-method': ['-XPOST'],
            'long-method': ['--request=POST'],
            'attached-data': ['-dBODY'],
            'attached-form': ['-FBODY'],
            'unknown-option': ['--unlisted-form'],
        }[defect]
    )
    bad = subprocess.run(
        mutant, env=build.env, capture_output=True, text=True, check=False, timeout=2
    )
    assert bad.returncode == 64 and not bad.stdout, (
        ' another token-grant resource or operation must refuse'
    )
