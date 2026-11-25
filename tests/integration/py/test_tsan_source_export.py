"""The ThreadSanitizer source gate reaches the real pinned export before configure."""

import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.fixtures.native_process import environment_bash

ROOT = Path(__file__).resolve().parents[3]


# These gates execute only source selection. The FIRST SDK bridge and real Git
# stay real; the external SDK acquisition/check boundary and first CMake
# configure are intercepted. No sanitizer, compiler or native code is run.


def _commit_tsan_source(source, name, git, git_env):
    source.mkdir(parents=True, exist_ok=True)
    if not (source / '.git').exists():
        subprocess.run([git, '-C', str(source), 'init', '-q'], env=git_env, check=True)
    (source / 'CMakeLists.txt').write_text('# ' + name + '\n')
    for path, declaration in (
        ('tests/fixtures/web_simd/build.py', 'PATHS'),
        ('tests/fixtures/web_parallel/build.py', 'SOURCE_PATHS'),
    ):
        builder = source / path
        builder.parent.mkdir(parents=True, exist_ok=True)
        builder.write_text(f'{declaration} = ("CMakeLists.txt",)\n')
    subprocess.run(
        [git, '-C', str(source), 'add', 'CMakeLists.txt', 'tests'], env=git_env, check=True
    )
    subprocess.run(
        [
            git,
            '-C',
            str(source),
            '-c',
            'core.hooksPath=/dev/null',
            '-c',
            'user.name=Source fixture',
            '-c',
            'user.email=source@example.invalid',
            'commit',
            '-qm',
            name,
        ],
        env=git_env,
        check=True,
    )
    return subprocess.check_output(
        [git, '-C', str(source), 'rev-parse', 'HEAD'], env=git_env, text=True
    ).strip()


def write_sdk_source(sdk, source, pin, env):
    tree = subprocess.check_output(
        ['git', '-C', str(source), 'rev-parse', f'{pin}^{{tree}}'],
        env=env,
        text=True,
    ).strip()
    manifest = sdk / 'share/crysta-sdk/manifest.json'
    manifest.write_text(json.dumps({'source_sha': pin, 'source_tree': tree}))
    return manifest


def copy_tsan_scripts(root):
    subject = Path(
        os.environ.get(
            'EDI_TSAN_WORKER_UNDER_TEST',
            Path(os.environ.get('EDI_TSAN_WORKER_SOURCE_REPO', ROOT)).resolve()
            / 'tools/ci/tsan-worker.sh',
        )
    ).resolve(strict=True)
    scripts = root / 'tools/ci'
    scripts.mkdir(parents=True)
    tool_source = Path(os.environ.get('EDI_TSAN_WORKER_SOURCE_REPO', ROOT)).resolve() / 'tools/ci'
    for name in (
        'build-crysta.sh',
        'producer-lock.sh',
        'crysta-src.sh',
        'crysta_source_export.py',
        'crysta_source_tree.py',
        'crysta_source_receipt.py',
        'portable_paths.py',
        'source_lists.py',
    ):
        shutil.copyfile(tool_source / name, scripts / name)
    shutil.copyfile(subject, scripts / 'tsan-worker.sh')
    assert (scripts / 'tsan-worker.sh').read_bytes() == subject.read_bytes(), (
        'The actual selected script must execute unchanged, never an extra'
        'cted/reimplemented branch'
    )
    return subject, scripts


def _tsan_source_fixture(tmp_path):
    root = tmp_path / 'edi'
    subject, scripts = copy_tsan_scripts(root)
    (root / 'tests/unit/cpp').mkdir(parents=True)
    (root / 'tests/unit/cpp/e04_t9_tsan_probe.cpp').write_text(
        '// A presence witness only: this test never compiles it.\n'
    )
    trace = tmp_path / 'external-boundaries.jsonl'
    mockbin = tmp_path / 'bin'
    mockbin.mkdir()
    # The original SDK bridge parses the manifest and verifies the actual Git
    # source itself. Only its external acquisition/fingerprint entry is mocked.
    (scripts / 'crysta_sdk.py').write_text(
        'import json,os,sys\nwith open(os.environ["TSAN_SELECTION_TRAC'
        'E"],"a") as f: print(json.dumps({"entry":"sdk","argv":sys.ar'
        'gv[1:]}),file=f)\nprint("crysta: source-selection-only mock S'
        'DK entry; NOT artifact qualification")\nprint(os.environ["TSA'
        'N_SELECTION_SDK"])\n'
    )
    (mockbin / 'python').write_text(
        '#!/bin/sh\nexec ' + shlex.quote(sys.executable) + ' "$@"\n', newline='\n'
    )
    (mockbin / 'python').chmod(0o755)
    (mockbin / 'cmake').write_text(
        '#!'
        + sys.executable
        + '\n'
        + (
            'import json,os,sys\nwith open(os.environ["TSAN_SELECTION_TRAC'
            'E"],"a") as f: print(json.dumps({"entry":"cmake","argv":sys.'
            'argv[1:]}),file=f)\nprint("SOURCE_SELECTION_CONFIGURE_STOP: n'
            'o configure/build/TSAN executed")\nsys.exit(86)\n'
        ),
        newline='\n',
    )
    (mockbin / 'cmake').chmod(0o755)
    git = shutil.which('git')
    assert git, 'Source selection requires the actual local Git executable, never a Git reply mock'
    git_env = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
    git_env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull)

    candidate = tmp_path / 'candidate'
    candidate_sha = _commit_tsan_source(candidate, 'candidate source', git, git_env)
    pinned = tmp_path / 'pinned'
    pinned_sha = _commit_tsan_source(pinned, 'pinned original source', git, git_env)
    sdk = tmp_path / 'sdk'
    (sdk / 'share/crysta-sdk').mkdir(parents=True)
    write_sdk_source(sdk, candidate, candidate_sha, git_env)
    cache = root / 'build/tsan'
    for relative, data in {
        'crysta/original-cache': b'original instrumented source cache\n',
        'prefix/original-cache': b'original instrumented prefix cache\n',
        'prefix/.crysta-sha': b'unrelated prior source\n',
        'source/prior': b'previous instrumented source export\n',
    }.items():
        (cache / relative).parent.mkdir(parents=True, exist_ok=True)
        (cache / relative).write_bytes(data)
    before = {str(p.relative_to(cache)): p.read_bytes() for p in cache.rglob('*') if p.is_file()}
    env = {
        **git_env,
        'PATH': str(mockbin) + os.pathsep + os.environ.get('PATH', ''),
        'PIXI_ENVIRONMENT_NAME': 'default',
        'PIXI_PLATFORM': 'linux-64',
        'TSAN_SELECTION_TRACE': str(trace),
        'TSAN_SELECTION_SDK': str(sdk),
    }
    for key in (
        'CRYSTA_SDK_DIR',
        'CRYSTA_CONSUMER_SRC',
        'EDI_PRODUCER_LOCK_HELD',
        'PYTEST_XDIST_WORKER',
        'RUNNER_TEMP',
        'BASH_ENV',
        'ENV',
    ):
        env.pop(key, None)
    env['CRYSTA_SRC'] = str(pinned)
    return SimpleNamespace(
        root=root,
        candidate=candidate,
        candidate_sha=candidate_sha,
        pinned=pinned,
        pinned_sha=pinned_sha,
        sdk=sdk,
        trace=trace,
        cache=cache,
        before=before,
        env=env,
        commit=lambda source, name: _commit_tsan_source(source, name, git, git_env),
        subject=subject,
    )


@pytest.mark.skipif(
    not sys.platform.startswith('linux'), reason='The original TSAN source selector is Linux-only'
)
@pytest.mark.parametrize('route', ['candidate', 'pinned'])
def test_tsan_worker_selects_exact_original_source_before_instrumented_configure(tmp_path, route):
    fixture = _tsan_source_fixture(tmp_path)
    checkout, pin = (
        (fixture.candidate, fixture.candidate_sha)
        if route == 'candidate'
        else (fixture.pinned, fixture.pinned_sha)
    )
    expected_bytes = subprocess.check_output(
        ['git', '-C', str(checkout), 'show', f'{pin}:CMakeLists.txt'], env=fixture.env
    )
    if route == 'candidate':
        fixture.env.update(
            CRYSTA_SDK_DIR=str(fixture.sdk), CRYSTA_CONSUMER_SRC=str(fixture.candidate)
        )
        fixture.commit(fixture.candidate, 'advance the working checkout')
        (fixture.candidate / 'CMakeLists.txt').write_text('# dirty checkout bytes\n')
        (fixture.candidate / 'untracked.txt').write_text('never export this file\n')
    else:
        write_sdk_source(fixture.sdk, fixture.pinned, fixture.pinned_sha, fixture.env)
    result = subprocess.run(
        [environment_bash(), 'tools/ci/tsan-worker.sh'],
        cwd=fixture.root,
        env=fixture.env,
        text=True,
        capture_output=True,
        timeout=15,
        check=False,
    )
    events = [json.loads(line) for line in fixture.trace.read_text().splitlines()]
    configured = [row for row in events if row['entry'] == 'cmake']
    assert any(row['entry'] == 'sdk' for row in events), (
        'The unchanged FIRST SDK source-validation bridge must execute before configure'
    )
    evidence = {
        'route': route,
        'subject': str(fixture.subject),
        'subject_sha256': hashlib.sha256(fixture.subject.read_bytes()).hexdigest(),
        'returncode': result.returncode,
        'events': events,
        'stderr': result.stderr,
        'stdout': result.stdout,
    }
    assert result.returncode != 0 and len(configured) == 1, (
        'The source-only gate must reach exactly one intercepted configure'
        ' and stop before any native build: '
    ) + json.dumps(evidence)
    arguments = configured[0]['argv']
    expected = fixture.root / ('build/tsan/source' if route == 'candidate' else 'build/crysta-src')
    assert arguments[:2] == ['-S', str(expected.resolve())], (
        'The instrumented configure must receive the actual qualified cons'
        'umer source, or unchanged pinned source: '
    ) + json.dumps(evidence)
    assert (expected / 'CMakeLists.txt').read_bytes() == expected_bytes and (
        not (expected / 'untracked.txt').exists()
    ), 'Sanitizer source comes from the SDK commit after the checkout moves or gets dirty'
    assert any(
        value.startswith('-DCMAKE_CXX_FLAGS=') and '-fsanitize=thread' in value
        for value in arguments
    ), (
        'The reached boundary must be the original instrumented native con'
        'figure, not another command: '
    ) + json.dumps(evidence)
    log = fixture.root / 'build/tsan.configure.log'
    assert (
        'SOURCE_SELECTION_CONFIGURE_STOP' in log.read_text()
        and 'configure failed (exit 86)' in result.stderr
        and 'SOURCE_SELECTION_CONFIGURE_STOP' not in result.stdout + result.stderr
    ), 'The reached mock configure failure is retained locally and filtered from public output'


@pytest.mark.skipif(
    not sys.platform.startswith('linux'), reason='The original TSAN source selector is Linux-only'
)
@pytest.mark.parametrize('invalid', ['missing-source', 'missing-commit', 'wrong-tree'])
def test_tsan_worker_refuses_unqualified_candidate_before_tsan_cache_mutation(tmp_path, invalid):
    fixture = _tsan_source_fixture(tmp_path)
    fixture.env['CRYSTA_SDK_DIR'] = str(fixture.sdk)
    if invalid != 'missing-source':
        fixture.env['CRYSTA_CONSUMER_SRC'] = str(
            fixture.pinned if invalid == 'missing-commit' else fixture.candidate
        )
    if invalid == 'wrong-tree':
        manifest = fixture.sdk / 'share/crysta-sdk/manifest.json'
        options = json.loads(manifest.read_text())
        options['source_tree'] = '0' * 40
        manifest.write_text(json.dumps(options))
    result = subprocess.run(
        [environment_bash(), 'tools/ci/tsan-worker.sh'],
        cwd=fixture.root,
        env=fixture.env,
        text=True,
        capture_output=True,
        timeout=15,
        check=False,
    )
    events = (
        [json.loads(line) for line in fixture.trace.read_text().splitlines()]
        if fixture.trace.exists()
        else []
    )
    after = {
        str(p.relative_to(fixture.cache)): p.read_bytes()
        for p in fixture.cache.rglob('*')
        if p.is_file()
    }
    evidence = {
        'case': invalid,
        'subject': str(fixture.subject),
        'subject_sha256': hashlib.sha256(fixture.subject.read_bytes()).hexdigest(),
        'returncode': result.returncode,
        'events': events,
        'stderr': result.stderr,
        'stdout': result.stdout,
    }
    assert result.returncode != 0 and not any(row['entry'] == 'cmake' for row in events), (
        'An unavailable SDK commit or an incorrect tree must refuse before configure: '
    ) + json.dumps(evidence)
    assert after == fixture.before, (
        'A refused candidate cannot erase or replace any preexisting TSAN cache/prefix byte: '
    ) + json.dumps(evidence)
    assert result.stderr.strip() or result.stdout.strip(), (
        'Source qualification must refuse explicitly rather than silently skipping the gate: '
    ) + json.dumps(evidence)
