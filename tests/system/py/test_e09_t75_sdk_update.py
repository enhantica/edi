"""D3: execute the updater with exact REST identities and incomplete PR inventories."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from tests.fixtures.e09_t75_commands import assert_no_swallowed_refusal, checked_program
from tests.fixtures.e09_t75_workflow import active, reached, workflow_cwd, workflow_env

ROOT = Path(__file__).resolve().parents[3]


def update(tmp_path, defect=None, workflow_override=None, *, pin_transform=None):  # noqa: PLR0912, PLR0914, PLR0915
    workflow = ROOT / '.github/workflows/crysta-sdk-update.yml'
    if workflow_override is None:
        assert workflow.is_file(), ' D3 requires the executable SDK update workflow'
        jobs = yaml.safe_load(workflow.read_text())['jobs']
    else:
        jobs = workflow_override['jobs']
    repo = tmp_path / 'edi'
    shutil.copytree(
        ROOT / 'tools/ci', repo / 'tools/ci', ignore=shutil.ignore_patterns('__pycache__')
    )
    (repo / '.gitignore').write_text('__pycache__/\n')
    realgit = shutil.which('git')

    def git(*args):
        return subprocess.run(
            [
                realgit,
                '-C',
                str(repo),
                '-c',
                'user.name=Fixture',
                '-c',
                'user.email=f@example.invalid',
                *args,
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=2,
        ).stdout.strip()

    producer = tmp_path / 'producer'
    producer.mkdir()

    def producer_git(*args):
        return subprocess.run(
            [
                realgit,
                '-C',
                str(producer),
                '-c',
                'user.name=Fixture',
                '-c',
                'user.email=f@example.invalid',
                *args,
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=2,
        ).stdout.strip()

    producer_git('init', '-q', '-b', 'main')
    (producer / 'source.cpp').write_text('Independent old producer content\n')
    producer_git('add', '.')
    producer_git('commit', '-qm', 'Prior published producer')
    old = producer_git('rev-parse', 'HEAD')
    (producer / 'source.cpp').write_text('Independent newer producer content\n')
    producer_git('add', '.')
    producer_git('commit', '-qm', 'Newer published producer')
    newest = producer_git('rev-parse', 'HEAD')
    if defect == 'squashed-pin':
        old = producer_git(
            'commit-tree',
            producer_git('rev-parse', old + '^{tree}'),
            '-p',
            old,
            '-m',
            'Retained paired PR with landed equal content',
        )
        producer_git('tag', 'build-' + old, old)
    bare = tmp_path / 'crysta.git'
    producer_git('clone', '--bare', '-q', str(producer), str(bare))
    before = (
        '[workspace]\nplatforms=["linux-64","osx-arm64"]\n'
        '[tasks]\nunchanged="must remain byte-identical"\n'
    )
    for platform in ('linux-64', 'osx-arm64'):
        before += (
            f'[target.{platform}.activation.env]\nCRYSTA_SDK_TAG="build-'
            + old
            + '"\nCRYSTA_SDK_SHA256="'
            + '7' * 64
            + '"\n'
        )
    if defect == 'single-quoted-main':
        before = before.replace(chr(34), chr(39))
    if pin_transform is not None:
        before = pin_transform(before)
    (repo / 'pixi.toml').write_text(before)
    git('init', '-q', '-b', 'main')
    git('add', '.')
    git('commit', '-qm', 'Independent update baseline')
    base = git('rev-parse', 'HEAD')
    git('remote', 'add', 'origin', 'https://github.com/enhantica/edi')
    git('update-ref', 'refs/remotes/origin/main', base)
    git('config', 'user.name', 'Fixture')
    git('config', 'user.email', 'f@example.invalid')
    git('branch', 'crysta-sdk/old-unreferenced')
    git('update-ref', 'refs/remotes/origin/crysta-sdk/old-unreferenced', base)
    if defect == 'lost-push':
        git('branch', 'crysta-sdk/local-unrelated')
    state = {
        'git': realgit,
        'base': base,
        'sha': newest,
        'old': old,
        'bare': str(bare),
        'repo': str(repo),
        'defect': defect,
        'deleted': [],
        'pushed': [],
        'dispatched': [],
    }
    (tmp_path / 'state.json').write_text(json.dumps(state))
    binary = tmp_path / 'bin'
    binary.mkdir()
    common = (
        "import json,os,sys\nfrom pathlib import Path\nr=Path(os.environ['UP"
        "DATE_FIXTURE']);p=r/'state.json';d=json.loads(p.read_text());a=sy"
        "s.argv[1:]\nwith (r/'calls').open('a') as f:f.write(json.dumps([NA"
        "ME,*a])+'\\n')\ndef fail():sys.exit(64)\ndef save():p.write_text(jso"
        'n.dumps(d))\n'
    )
    gh = binary / 'gh'
    gh.write_text(
        '#!'
        + sys.executable
        + '\nNAME="gh"\n'
        + common
        + r"""
# Parse the public long-equals and attached short flag forms before resource selection.
parsed = []
for value in a:
    if value.startswith('--') and '=' in value:
        flag, operand = value.split('=', 1)
        parsed.extend([flag, operand])
    elif len(value) > 2 and value[:2] in (
        '-R',
        '-H',
        '-B',
        '-s',
        '-X',
        '-f',
        '-F',
        '-p',
        '-D',
        '-L',
        '-w',
        '-j',
        '-r',
    ):
        parsed.extend([value[:2], value[2:]])
    else:
        parsed.append(value)
a = parsed


def opt(*names):
    return next((a[i + 1] for i, x in enumerate(a[:-1]) if x in names), None)


if (opt('--hostname') or os.environ.get('GH_HOST', 'github.com')) != 'github.com':
    fail()


def selected(rows, head=None, base=None, state='open'):
    return [
        row
        for row in rows
        if (head is None or row['head']['ref'] == head)
        and (base is None or row['base']['ref'] == base)
        and (state == 'all' or row['state'] == state)
    ]


def emit(value):
    emit_gh(value)
    sys.exit(0)


assets = [
    {
        'id': i + 1,
        'name': 'crysta-sdk-' + d['sha'] + '-' + platform + '.tar.gz',
        'digest': 'sha256:' + '9' * 64,
        'browser_download_url': 'https://fixture.invalid/sdk/' + platform,
        'url': 'https://api.github.com/repos/enhantica/crysta/releases/assets/' + str(i + 1),
    }
    for i, platform in enumerate(('linux-64', 'osx-arm64'))
]
release = {
    'id': 88,
    'tag_name': 'build-' + d['sha'],
    'tagName': 'build-' + d['sha'],
    'target_commitish': d['sha'],
    'published_at': '2026-09-30T14:00:00Z',
    'prerelease': True,
    'assets': assets,
}
prs = [
    {
        'number': 74,
        'state': 'open',
        'head': {'ref': 'other-topic', 'sha': d['base']},
        'base': {'ref': 'main'},
    }
]
if (
    a[:2] == ['release', 'list']
    and (opt('--repo', '-R') or os.environ.get('GH_REPO', 'enhantica/edi')) == 'enhantica/crysta'
):
    emit([release])
if (
    a[:2] == ['release', 'view']
    and a[2] == 'build-' + d['sha']
    and (opt('--repo', '-R') or os.environ.get('GH_REPO', 'enhantica/edi')) == 'enhantica/crysta'
):
    emit(release)
if (
    a[:2] == ['pr', 'list']
    and (opt('--repo', '-R') or os.environ.get('GH_REPO', 'enhantica/edi')) == 'enhantica/edi'
):
    # A bare pr list is not a proof of complete pagination in this planted large inventory.
    if opt('--limit', '-L') is None:
        fail()
    emit(
        selected(prs, opt('--head', '-H'), opt('--base', '-B'), opt('--state', '-s') or 'open')
    )
if a[:2] == ['run', 'list']:
    if (opt('--repo', '-R') or os.environ.get('GH_REPO', 'enhantica/edi')) != 'enhantica/edi':
        fail()
    rows = [
        {'headSha': p['sha'], 'branch': ref, 'workflow': 'ci.yml', 'event': 'workflow_dispatch'}
        for ref in d['dispatched']
        for p in d['pushed']
        if p['ref'] == ref
    ]
    for flag, key in [('--workflow', 'workflow'), ('--branch', 'branch'), ('--event', 'event')]:
        if opt(flag) is not None:
            rows = [row for row in rows if row[key] == opt(flag)]
    emit(rows)
if a[:2] == ['workflow', 'run'] and a[2] == 'ci.yml':
    if (opt('--repo', '-R') or os.environ.get('GH_REPO', 'enhantica/edi')) != 'enhantica/edi':
        fail()
    ref = next((a[i + 1] for i, x in enumerate(a[:-1]) if x in ('--ref', '-r')), None)
    if ref != 'crysta-sdk/' + d['sha'][:12] or not any(x['ref'] == ref for x in d['pushed']):
        fail()
    if d['defect'] == 'lost-dispatch':
        sys.exit(19)
    d['dispatched'].append(ref)
    save()
    sys.exit(0)
if a[:1] != ['api']:
    fail()
request = gh_api_request()
path = request['path']
fields = request['fields']
method = opt('--method', '-X') or (
    'POST' if any(x in a for x in ('-f', '-F', '--field', '--raw-field', '--input')) else 'GET'
)
mutation_methods = {
    'repos/enhantica/edi/git/refs/heads/crysta-sdk/old-unreferenced': 'DELETE',
    'repos/enhantica/edi/actions/workflows/ci.yml/dispatches': 'POST',
}
if method != mutation_methods.get(path, 'GET'):
    fail()
if path == 'repos/enhantica/crysta/releases':
    current = {**release, 'tag_name': 'build-' + d['old']}
    emit([current if d['defect'] == 'pin-currentness' else release])
if path == 'repos/enhantica/crysta/releases/tags/build-' + d['sha']:
    emit(release)
if path == 'repos/enhantica/crysta/compare/' + d['old'] + '...' + d['sha']:
    emit({
        'status': 'ahead',
        'ahead_by': 1,
        'behind_by': 0,
        'merge_base_commit': {'sha': d['old']},
    })
if path == 'repos/enhantica/crysta/commits/' + d['sha']:
    emit({'sha': d['sha']})
if path in ('repos/enhantica/crysta/branches/main', 'repos/enhantica/crysta/git/ref/heads/main'):
    emit({'commit': {'sha': d['sha']}, 'object': {'sha': d['sha']}})
if path == 'repos/enhantica/edi/pulls' or path == 'search/issues':
    if '--paginate' in a and d['defect'] == 'missing-page':
        sys.exit(19)
    page = fields.get('page', '1')
    if d['defect'] == 'missing-page' and page != '1':
        sys.exit(19)
    if path.startswith('search/'):
        q = fields.get('q', '').split()
        if not {'repo:enhantica/edi', 'is:pr', 'is:open'} <= set(q):
            emit({'total_count': 0, 'incomplete_results': False, 'items': []})
    filtered = selected(
        prs,
        fields.get('head', None),
        fields.get('base', None),
        fields.get('state', 'open'),
    )
    count = 3 if d['defect'] == 'total-mismatch' else len(filtered)
    if path.startswith('search/'):
        emit({
            'total_count': count,
            'incomplete_results': d['defect'] in ('incomplete', 'missing-page'),
            'items': filtered,
        })
    # REST pull lists have no total_count: expose pagination through Link headers.
    if '--include' in a or '-i' in a:
        print(
            'HTTP/2 200\nLink: <https://api.github.com/repos/enhantica/edi/'
            'pulls?page=2>; rel="next"\n'
        )
    size = int(fields.get('per_page', '30'))
    start = (int(page) - 1) * size
    emit_gh(filtered[start : start + size])
    sys.exit(0)
if path == 'repos/enhantica/edi/git/refs/heads':
    emit([{'ref': 'refs/heads/crysta-sdk/old-unreferenced', 'object': {'sha': d['base']}}])
if path == 'repos/enhantica/edi/git/refs/heads/crysta-sdk/old-unreferenced' and 'DELETE' in a:
    d['deleted'].append(path)
    save()
    sys.exit(0)
if path == 'repos/enhantica/edi/actions/workflows/ci.yml/dispatches':
    ref = fields.get('ref')
    if (
        ('POST' not in a)
        or ref != 'crysta-sdk/' + d['sha'][:12]
        or not any(x['ref'] == ref for x in d['pushed'])
    ):
        fail()
    if d['defect'] == 'lost-dispatch':
        sys.exit(19)
    d['dispatched'].append(ref)
    save()
    sys.exit(0)
fail()
"""
    )
    gh.write_text(checked_program(gh.read_text(), 'gh'))
    gh.chmod(0o755)
    g = binary / 'git'
    g.write_text(
        '#!'
        + sys.executable
        + '\nNAME="git"\n'
        + common
        + r"""from urllib.parse import urlsplit
import subprocess

prefix = a[
    : next(
        (i for i, x in enumerate(a) if x in ('ls-remote', 'push', 'fetch', 'clone', 'pull')),
        len(a),
    )
]
cwd = Path.cwd()
for i, flag in enumerate(prefix[:-1]):
    if flag == '-C':
        cwd = (cwd / prefix[i + 1]).resolve()


def repository(remote, expected):
    if '://' not in remote and not remote.startswith('git@'):
        result = subprocess.run(
            [d['git'], *prefix, 'remote', 'get-url', remote], capture_output=True, text=True
        )
        if result.returncode:
            fail()
        remote = result.stdout.strip()
    if remote == 'git@github.com:' + expected + '.git':
        return
    url = urlsplit(remote)
    if (
        url.scheme != 'https'
        or url.hostname != 'github.com'
        or url.port not in (None, 443)
        or url.path.removesuffix('.git') != '/' + expected
        or url.query
        or url.fragment
    ):
        fail()


if 'ls-remote' in a:
    i = a.index('ls-remote')
    operands = [x for x in a[i + 1 :] if not x.startswith('-')]
    if len(operands) != 2:
        fail()
    remote, ref = operands
    if ref == 'refs/heads/main':
        repository(remote, 'enhantica/crysta')
        print(d['sha'] + '\trefs/heads/main')
        sys.exit(0)
    if ref in ('refs/heads/crysta-sdk/*', 'refs/heads/crysta-sdk/old-unreferenced'):
        repository(remote, 'enhantica/edi')
        print(d['base'] + '\trefs/heads/crysta-sdk/old-unreferenced')
        sys.exit(0)
    fail()
if 'push' in a:
    if cwd != Path(d['repo']).resolve():
        fail()
    repository('origin', 'enhantica/edi')
    i = a.index('push')
    operands = [x for x in a[i + 1 :] if not x.startswith('-')]
    if len(operands) != 2 or operands[0] != 'origin':
        fail()
    spec = operands[1]
    if '--delete' in a or spec.startswith(':'):
        if spec.lstrip(':') != 'crysta-sdk/old-unreferenced':
            fail()
        d['deleted'].append(a)
    else:
        branch = 'crysta-sdk/' + d['sha'][:12]
        source, destination = spec.split(':', 1) if ':' in spec else (spec, spec)
        if destination not in (branch, 'refs/heads/' + branch):
            fail()
        result = __import__('subprocess').run(
            [d['git'], *prefix, 'rev-parse', '--verify', source + '^{commit}'],
            capture_output=True,
            text=True,
        )
        if result.returncode:
            fail()
        content = __import__('subprocess').run(
            [d['git'], *prefix, 'show', result.stdout.strip() + ':pixi.toml'],
            capture_output=True,
            text=True,
        )
        if content.returncode:
            fail()
        manifest = __import__('tomllib').loads(content.stdout)
        if any(
            manifest['target'][platform]['activation']['env']['CRYSTA_SDK_TAG']
            != 'build-' + d['sha']
            for platform in ('linux-64', 'osx-arm64')
        ):
            fail()
        if any(
            manifest['target'][platform]['activation']['env']['CRYSTA_SDK_SHA256'] != '9' * 64
            for platform in ('linux-64', 'osx-arm64')
        ):
            fail()
        if d['defect'] == 'lost-push':
            d['local_proposal'] = result.stdout.strip()
            save()
            sys.exit(19)
        d['pushed'].append({'remote': 'origin', 'ref': branch, 'sha': result.stdout.strip()})
        subprocess.run(
            [
                d['git'],
                *prefix,
                'update-ref',
                'refs/remotes/origin/' + branch,
                result.stdout.strip(),
            ],
            check=True,
        )
    save()
    sys.exit(0)
if 'fetch' in a:
    i = a.index('fetch')
    operands = [x for x in a[i + 1 :] if not x.startswith('-')]
    expected = 'refs/tags/build-' + d['old'] + ':refs/tags/build-' + d['old']
    if cwd == (r / 'crysta').resolve() and len(operands) == 2 and operands[1] == expected:
        repository(operands[0], 'enhantica/crysta')
        os.execv(d['git'], [d['git'], *prefix, 'fetch', d['bare'], expected])
    if cwd != Path(d['repo']).resolve():
        fail()
    repository('origin', 'enhantica/edi')
    i = a.index('fetch')
    operands = [x for x in a[i + 1 :] if not x.startswith('-')]
    if operands not in (
        ['origin', 'main'],
        ['origin', 'refs/heads/main'],
        ['origin', 'main:refs/remotes/origin/main'],
    ):
        fail()
    __import__('subprocess').run(
        [d['git'], 'update-ref', 'refs/remotes/origin/main', d['base']], check=True
    )
    sys.exit(0)
if 'clone' in a:
    urls = [x for x in a if x.startswith(('https://', 'git@'))]
    if len(urls) != 1:
        fail()
    repository(urls[0], 'enhantica/crysta')
    os.execv(d['git'], [d['git'], *[(d['bare'] if x == urls[0] else x) for x in a]])
if 'pull' in a:
    fail()
os.execv(d['git'], [d['git'], *a])
"""
    )
    g.write_text(checked_program(g.read_text(), 'git'))
    g.chmod(0o755)
    env = {
        **os.environ,
        'PATH': str(binary) + ':' + str(Path(sys.executable).parent) + ':' + os.defpath,
        'UPDATE_FIXTURE': str(tmp_path),
        'GITHUB_TOKEN': 'own-repository-token',
        'GITHUB_REPOSITORY': 'enhantica/edi',
        'GITHUB_EVENT_NAME': 'workflow_dispatch',
        'GITHUB_REF': 'refs/heads/main',
        'GITHUB_SHA': base,
        'GITHUB_WORKSPACE': str(repo),
        'RUNNER_TEMP': str(tmp_path),
        'GITHUB_OUTPUT': str(tmp_path / 'outputs'),
        'GITHUB_ENV': str(tmp_path / 'environment'),
    }
    results = []
    outputs = {}
    for job in jobs.values():  # noqa: PLR1702
        reached(job, 'workflow_dispatch')
        for step in job['steps']:
            if 'run' not in step:
                continue

            def expand(value):
                for k, v in {
                    'github.repository': 'enhantica/edi',
                    'github.token': 'own-repository-token',
                    'github.sha': base,
                    'runner.temp': str(tmp_path),
                    'github.event_name': 'workflow_dispatch',
                }.items():
                    value = str(value).replace('${{ ' + k + ' }}', v)
                for (ident, key), v in outputs.items():
                    value = value.replace('${{ steps.' + ident + '.outputs.' + key + ' }}', v)
                if 'outputs.token' in value:
                    value = re.sub(
                        r'\$\{\{\s*steps\.[^.]+\.outputs\.token\s*\}\}',
                        'producer-read-token',
                        value,
                    )
                assert '${{' not in value, (
                    ' updater environment must resolve its actual workflow expression'
                )
                return value

            if not active(step, 'workflow_dispatch', outputs=outputs):
                continue
            assert not step.get('continue-on-error'), (
                ' update cannot hide a failed state transition'
            )
            result = subprocess.run(
                ['bash', '-eu', '-o', 'pipefail', '-c', expand(step['run'])],
                cwd=workflow_cwd(job, step, repo, expand),
                env=workflow_env(job, step, env, expand),
                text=True,
                capture_output=True,
                check=False,
                timeout=3,
            )
            results.append(result)
            assert_no_swallowed_refusal(tmp_path, result.returncode == 0)
            for target, kind in (
                (Path(env['GITHUB_ENV']), 'env'),
                (Path(env['GITHUB_OUTPUT']), 'output'),
            ):
                if target.exists():
                    for line in target.read_text().splitlines():
                        if '=' in line:
                            key, value = line.split('=', 1)
                            if kind == 'env':
                                env[key] = value
                            elif step.get('id'):
                                outputs[step['id'], key] = value
                    target.write_text('')
            if result.returncode:
                break
    if defect in {'lost-dispatch', 'lost-push'}:
        observed = json.loads((tmp_path / 'state.json').read_text())
        if defect == 'lost-dispatch':
            assert observed['pushed'], (
                ' F17 partial dispatch must actually push the complete pin first'
            )
        else:
            assert observed.get('local_proposal') and not observed['pushed'], (
                ' I26 failed push leaves a validated local proposal without publishing it'
            )
        assert not observed['dispatched'], (
            ' F17 the first dispatch must actually fail before retry'
        )
        observed['defect'] = None
        (tmp_path / 'state.json').write_text(json.dumps(observed))
        git('switch', 'main')
        retry = subprocess.run(
            [
                sys.executable,
                'tools/ci/crysta_sdk_update.py',
                '--crysta-clone',
                str(tmp_path / 'crysta'),
            ],
            cwd=repo,
            env={**env, 'CRYSTA_TOKEN': 'producer-read-token', 'GH_TOKEN': 'own-repository-token'},
            capture_output=True,
            text=True,
            check=False,
            timeout=3,
        )
        results.append(retry)
        assert_no_swallowed_refusal(tmp_path, retry.returncode == 0)
    return (
        results,
        json.loads((tmp_path / 'state.json').read_text()),
        before,
        (repo / 'pixi.toml').read_text(),
    )


def unpin(text):
    return re.sub(r'(?m)^CRYSTA_SDK_(TAG|SHA256)\s*=.*$', '', text)


@pytest.mark.parametrize('defect', ['missing-page', 'total-mismatch'])
def test_d3_incomplete_pr_inventory_deletes_no_superseded_branch(tmp_path, defect):
    control = tmp_path / 'control'
    control.mkdir()
    runs, state, before, after = update(control)
    assert runs, ' D3 complete inventory must first admit the bounded pin-update control'
    assert all(r.returncode == 0 for r in runs), (
        ' D3 complete inventory must first admit the bounded pin-update control'
    )
    assert state['pushed'], (
        ' I26 updater must push the committed platform-complete pin before dispatch'
    )
    assert state['dispatched'], (
        ' D3 complete inventory must first admit the bounded pin-update control'
    )
    assert state['deleted'], (
        ' ruling C complete inventory must exercise deletion of the'
        ' independently unreferenced old branch'
    )
    assert unpin(before) == unpin(after), ' I26 update diff must change only SDK pin lines'
    assert before != after, ' I26 update diff must change only SDK pin lines'
    mutant = tmp_path / 'mutant'
    mutant.mkdir()
    runs, state, _, _ = update(mutant, defect)
    assert not state['deleted'], (
        ' ruling C any incomplete PR listing must delete no superseded branch'
    )


# Fixture-only requests exercise both transports without claiming updater green.
@pytest.mark.parametrize('route', ['CLI', 'REST'])
@pytest.mark.parametrize('coordinate', ['head', 'base', 'state', 'repo'])
def test_sdk_update_pair_listing_fixture_preserves_selection(tmp_path, route, coordinate):
    head = 'other-topic'
    base = 'main'
    state = 'open'
    repo = 'enhantica/edi'
    if coordinate == 'head':
        head = 'wrong-topic'
    elif coordinate == 'base':
        base = 'wrong-base'
    elif coordinate == 'state':
        state = 'closed'
    else:
        repo = 'other/edi'
    if route == 'REST':
        command = f'gh api "repos/{repo}/pulls?head={head}&base={base}&state={state}"'
    else:
        command = (
            f'gh pr list --repo {repo} --head {head} --base {base} '
            f'--state {state} --limit 1000 --json number'
        )
    correct = 'gh api "repos/enhantica/edi/pulls?head=other-topic&base=main&state=open"'
    if route == 'CLI-equals':
        command = re.sub(r'(--(?:repo|head|base|state|limit)) ', r'\1=', command)
        correct = re.sub(r'(--(?:repo|head|base|state|limit)) ', r'\1=', correct)
    good = tmp_path / 'control'
    good.mkdir()
    runs, _, _, _ = update(
        good, workflow_override={'jobs': {'probe': {'steps': [{'run': correct}]}}}
    )
    assert runs, ' F4 listing mutant must first admit the correctly selected PR'
    assert runs[-1].returncode == 0, (
        ' F4 listing mutant must first admit the correctly selected PR'
    )
    assert len(json.loads(runs[-1].stdout)) == 1, (
        ' F4 listing mutant must first admit the correctly selected PR'
    )
    bad = tmp_path / 'mutant'
    bad.mkdir()
    runs, fixture, _, _ = update(
        bad, workflow_override={'jobs': {'probe': {'steps': [{'run': command}]}}}
    )
    assert runs, ' F4 wrong updater listing coordinate cannot return the intended PR'
    assert runs[-1].returncode == 64 or json.loads(runs[-1].stdout) == [], (
        ' F4 wrong updater listing coordinate cannot return the intended PR'
    )
    assert not fixture['deleted'], ' F4 wrong selection must not mutate intended update resources'
    assert not fixture['pushed'], ' F4 wrong selection must not mutate intended update resources'
    assert not fixture['dispatched'], (
        ' F4 wrong selection must not mutate intended update resources'
    )


def update_probe(command):
    return {'jobs': {'probe': {'steps': [{'run': command}]}}}


def branch_prefix():
    return (
        'branch=$(python3 -c \'import json,os;print("crysta-sdk/"+json.load'
        '(open(os.environ["UPDATE_FIXTURE"]+"/state.json"))["sha"][:12])\')'
        '\n'
    )


def pin_new_content():
    return (
        'python3 -c \'import json,os,pathlib;d=json.load(open(os.environ["U'
        'PDATE_FIXTURE"]+"/state.json"));p=pathlib.Path("pixi.toml");p.wri'
        'te_text(p.read_text().replace(d["old"],d["sha"]).replace("7"*64,"9"*64))'
        "'\ngit add pixi.t"
        'oml\ngit commit -qm "Independent new pin fixture"\n'
    )


@pytest.mark.parametrize('route', ['CLI', 'REST'])
@pytest.mark.parametrize('coordinate', ['repo', 'ref'])
def test_sdk_update_dispatch_fixture_preserves_repository_and_ref(tmp_path, route, coordinate):
    def command(repo, ref):
        return (
            branch_prefix()
            + pin_new_content()
            + 'git push origin HEAD:$branch\n'
            + (
                f'gh workflow run ci.yml --repo {repo} --ref {ref}'
                if route == 'CLI'
                else (
                    f'gh api -X POST repos/{repo}/actions/workflows/ci.yml/dispatches -f ref={ref}'
                )
            )
        )

    good = tmp_path / 'control'
    good.mkdir()
    runs, state, _, _ = update(
        good,
        workflow_override=update_probe(
            branch_prefix()
            + pin_new_content()
            + 'git push origin HEAD:$branch\n'
            + 'gh workflow run ci.yml --ref $branch'
        ),
    )
    assert runs, ' F4 matching updater dispatch transport must first admit its exact ref'
    assert runs[-1].returncode == 0, (
        ' F4 matching updater dispatch transport must first admit its exact ref'
    )
    assert state['dispatched'] == ['crysta-sdk/' + state['sha'][:12]], (
        ' F4 matching updater dispatch transport must first admit its exact ref'
    )
    repo = 'other/edi' if coordinate == 'repo' else 'enhantica/edi'
    ref = 'wrong-topic' if coordinate == 'ref' else '$branch'
    bad = tmp_path / 'mutant'
    bad.mkdir()
    runs, state, _, _ = update(bad, workflow_override=update_probe(command(repo, ref)))
    assert runs, ' F4 changing only repository or supplied ref must refuse desired dispatch'
    assert runs[-1].returncode == 64, (
        ' F4 changing only repository or supplied ref must refuse desired dispatch'
    )
    assert not state['dispatched'], (
        ' F4 changing only repository or supplied ref must refuse desired dispatch'
    )


@pytest.mark.parametrize('coordinate', ['remote', 'refspec', 'source'])
def test_sdk_update_push_fixture_preserves_remote_destination_and_content(tmp_path, coordinate):
    good = tmp_path / 'control'
    good.mkdir()
    runs, state, _, _ = update(
        good,
        workflow_override=update_probe(
            branch_prefix() + pin_new_content() + 'git push origin HEAD:$branch'
        ),
    )
    assert runs, (
        ' F4 exact remote/refspec and independently committed pin content must admit transport'
    )
    assert runs[-1].returncode == 0, (
        ' F4 exact remote/refspec and independently committed pin content must admit transport'
    )
    assert len(state['pushed']) == 1, (
        ' F4 exact remote/refspec and independently committed pin content must admit transport'
    )
    target = 'wrong-topic' if coordinate == 'refspec' else '$branch'
    remote = 'wrong-origin' if coordinate == 'remote' else 'origin'
    command = (
        branch_prefix()
        + ('' if coordinate == 'source' else pin_new_content())
        + f'git push {remote} HEAD:{target}'
    )
    bad = tmp_path / 'mutant'
    bad.mkdir()
    runs, state, _, _ = update(bad, workflow_override=update_probe(command))
    assert runs, (
        ' F4 changing only remote, destination or source content must refuse intended push'
    )
    assert runs[-1].returncode == 64, (
        ' F4 changing only remote, destination or source content must refuse intended push'
    )
    assert not state['pushed'], (
        ' F4 changing only remote, destination or source content must refuse intended push'
    )


@pytest.mark.parametrize('method', ['POST', 'PUT', 'DELETE'])
def test_updater_read_resource_rejects_mutation_methods(tmp_path, method):
    runs, state, _, _ = update(
        tmp_path,
        workflow_override=update_probe(
            'gh api --method='
            + method
            + ' "repos/enhantica/edi/pulls?head=other-topic&base=main&state=open"'
        ),
    )
    assert runs, ' F4 mutation method must reach the updater transport'
    assert runs[-1].returncode == 64, ' F4 updater reads refuse mutation methods'
    assert not state['deleted'], ' F4 refused read cannot delete owned resources'
    assert not state['dispatched'], ' F4 refused read cannot dispatch owned CI'


@pytest.mark.parametrize('route', ['CLI', 'REST'])
def test_update_dispatch_without_a_pushed_committed_pin_refuses(tmp_path, route):
    command = branch_prefix() + (
        'gh workflow run ci.yml --repo enhantica/edi --ref $branch'
        if route == 'CLI'
        else (
            'gh api -X POST repos/enhantica/edi/actions/workflows/ci.yml/dispatches -f ref=$branch'
        )
    )
    runs, state, _, _ = update(tmp_path, workflow_override=update_probe(command))
    assert runs, ' I26 workflow dispatch must address an actually pushed pin commit'
    assert runs[-1].returncode == 64, (
        ' I26 workflow dispatch must address an actually pushed pin commit'
    )
    assert not state['dispatched'], (
        ' I26 workflow dispatch must address an actually pushed pin commit'
    )


@pytest.mark.parametrize('boundary', ['job', 'step'])
def test_update_replay_cannot_execute_work_the_workflow_skips(tmp_path, boundary):
    workflow = update_probe('echo forbidden > "$RUNNER_TEMP/forbidden"')
    job = workflow['jobs']['probe']
    (job if boundary == 'job' else job['steps'][0])['if'] = False
    if boundary == 'job':
        with pytest.raises(AssertionError, match=' required workflow route'):
            update(tmp_path, workflow_override=workflow)
    else:
        runs, state, _, _ = update(tmp_path, workflow_override=workflow)
        assert not runs, ' skipped step cannot acquire a fabricated successful result'
        assert not state['dispatched'], (
            ' skipped step cannot acquire a fabricated successful result'
        )
    assert not (tmp_path / 'forbidden').exists(), ' skipped workflow work must never execute'


@pytest.mark.parametrize('route', ['fetch', 'push'])
@pytest.mark.parametrize('coordinate', ['origin-url', 'checkout'])
def test_update_git_mutation_observes_actual_checkout_and_remote(tmp_path, route, coordinate):
    command = branch_prefix() + pin_new_content()
    if coordinate == 'origin-url':
        command += 'git remote set-url origin https://notgithub.com/enhantica/edi\n'
    call = 'git -C "$RUNNER_TEMP" ' if coordinate == 'checkout' else 'git '
    command += call + ('fetch origin main' if route == 'fetch' else 'push origin HEAD:$branch')
    runs, state, _, _ = update(tmp_path, workflow_override=update_probe(command))
    assert runs, ' addressed checkout and origin host cannot alias the updater repository'
    assert runs[-1].returncode == 64, (
        ' addressed checkout and origin host cannot alias the updater repository'
    )
    assert not state['pushed'], ' wrong-addressed git mutation must perform no intended push'


@pytest.mark.parametrize(
    'command',
    [
        'git ls-remote https://notgithub.com/enhantica/crysta refs/heads/main',
        'git ls-remote https://github.com/enhantica/c' + 'rysta refs/heads/wrong',
        'git ls-remote https://github.com/enhantica/edi refs/heads/wrong',
        'git ls-remote https://notgithub.com/enhantica/edi refs/heads/crysta-sdk/*',
    ],
    ids=['producer-host', 'producer-ref', 'consumer-ref', 'consumer-host'],
)
def test_update_ref_lookup_does_not_alias_host_or_requested_ref(tmp_path, command):
    runs, _state, _, _ = update(tmp_path, workflow_override=update_probe(command))
    assert runs, ' wrong host or ref cannot receive intended branch observations'
    assert runs[-1].returncode == 64, (
        ' wrong host or ref cannot receive intended branch observations'
    )
    assert not runs[-1].stdout, ' wrong host or ref cannot receive intended branch observations'


UPDATE_ROUTES = {
    'release-list-rest': ('gh api repos/enhantica/crysta/releases', 'GET'),
    'release-tag-rest': ('gh api repos/enhantica/crysta/releases/tags/build-$sha', 'GET'),
    'compare-rest': ('gh api repos/enhantica/crysta/compare/$old...$sha', 'GET'),
    'commit-rest': ('gh api repos/enhantica/crysta/commits/$sha', 'GET'),
    'branch-rest': ('gh api repos/enhantica/crysta/branches/main', 'GET'),
    'ref-rest': ('gh api repos/enhantica/crysta/git/ref/heads/main', 'GET'),
    'pull-list-rest': (
        'gh api "repos/enhantica/edi/pulls?head=other-topic&base=main&state=open"',
        'GET',
    ),
    'search-rest': ('gh api "search/issues?q=repo:enhantica/edi+is:pr+is:open"', 'GET'),
    'ref-list-rest': ('gh api repos/enhantica/edi/git/refs/heads', 'GET'),
    'ref-delete-rest': (
        'gh api -X DELETE repos/enhantica/edi/git/refs/heads/crysta-sdk/old-unreferenced',
        'DELETE',
    ),
    'dispatch-rest': (
        'gh api -X POST repos/enhantica/edi/actions/workflows/ci.yml/dispatches -f ref=$branch',
        'POST',
    ),
    'release-list-cli': ('gh release list -R enhantica/crysta --json tagName', None),
    'release-view-cli': ('gh release view build-$sha -R enhantica/crysta', None),
    'pull-list-cli': (
        (
            'gh pr list -R enhantica/edi --head other-topic --base main --stat'
            'e open --limit 1000 --json number'
        ),
        None,
    ),
    'dispatch-cli': ('gh workflow run ci.yml -R enhantica/edi --ref $branch', None),
}


@pytest.mark.parametrize('route', sorted(UPDATE_ROUTES))
def test_update_every_observation_and_mutation_route_rejects_wrong_resource_and_operation(
    tmp_path, route
):
    command, method = UPDATE_ROUTES[route]

    def prefix():
        setup = (
            branch_prefix()
            + """read -r sha old < <(python3 - <<'STATE'
import json,os
with open(os.environ['UPDATE_FIXTURE']+'/state.json') as source:
    d=json.load(source)
print(d['sha'],d['old'])
STATE
)
"""
        )
        if route.startswith('dispatch'):
            setup += pin_new_content() + 'git push origin HEAD:$branch\n'
        return setup

    good = tmp_path / 'control'
    good.mkdir()
    runs, state, _, _ = update(good, workflow_override=update_probe(prefix() + command))
    assert runs, (
        ' route enumeration requires each exact resource and operation to admit its control'
    )
    if runs[-1].returncode == 64:
        assert (good / 'unsupported-commands.jsonl').exists(), (
            ' F1 every retired complete route persists refusal before effects'
        )
        assert not state['dispatched'] and not state['deleted'], (
            ' F1 a retired route cannot acquire a modeled effect'
        )
        return
    assert runs[-1].returncode == 0, (
        ' route enumeration requires each exact resource and operation to admit its control'
    )
    if route.startswith('dispatch'):
        assert state['pushed'], (
            ' dispatch route control must observe committed push before dispatch'
        )
        assert state['dispatched'], (
            ' dispatch route control must observe committed push before dispatch'
        )
    elif route == 'ref-delete-rest':
        assert state['deleted'], ' delete route control must reach the intended branch deletion'
    else:
        value = (
            runs[-1].stdout.strip() if route == 'release-view-cli' else json.loads(runs[-1].stdout)
        )
        assert value, ' read route control must return its independently planted observation'
    for defect in ('resource', 'operation'):
        bad = tmp_path / defect
        bad.mkdir()
        mutant = (
            command.replace('enhantica/', 'decoy/')
            if defect == 'resource'
            else (
                command.replace('-X ' + method, '-X GET' if method != 'GET' else '-X DELETE')
                if method and method != 'GET'
                else command.replace('gh api ', 'gh api -X DELETE ')
                if method
                else command
                .replace('gh release ', 'gh release upload ')
                .replace('gh pr list', 'gh pr create')
                .replace('gh workflow run', 'gh workflow view')
            )
        )
        runs, state, _, _ = update(bad, workflow_override=update_probe(prefix() + mutant))
        assert runs, ' wrong resource or operation must lose its intended observation or mutation'
        assert runs[-1].returncode == 64 or (
            route == 'search-rest' and json.loads(runs[-1].stdout)['items'] == []
        ), ' wrong resource or operation must lose its intended observation or mutation'
        assert not state['dispatched'], (
            ' refused enumerated requests cannot mutate desired resources'
        )
        assert not state['deleted'], ' refused enumerated requests cannot mutate desired resources'


@pytest.mark.parametrize(
    ('command', 'mutant'),
    [
        (
            'gh release list -R enhantica/crysta --json tagName',
            'gh release list -R enhantica/crysta --json tagName --exclude-pre-releases',
        ),
        (
            'gh release list -R enhantica/crysta --json tagName',
            'gh release list -R enhantica/crysta --json tagName --limit 1',
        ),
        (
            'gh api repos/enhantica/crysta/releases',
            'gh api "repos/enhantica/crysta/releases?page=2"',
        ),
        (
            (
                'git clone --filter=blob:none --no-checkout '
                'https://github.com/enhantica/c' + 'rysta.git "$RUNNER_TEMP/clone-control"'
            ),
            (
                'git clone --filter=blob:limit=1 --no-checkout '
                'https://github.com/enhantica/c' + 'rysta.git "$RUNNER_TEMP/clone-control"'
            ),
        ),
        ('git fetch origin main', 'git fetch --dry-run origin main'),
        (
            'git ls-remote https://github.com/enhantica/c' + 'rysta refs/heads/main',
            'git ls-remote --tags https://github.com/enhantica/c' + 'rysta refs/heads/main',
        ),
        (
            'git ls-remote https://github.com/enhantica/c' + 'rysta refs/heads/main',
            'git ls-remote --get-url https://github.com/enhantica/c' + 'rysta refs/heads/main',
        ),
        ('git push origin HEAD:$branch', 'git push --dry-run origin HEAD:$branch'),
        (
            'git push origin --delete crysta-sdk/old-unreferenced',
            'git push --dry-run origin --delete crysta-sdk/old-unreferenced',
        ),
    ],
    ids=[
        'release-filter',
        'release-limit',
        'page',
        'clone-filter',
        'fetch-dry-run',
        'lookup-tags',
        'lookup-url',
        'push-dry-run',
        'delete-dry-run',
    ],
)
def test_updater_unsupported_operation_forms_refuse_before_credited_effect(
    tmp_path, command, mutant
):
    if command.startswith('gh release list '):
        command = 'gh api --paginate --slurp repos/enhantica/crysta/releases'
    setup = branch_prefix() + pin_new_content() if 'push' in command else ''
    good = tmp_path / 'control'
    good.mkdir()
    runs, *_ = update(good, workflow_override=update_probe(setup + command))
    assert runs[-1].returncode == 0, (
        ' D3 supported operation must admit before dry-run/query/filter escape'
    )
    bad = tmp_path / 'mutant'
    bad.mkdir()
    runs, state, *_ = update(bad, workflow_override=update_probe(setup + mutant))
    assert runs[-1].returncode == 64, (
        ' D3 unsupported command form cannot be credited with a real operation'
    )
    assert not state['pushed'] and not state['deleted'] and not state['dispatched'], (
        ' D3 refused operation cannot publish/delete/dispatch'
    )
    assert (bad / 'unsupported-commands.jsonl').exists(), (
        ' D3 unsupported form must leave refusal evidence'
    )
