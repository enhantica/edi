"""D2: independently constructed SDK/lock fixtures challenge consumption."""

from __future__ import annotations

import hashlib
import io
import json
import os
import shlex
import shutil
import subprocess
import sys
import tarfile
import tomllib
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from tests.fixtures.e09_t75_commands import assert_no_swallowed_refusal, checked_program
from tests.system.py.test_e09_t75_pin_currency import currency_world

ROOT = Path(__file__).resolve().parents[3]
SHA = 'a7' * 20
TREE = '3b' * 20
PACKAGE = {'name': 'libcxx', 'version': '19.1.7', 'build': 'hf95d169_0'}
# Independent I25 ABI inventory, transcribed from the accepted producer/consumer seam.
ABI_PACKAGES = {
    'linux-64': (
        'gcc_impl_linux-64',
        'gxx_impl_linux-64',
        'libgcc',
        'libgcc-devel_linux-64',
        'libstdcxx',
        'libstdcxx-devel_linux-64',
        'libgomp',
        'sysroot_linux-64',
        'eigen',
        'sleef',
    ),
    'osx-arm64': (
        'clang_impl_osx-arm64',
        'clangxx_impl_osx-arm64',
        'libcxx',
        'libcxx-devel',
        'llvm-openmp',
        'eigen',
        'sleef',
    ),
}


def consumer(  # noqa: PLR0914, PLR0915
    tmp_path,
    defect=None,
    platform='osx-arm64',
    *,
    download=False,
    retained_tags=None,
    command_override=None,
    prepare_only=False,
):
    source = (ROOT / 'tools/ci/build-crysta.sh').read_text()
    assert command_override is not None or 'CRYSTA_SDK_DIR' in source, (
        ' I26 requires SDK-only consumption (baseline absent)'
    )
    repo = tmp_path / 'edi'
    shutil.copytree(
        ROOT / 'tools/ci', repo / 'tools/ci', ignore=shutil.ignore_patterns('__pycache__')
    )
    (repo / '.gitignore').write_text('__pycache__/\n')
    sdk = tmp_path / 'sdk'
    for path, content in {
        'lib/libcrysta_core.a': b'independent static library bytes\x00\x17',
        'bin/crysta': b'#!/bin/sh\necho git:' + SHA.encode() + b'\n',
        'include/crysta/fixture.hpp': b'#pragma once\n',
        'lib/cmake/crysta/crystaConfig.cmake': b'# fixture\n',
    }.items():
        p = sdk / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(content)
        if path.startswith('bin/'):
            p.chmod(0o755)
    packages = [dict(PACKAGE, name=name) for name in ABI_PACKAGES[platform]]
    fp = {'packages': [p.copy() for p in packages], 'macos_deployment_target': '11.0'}
    if defect == 'version':
        fp['packages'][0]['version'] = '19.1.6'
    elif defect == 'build':
        fp['packages'][0]['build'] = 'different_build_9'
    elif defect == 'package':
        fp['packages'][0]['name'] = 'unresolved-package'
    elif defect == 'target':
        fp['macos_deployment_target'] = '12.0'
    manifest = {
        'schema': 1,
        'source_sha': SHA,
        'source_tree': TREE,
        'platform': platform,
        'identity': 'git:' + SHA,
        'fingerprint': fp,
        'crysta_version': '1.0.0',
        'cmake_options': {'CRYSTA_LTO': 'OFF', 'CMAKE_BUILD_TYPE': 'Release'},
        'tested': {
            'sha256': {
                p: hashlib.sha256((sdk / p).read_bytes()).hexdigest()
                for p in ('lib/libcrysta_core.a', 'bin/crysta')
            },
            'cpp_tier': {'passed': 7, 'total': 7},
            'corpus': {'passed': 3, 'total': 3},
            'configuration': 'Release',
            'run_id': 75090,
            'run_attempt': 2,
            'job': 'checks (macOS)',
        },
    }
    p = sdk / 'share/crysta-sdk/manifest.json'
    p.parent.mkdir(parents=True)
    p.write_text(json.dumps(manifest))
    urls = [
        f'https://conda.anaconda.org/conda-forge/{platform}/{p["name"]}-{p["version"]}-{p["build"]}.conda'
        for p in packages
    ]
    lock = {
        'version': 7,
        'platforms': [{'name': platform}],
        'environments': {
            'default': {'channels': [], 'packages': {platform: [{'conda': url} for url in urls]}}
        },
        'packages': [dict(p, conda=url) for p, url in zip(packages, urls, strict=True)],
    }
    (repo / 'pixi.lock').write_text(yaml.safe_dump(lock, sort_keys=False))
    (repo / 'pixi.toml').write_text(
        '[workspace]\nplatforms = ["linux-64", "osx-arm64"]\n'
        + ''.join(
            '[target.' + target + '.activation.env]\nCRYSTA_SDK_TAG = "build-' + SHA + '"\n'
            'CRYSTA_SDK_SHA256 = "' + '7' * 64 + '"\nMACOSX_DEPLOYMENT_TARGET = "11.0"\n'
            for target in ('linux-64', 'osx-arm64')
        )
    )
    binpath = tmp_path / 'bin'
    binpath.mkdir()
    for command in ('cmake', 'ninja', 'make', 'git', 'gh', 'curl'):
        p = binpath / command
        p.write_text('#!/bin/sh\nprintf "%s\\n" "$0 $*" >> "$SDK_COMMANDS"\nexit 91\n')
        p.chmod(0o755)
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith((
            'CRYSTA_',
            'PIXI_',
            'HUB_',
            'RELAY_',
            'EDI_',
            'GITHUB_',
            'GIT_',
            'RUNNER_',
            'ACTIONS_',
        ))
        and k not in {'GH_TOKEN', 'CI'}
    }
    # Before: RUNNER_TEMP leaked the real job's cached paired head. After:
    # every synthetic acquisition owns its memo directory and CI inputs.
    runner_temp = tmp_path / 'runner-temp'
    runner_temp.mkdir()
    env.update(
        PATH=f'{binpath}:{Path(sys.executable).parent}:{env.get("PATH", os.defpath)}',
        CRYSTA_SDK_DIR=str(sdk),
        PIXI_PROJECT_ROOT=str(repo),
        PIXI_ENVIRONMENT_NAME='default',
        PIXI_PLATFORM=platform,
        CONDA_SUBDIR=platform,
        RUNNER_OS='macOS' if platform == 'osx-arm64' else 'Linux',
        RUNNER_ARCH='ARM64' if platform == 'osx-arm64' else 'X64',
        RUNNER_TEMP=str(runner_temp),
        MACOSX_DEPLOYMENT_TARGET='11.0',
        SDK_COMMANDS=str(tmp_path / 'commands'),
    )
    if download:
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode='w:gz') as archive:
            for file in sorted(sdk.rglob('*')):
                if file.is_file():
                    archive.add(file, arcname=str(file.relative_to(sdk)))
        asset = tmp_path / 'published-sdk.tar.gz'
        asset.write_bytes(buffer.getvalue())
        digest = hashlib.sha256(asset.read_bytes()).hexdigest()
        (repo / 'pixi.toml').write_text((repo / 'pixi.toml').read_text().replace('7' * 64, digest))
        name = f'crysta-sdk-{SHA}-{platform}.tar.gz'
        metadata = {
            'tag_name': 'build-' + SHA,
            'target_commitish': SHA,
            'assets': [
                {
                    'id': 1001,
                    'name': name,
                    'url': 'https://api.github.com/repos/enhantica/crysta/releases/assets/1001',
                    'browser_download_url': 'https://fixture.invalid/' + name,
                    'digest': 'sha256:' + digest,
                }
            ],
        }
        state = {
            'metadata': metadata,
            'asset': str(asset),
            'name': name,
            'retained_tags': list(retained_tags)
            if retained_tags is not None
            else ['build-' + SHA],
        }
        (tmp_path / 'download.json').write_text(json.dumps(state))
        curl = binpath / 'curl'
        curl.write_text(
            '#!'
            + sys.executable
            + '\n'
            + r"""import json, os, sys
from pathlib import Path

r = Path(os.environ['DOWNLOAD_FIXTURE'])
d = json.loads((r / 'download.json').read_text())
a = sys.argv[1:]

parsed = []
for value in a:
    if value.startswith('--') and '=' in value:
        flag, operand = value.split('=', 1)
        parsed.extend([flag, operand])
    elif len(value) > 2 and value[:2] in ('-X', '-o', '-H'):
        parsed.extend([value[:2], value[2:]])
    else:
        parsed.append(value)
a = parsed
method = next(
    (a[i + 1] for i, x in enumerate(a[:-1]) if x in ('--request', '-X')),
    'POST'
    if any(x in a for x in ('--data', '--data-raw', '--data-binary', '-d', '--form', '-F'))
    else 'GET',
)
if method != 'GET' or any(x in a for x in ('-I', '--head')):
    sys.exit(64)
with (r / 'downloads').open('a') as f:
    f.write(json.dumps(a) + '\n')
urls = [x for x in a if x.startswith('https://')]
if len(urls) != 1:
    sys.exit(64)
u = urls[0]
if u == 'https://api.github.com/repos/enhantica/crysta/releases/tags/' + d['metadata']['tag_name']:
    if d['metadata']['tag_name'] not in d['retained_tags']:
        sys.exit(22)
    data = json.dumps(d['metadata']).encode()
elif u in (
    'https://api.github.com/repos/enhantica/crysta/releases/assets/1001',
    'https://fixture.invalid/' + d['name'],
):
    headers = [a[i + 1].lower() for i, x in enumerate(a[:-1]) if x in ('-H', '--header')]
    if (
        u.startswith('https://api.github.com/')
        and 'accept: application/octet-stream' not in headers
    ):
        sys.exit(64)
    data = Path(d['asset']).read_bytes()
else:
    sys.exit(64)
emit_curl(data)
"""
        )
        curl.write_text(checked_program(curl.read_text(), 'curl'))
        curl.chmod(0o755)
        env.pop('CRYSTA_SDK_DIR')
        env.update(
            DOWNLOAD_FIXTURE=str(tmp_path),
            GITHUB_TOKEN='fixture-token',  # noqa: S106
            CI='true',
            GITHUB_EVENT_NAME='push',
            GITHUB_REF='refs/heads/main',
        )
    if prepare_only:
        return env, repo, sdk
    result = subprocess.run(
        ['bash', '-eu', '-c', command_override]
        if command_override is not None
        else ['bash', str(repo / 'tools/ci/build-crysta.sh')],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=3,
    )
    assert_no_swallowed_refusal(tmp_path, result.returncode == 0)
    return result, tmp_path / 'commands'


def test_d2_diagnostic_sdk_is_used_without_compiling_or_resolving_another_source(tmp_path):
    r, commands = consumer(tmp_path)
    assert r.returncode == 0, f' matching diagnostic SDK must admit: {r.stdout}{r.stderr}'
    assert 'crysta: using SDK build-' + SHA in r.stdout + r.stderr, (
        ' I6 consumer log must identify the prescribed SDK'
    )
    assert TREE in r.stdout + r.stderr, ' SDK provenance must name the independently planted tree'
    assert not commands.exists(), ' diagnostic package path must compile and download nothing'


@pytest.mark.parametrize('defect', ['version', 'build', 'package', 'target'])
def test_d2_nontrivial_fingerprint_mismatch_refuses_before_configure(tmp_path, defect):
    good = tmp_path / 'control'
    good.mkdir()
    control, _ = consumer(good)
    assert control.returncode == 0, (
        ' fingerprint rejection must first admit the matching lock fixture'
    )
    bad = tmp_path / 'mutant'
    bad.mkdir()
    result, commands = consumer(bad, defect)
    assert result.returncode != 0, ' I25 every fingerprint field mismatch must refuse'
    assert 'fingerprint' in result.stdout + result.stderr, (
        ' fingerprint mismatch must be diagnosed by name'
    )
    assert not commands.exists(), ' I25 mismatch refuses before configure, fetch or compile'


def test_d2_pin_is_platform_complete_and_osx64_is_retired():
    doc = tomllib.loads((ROOT / 'pixi.toml').read_text())
    platforms = doc.get('workspace', doc.get('project', {}))['platforms']
    assert 'osx-64' not in platforms, ' owner decision removes osx-64 from edi platforms'
    assert 'osx-64' not in doc.get('target', {}), (
        ' owner decision removes every osx-64 target table'
    )
    for platform in ('linux-64', 'osx-arm64'):
        pin = doc['target'][platform]['activation']['env']
        assert {'CRYSTA_SDK_TAG', 'CRYSTA_SDK_SHA256'} <= set(pin), (
            ' each supported platform must declare both SDK pin fields'
        )
        assert len(pin['CRYSTA_SDK_TAG'].removeprefix('build-')) == 40, (
            ' SDK pin must use a full commit identity'
        )
        assert len(pin['CRYSTA_SDK_SHA256']) == 64, ' SDK pin must use an exact asset digest'


def test_d3_update_token_and_trigger_are_distinct_from_the_readonly_app():
    p = ROOT / '.github/workflows/crysta-sdk-update.yml'
    assert p.is_file(), ' D3 requires the bounded SDK update workflow'
    doc = yaml.safe_load(p.read_text())
    assert doc['permissions'] == {
        'contents': 'write',
        'actions': 'write',
        'pull-requests': 'read',
    }, ' ruling C permits PR inventory only on the update workflow own-repo token'
    trigger = doc.get('on', doc.get(True))
    assert 'schedule' in trigger, ' update needs scheduled and producer triggers'
    assert 'workflow_dispatch' in trigger, ' update needs scheduled and producer triggers'
    text = json.dumps(doc)
    assert any(
        'crysta_sdk_update.py' in step.get('run', '')
        for job in doc['jobs'].values()
        for step in job.get('steps', [])
    ), ' update must push a bounded pin branch and dispatch full CI'
    assert 'workflow_dispatch' in text, (
        ' update must push a bounded pin branch and dispatch full CI'
    )
    assert 'gh pr create' not in text, ' D3 conductor owns opening the update PR'


def test_d2_fleet_pair_lookup_never_masks_an_error_or_requires_gh():
    source = (ROOT / 'tools/ci/crysta-source.sh').read_text()
    assert 'ls-remote' in source, '  pairing must use git branch discovery'
    executable = '\n'.join(
        line for line in source.splitlines() if not line.lstrip().startswith('#')
    )
    assert 'gh ' not in executable, '  fleet paths cannot require gh'
    # Failure propagation is observed by every real lookup mutation below;
    # unrelated optional grep results are not branch-discovery evidence.


@pytest.fixture(scope='module')
def pairing_history(tmp_path_factory):
    root = tmp_path_factory.mktemp('c34-pairing-history')
    build, prescribed = currency_world(root, 'paired-current')
    build._git('checkout', '-qb', 'later-candidate', prescribed)
    (build.sibling / 'later.txt').write_text('another unlanded input\n')
    build._git('add', 'later.txt')
    build._git('commit', '-qm', 'Later unlanded producer')
    other = build._git('rev-parse', 'HEAD').strip()
    return root, build.env, build.git, prescribed, other


def copy_pairing_history(world, history):
    template, template_env, real_git, prescribed, other = history
    shutil.copytree(template, world)
    repo = world / 'edi'
    for config in (world / 'gitconfig', repo / '.git/config', world / 'sibling/.git/config'):
        config.write_text(config.read_text().replace(str(template), str(world)))
    return SimpleNamespace(
        env={k: v.replace(str(template), str(world)) for k, v in template_env.items()},
        git=real_git,
        pin=prescribed,
        other=other,
        edi=repo,
    )


def test_d2_pairing_control_history_is_a_real_unlanded_branch(pairing_history):
    template, _, git, prescribed, other = pairing_history
    root = str(template / 'sibling')
    ancestry = subprocess.run(
        [git, '-C', root, 'merge-base', '--is-ancestor', prescribed, 'main'],
        capture_output=True,
        text=True,
        check=False,
        timeout=2,
    )
    assert ancestry.returncode == 1, (
        ' I26 the pairing control must actually be unlanded on producer main'
    )
    trees = [
        subprocess.check_output([git, '-C', root, 'rev-parse', ref + '^{tree}'], text=True)
        for ref in ('main', prescribed, other)
    ]
    assert len(set(trees)) == 3, (
        ' I26 matching, mismatched and main producer inputs must have distinct real trees'
    )


@pytest.mark.parametrize(
    'lookup',
    [
        'found',
        'absent',
        'error',
        'wrong-pin',
        'second-line',
        'tag-ref',
        'wrong-ref',
        'malformed',
        'short-sha',
    ],
)
def test_d2_pairing_executes_branch_discovery_and_refuses_transport_failure(
    tmp_path, lookup, pairing_history
):
    source = ROOT / 'tools/ci/crysta-source.sh'
    assert 'ls-remote' in source.read_text(), ' I26 requires git-only paired branch discovery'
    # : keep the malformed branch-response controls but let real Git
    # answer the additional ancestry/tree reads from a coherent unlanded graph.

    world = tmp_path / 'world'
    # Every node owns fresh repositories and transport state. Only the immutable
    # source history is shared; all absolute remote addresses move with its copy.
    build = copy_pairing_history(world, pairing_history)
    repo = build.edi
    binpath = world / 'bin'
    calls = tmp_path / 'calls'
    responses = {
        'found': build.pin + '\trefs/heads/paired-topic\n',
        'absent': '',
        'wrong-pin': build.other + '\trefs/heads/paired-topic\n',
        'second-line': build.pin
        + '\trefs/heads/paired-topic\n'
        + build.other
        + '\trefs/heads/paired-topic\n',
        'tag-ref': build.pin + '\trefs/tags/paired-topic\n',
        'wrong-ref': build.pin + '\trefs/heads/other-topic\n',
        'malformed': build.pin + ' refs/heads/paired-topic\n',
        'short-sha': 'abc123\trefs/heads/paired-topic\n',
    }
    response = tmp_path / 'response'
    git = binpath / 'git'
    git.write_text(pair_lookup_program(calls, response))
    git.chmod(0o755)
    for name in ('gh', 'cmake', 'curl'):
        p = binpath / name
        p.write_text(
            '#!/bin/sh\nprintf "%s\\n" "$0 $*" >> "' + str(tmp_path / 'forbidden') + '"\nexit 64\n'
        )
        p.chmod(0o755)
    env = {
        **build.env,
        'PATH': str(binpath) + ':' + str(Path(sys.executable).parent) + ':' + os.defpath,
        'GITHUB_EVENT_NAME': 'pull_request',
        'GITHUB_HEAD_REF': 'paired-topic',
        'PIXI_PROJECT_ROOT': str(repo),
        'PIXI_PLATFORM': 'linux-64',
        'CONDA_SUBDIR': 'linux-64',
        'GITHUB_TOKEN': 'fixture-token',
        'CRYSTA_SDK_TAG': 'build-' + build.pin,
        'FIXTURE_CURRENCY_GIT': build.git,
    }

    def invoke(answer, status=0):
        response.write_text(answer)
        return subprocess.run(
            ['bash', str(repo / 'tools/ci/crysta-source.sh'), '--currency'],
            cwd=repo,
            env={**env, 'FIXTURE_LOOKUP_STATUS': str(status)},
            text=True,
            capture_output=True,
            check=False,
            # Currency now performs real ancestry/tree reads as well as branch
            # discovery. This is an execution watchdog; the runtime ratchet
            # still measures and enforces the integration-tier bound.
            timeout=5,
        )

    control = invoke(responses['found'])
    assert control.returncode == 0, (
        ' I26 matching authenticated branch and pin must admit before each lookup mutation'
    )
    r = invoke(responses.get(lookup, ''), 19 if lookup == 'error' else 0)
    assert calls.exists(), ' I26 pairing gate must actually attempt the named branch lookup'
    assert 'enhantica/crysta' in calls.read_text(), (
        ' I26 lookup must address the declared producer repository'
    )
    assert (r.returncode == 0) == (lookup in {'found', 'wrong-pin', 'absent'}), (
        ' final-green-only intermediate stale or unpaired pins report; '
        'malformed and unread lookups refuse'
    )
    if lookup == 'wrong-pin':
        assert 're-pin' in r.stdout + r.stderr, (
            ' I26 a mismatched paired pin requires the prescribed remedy'
        )
    assert not (tmp_path / 'forbidden').exists(), (
        '  fleet pairing must execute no gh, download or compilation'
    )


@pytest.mark.parametrize('platform', ['linux-64', 'osx-arm64'])
def test_d2_empty_cache_fetches_exact_pinned_asset_without_compilation(tmp_path, platform):
    r, forbidden = consumer(tmp_path, platform=platform, download=True)
    assert r.returncode == 0, ' I26 complete retained SDK asset must admit an empty-cache consumer'
    assert SHA in r.stdout, ' I6 downloaded SDK log must retain source and tree identity'
    assert TREE in r.stdout + r.stderr, (
        ' I6 downloaded SDK log must retain source and tree identity'
    )
    assert not forbidden.exists(), (
        ' I26 fleet download must use no gh, source fetch or compilation'
    )
    calls = (tmp_path / 'downloads').read_text()
    assert '/releases/assets/1001' in calls or f'crysta-sdk-{SHA}-{platform}.tar.gz' in calls, (
        ' I26 empty-cache success must actually request the exact prescribed asset'
    )


@pytest.mark.parametrize('platform', ['linux-64', 'osx-arm64'])
@pytest.mark.parametrize(
    'method',
    [
        '--request=POST',
        '-XPUT',
        '-XDELETE',
        '-dBODY',
        '-FBODY',
        '--data-binary=BODY',
        '--unlisted-selector',
    ],
)
def test_sdk_download_http_method_remains_bound_to_the_addressed_read(tmp_path, platform, method):
    endpoint = 'https://api.github.com/repos/enhantica/crysta/releases/tags/build-' + SHA
    good = tmp_path / 'control'
    good.mkdir()
    result, _ = consumer(
        good,
        platform=platform,
        download=True,
        command_override=(
            'curl -fsSL --retry 3 -H "Authorization: Bearer $GITHUB_TOKEN" '
            '-H "Accept: application/vnd.github+json" ' + endpoint
        ),
    )
    assert result.returncode == 0, ' F4 exact release metadata GET must admit transport'
    bad = tmp_path / 'mutant'
    bad.mkdir()
    result, _ = consumer(
        bad, platform=platform, download=True, command_override='curl ' + method + ' ' + endpoint
    )
    assert result.returncode == 64, ' F4 wrong HTTP operation cannot receive intended SDK metadata'


def pair_lookup_program(calls, response):
    # Real ancestry/tree operations keep their argv and process result without
    # paying a Python interpreter for every Git invocation. Branch selection
    # still passes through the complete Python resource/operation validator.
    return (
        '#!/bin/sh\n'
        'lookup=0; local_repo=0\n'
        'for arg do [ "$arg" = ls-remote ] && lookup=1; '
        '[ "$arg" = -C ] && local_repo=1; done\n'
        'if { [ "$lookup" = 0 ] || [ "$local_repo" = 1 ]; } '
        '&& [ -n "${FIXTURE_CURRENCY_GIT:-}" ]; then\n'
        '  printf "Git argv\\n%s\\n" "$@" >> ' + shlex.quote(str(calls)) + '\n'
        '  exec "$FIXTURE_CURRENCY_GIT" "$@"\n'
        'fi\n'
        'exec '
        + shlex.quote(sys.executable)
        + ' - "$@" <<\'C34_PAIR_LOOKUP\'\n'
        + ('CALLS=' + repr(str(calls)) + '\nRESPONSE=' + repr(str(response)) + '\n')
        + r"""import json, os, sys

args = sys.argv[1:]
with open(CALLS, 'a') as f:
    f.write(json.dumps(args) + '\n')
if 'ls-remote' not in args or '-C' in args:
    if os.environ.get('FIXTURE_CURRENCY_GIT'):
        real_git = os.environ['FIXTURE_CURRENCY_GIT']
        os.execv(real_git, [real_git, *args])
    sys.exit(64)
from pathlib import Path
from urllib.parse import urlsplit

i = args.index('ls-remote')
a = args[i + 1 :]
if any(x.startswith('-') and x != '--heads' for x in a):
    sys.exit(64)
if args[:i] not in ([], ['-c', 'http.https://github.com/.extraheader=']):
    sys.exit(64)
values = [x for x in a if not x.startswith('-')]
if len(values) != 2:
    sys.exit(64)
url = urlsplit(values[0])
if (
    url.scheme != 'https'
    or url.hostname != 'github.com'
    or url.port not in (None, 443)
    or url.path.removesuffix('.git') != '/enhantica/crysta'
    or url.query
    or url.fragment
    or values[1] != 'refs/heads/paired-topic'
):
    sys.exit(64)
print(Path(RESPONSE).read_text(), end='')
sys.exit(int(os.getenv('FIXTURE_LOOKUP_STATUS', '0')))
C34_PAIR_LOOKUP
"""
    )


@pytest.mark.parametrize(
    'args',
    [
        [
            'ls-remote',
            '--heads',
            'https://notgithub.com/enhantica/crysta',
            'refs/heads/paired-topic',
        ],
        ['ls-remote', '--heads', 'https://github.com/other/crysta', 'refs/heads/paired-topic'],
        ['ls-remote', '--heads', 'https://github.com/enhantica/c' + 'rysta', 'refs/heads/wrong'],
        [
            'ls-remote',
            '--tags',
            'https://github.com/enhantica/c' + 'rysta',
            'refs/heads/paired-topic',
        ],
        [
            'fetch',
            '--heads',
            'https://github.com/enhantica/c' + 'rysta',
            'refs/heads/paired-topic',
        ],
        [
            'fetch',
            'ls-remote',
            'https://github.com/enhantica/c' + 'rysta',
            'refs/heads/paired-topic',
        ],
    ],
)
def test_pairing_git_transport_binds_host_repo_ref_and_operation(tmp_path, args):
    response = tmp_path / 'response'
    response.write_text(SHA + '\trefs/heads/paired-topic\n')
    entry = tmp_path / 'git'
    entry.write_text(pair_lookup_program(tmp_path / 'calls', response))
    entry.chmod(0o755)
    good = subprocess.run(
        [
            str(entry),
            'ls-remote',
            '--heads',
            'https://x-access-token:fixture@github.com/enhantica/crysta.git',
            'refs/heads/paired-topic',
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=2,
    )
    assert good.returncode == 0, (
        ' I26 exact authenticated producer branch resource must admit transport'
    )
    assert good.stdout == response.read_text(), (
        ' I26 exact authenticated producer branch resource must admit transport'
    )
    plain = subprocess.run(
        [
            str(entry),
            'ls-remote',
            'https://github.com/enhantica/c' + 'rysta',
            'refs/heads/paired-topic',
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=2,
    )
    assert plain.returncode == 0 and plain.stdout == response.read_text(), (
        ' I26 the exact heads ref is a complete selection without an optional heads flag'
    )
    bad = subprocess.run(
        [str(entry), *args], capture_output=True, text=True, check=False, timeout=2
    )
    assert bad.returncode == 64, (
        ' I26 wrong host, repo, ref or operation cannot receive the paired branch'
    )
    assert not bad.stdout, (
        ' I26 wrong host, repo, ref or operation cannot receive the paired branch'
    )


@pytest.mark.parametrize('platform', ['linux-64', 'osx-arm64'])
@pytest.mark.parametrize('route', ['metadata', 'asset-api', 'asset-browser'])
def test_sdk_download_every_route_binds_resource_operation_and_representation(
    tmp_path, platform, route
):
    base = 'https://api.github.com/repos/enhantica/crysta/releases/'
    address = (
        base + 'tags/build-' + SHA
        if route == 'metadata'
        else base + 'assets/1001'
        if route == 'asset-api'
        else 'https://fixture.invalid/crysta-sdk-' + SHA + '-' + platform + '.tar.gz'
    )
    header = 'application/vnd.github+json' if route == 'metadata' else 'application/octet-stream'
    command = (
        'curl -fsSL --retry 3 -H "Authorization: Bearer $GITHUB_TOKEN" '
        '-H "Accept: ' + header + '" -o "$DOWNLOAD_FIXTURE/selected" ' + address
    )
    control = tmp_path / 'control'
    control.mkdir()
    result, _ = consumer(control, platform=platform, download=True, command_override=command)
    assert result.returncode == 0, (
        ' I26 every retained download route must admit its addressed read control'
    )
    mutants = {
        'resource': command.replace('api.github.com', 'notgithub.com')
        if route != 'asset-browser'
        else command.replace(platform, 'wrong-platform'),
        'operation': command.replace('curl', 'curl -X DELETE', 1),
    }
    if route == 'asset-api':
        mutants['representation'] = command.replace('application/octet-stream', 'application/json')
    for defect, mutant in mutants.items():
        bad = tmp_path / defect
        bad.mkdir()
        result, _ = consumer(bad, platform=platform, download=True, command_override=mutant)
        assert result.returncode == 64, (
            ' I26 wrong resource, operation or representation cannot supply SDK bytes'
        )
