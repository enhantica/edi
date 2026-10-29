"T1: the required Linux core step reaches the two-thread sanitizer witness."

import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


def test_sanitizer_has_a_declared_task_and_required_linux_ci_step():
    manifest = tomllib.loads((ROOT / 'pixi.toml').read_text())
    assert 'tsan-worker' in manifest.get('tasks', {}), (
        ' T1 sanitizer witness is a reproducible declared core task'
    )
    workflow = (ROOT / '.github/workflows/ci.yml').read_text()
    assert 'tsan-worker' in workflow, (
        ' T1 the required Linux core CI job invokes the sanitizer task'
    )
    script = ROOT / 'tools/ci/tsan-worker.sh'
    assert script.is_file(), (
        ' T1 the declared script builds both pinned crysta and edi under ThreadSanitizer'
    )
    text = script.read_text()
    assert 'e04_t9_tsan_probe' in text and 'fsanitize=thread' in text, (
        ' T1 instrumentation reaches the hidden two-thread witness executable'
    )
    assert 'OMP_NUM_THREADS=1' in text, (
        ' T1 the declared witness runs with the specified single OpenMP worker'
    )


# These gates execute only source selection. The FIRST SDK bridge and real Git
# stay real; the external SDK acquisition/check boundary and first CMake
# configure are intercepted. No sanitizer, compiler or native code is run.


def _commit_tsan_source(source, name, git, git_env):
    source.mkdir(parents=True, exist_ok=True)
    if not (source / '.git').exists():
        subprocess.run([git, '-C', str(source), 'init', '-q'], env=git_env, check=True)
    (source / 'CMakeLists.txt').write_text('# ' + name + '\n')
    subprocess.run([git, '-C', str(source), 'add', 'CMakeLists.txt'], env=git_env, check=True)
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


def _tsan_source_fixture(tmp_path):
    subject = Path(
        os.environ.get(
            'EDI_TSAN_WORKER_UNDER_TEST',
            Path(os.environ.get('EDI_TSAN_WORKER_SOURCE_REPO', ROOT)).resolve()
            / 'tools/ci/tsan-worker.sh',
        )
    ).resolve(strict=True)
    root = tmp_path / 'edi'
    scripts = root / 'tools/ci'
    scripts.mkdir(parents=True)
    for name in ('build-crysta.sh', 'producer-lock.sh'):
        shutil.copyfile(
            Path(os.environ.get('EDI_TSAN_WORKER_SOURCE_REPO', ROOT)).resolve()
            / 'tools/ci'
            / name,
            scripts / name,
        )
    shutil.copyfile(subject, scripts / 'tsan-worker.sh')
    assert (scripts / 'tsan-worker.sh').read_bytes() == subject.read_bytes(), (
        'The actual selected script must execute unchanged, never an extra'
        'cted/reimplemented branch'
    )
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
    (scripts / 'crysta-src.sh').write_text(
        '#!/usr/bin/env bash\n'
        'set -eu\n'
        'printf \'{"entry":"source-acquisition"}\\n\' >> "$TSAN_SELECTION_TRACE"\n'
        '# The real pre-created pinned Git tree is retained unchanged.\n'
    )
    (mockbin / 'python').write_text('#!/bin/sh\nexec ' + shlex.quote(sys.executable) + ' "$@"\n')
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
        )
    )
    (mockbin / 'cmake').chmod(0o755)
    git = shutil.which('git')
    assert git, 'Source selection requires the actual local Git executable, never a Git reply mock'
    git_env = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
    git_env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull)

    candidate = tmp_path / 'candidate'
    candidate_sha = _commit_tsan_source(candidate, 'candidate source', git, git_env)
    pinned = root / 'build/crysta-src'
    pinned_sha = _commit_tsan_source(pinned, 'pinned original source', git, git_env)
    (pinned / 'CRYSTA_SOURCE_SHA').write_text(pinned_sha + '\n')
    sdk = tmp_path / 'sdk'
    (sdk / 'share/crysta-sdk').mkdir(parents=True)
    (sdk / 'share/crysta-sdk/manifest.json').write_text(json.dumps({'source_sha': candidate_sha}))
    cache = root / 'build/tsan'
    for relative, data in {
        'crysta/original-cache': b'original instrumented source cache\n',
        'prefix/original-cache': b'original instrumented prefix cache\n',
        'prefix/.crysta-sha': b'unrelated prior source\n',
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
    return (
        root,
        candidate,
        candidate_sha,
        pinned,
        pinned_sha,
        sdk,
        trace,
        cache,
        before,
        env,
        lambda source, name: _commit_tsan_source(source, name, git, git_env),
        subject,
    )


@pytest.mark.skipif(
    not sys.platform.startswith('linux'), reason='The original TSAN source selector is Linux-only'
)
@pytest.mark.parametrize('route', ['candidate', 'pinned'])
def test_tsan_worker_selects_exact_original_source_before_instrumented_configure(tmp_path, route):
    (
        root,
        candidate,
        _,
        pinned,
        pinned_sha,
        sdk,
        trace,
        _,
        _,
        env,
        _,
        subject,
    ) = _tsan_source_fixture(tmp_path)
    if route == 'candidate':
        env.update(CRYSTA_SDK_DIR=str(sdk), CRYSTA_CONSUMER_SRC=str(candidate))
    else:
        # The mock external SDK entry now describes the original pinned SDK.
        (sdk / 'share/crysta-sdk/manifest.json').write_text(json.dumps({'source_sha': pinned_sha}))
    result = subprocess.run(
        ['bash', 'tools/ci/tsan-worker.sh'],
        cwd=root,
        env=env,
        text=True,
        capture_output=True,
        timeout=15,
        check=False,
    )
    events = [json.loads(line) for line in trace.read_text().splitlines()]
    configured = [row for row in events if row['entry'] == 'cmake']
    assert any(row['entry'] == 'sdk' for row in events), (
        'The unchanged FIRST SDK source-validation bridge must execute before configure'
    )
    evidence = {
        'route': route,
        'subject': str(subject),
        'subject_sha256': hashlib.sha256(subject.read_bytes()).hexdigest(),
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
    expected = candidate if route == 'candidate' else pinned
    assert arguments[:2] == ['-S', str(expected.resolve())], (
        'The instrumented configure must receive the actual qualified cons'
        'umer source, or unchanged pinned source: '
    ) + json.dumps(evidence)
    assert any(
        value.startswith('-DCMAKE_CXX_FLAGS=') and '-fsanitize=thread' in value
        for value in arguments
    ), (
        'The reached boundary must be the original instrumented native con'
        'figure, not another command: '
    ) + json.dumps(evidence)
    assert 'SOURCE_SELECTION_CONFIGURE_STOP' in result.stdout + result.stderr, (
        'This test ends at the mock configure boundary; a fake successful '
        'TSAN report cannot count: '
    ) + json.dumps(evidence)


@pytest.mark.skipif(
    not sys.platform.startswith('linux'), reason='The original TSAN source selector is Linux-only'
)
@pytest.mark.parametrize('invalid', ['missing-source', 'wrong-sha', 'tracked-modification'])
def test_tsan_worker_refuses_unqualified_candidate_before_tsan_cache_mutation(tmp_path, invalid):
    root, candidate, _, _, _, sdk, trace, cache, before, env, commit, subject = (
        _tsan_source_fixture(tmp_path)
    )
    env['CRYSTA_SDK_DIR'] = str(sdk)
    if invalid != 'missing-source':
        env['CRYSTA_CONSUMER_SRC'] = str(candidate)
    if invalid == 'wrong-sha':
        commit(candidate, 'source moved after SDK build')
    elif invalid == 'tracked-modification':
        with (candidate / 'CMakeLists.txt').open('a') as output:
            output.write('# tracked source changed after SDK build\n')
    result = subprocess.run(
        ['bash', 'tools/ci/tsan-worker.sh'],
        cwd=root,
        env=env,
        text=True,
        capture_output=True,
        timeout=15,
        check=False,
    )
    events = (
        [json.loads(line) for line in trace.read_text().splitlines()] if trace.exists() else []
    )
    after = {str(p.relative_to(cache)): p.read_bytes() for p in cache.rglob('*') if p.is_file()}
    evidence = {
        'case': invalid,
        'subject': str(subject),
        'subject_sha256': hashlib.sha256(subject.read_bytes()).hexdigest(),
        'returncode': result.returncode,
        'events': events,
        'stderr': result.stderr,
        'stdout': result.stdout,
    }
    assert result.returncode != 0 and not any(row['entry'] == 'cmake' for row in events), (
        'Missing, mismatched or tracked-modified candidate source must ref'
        'use before instrumented configure: '
    ) + json.dumps(evidence)
    assert after == before, (
        'A refused candidate cannot erase or replace any preexisting TSAN cache/prefix byte: '
    ) + json.dumps(evidence)
    assert result.stderr.strip() or result.stdout.strip(), (
        'Source qualification must refuse explicitly rather than silently skipping the gate: '
    ) + json.dumps(evidence)
