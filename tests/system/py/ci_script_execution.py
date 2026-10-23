"""Compare shell work in isolated trees with recorded external command boundaries."""

from __future__ import annotations

import ast
import json
import re
import subprocess
import tempfile
from functools import lru_cache
from pathlib import Path

OBSERVED = {'tools/ci/core-build.sh', 'tools/ci/crysta-src.sh'}
SHA = '1' * 40
FROZEN = json.loads(
    (
        Path(__file__).resolve().parents[3] / 'tests/fixtures/ci_cadence/shipped-policy.json'
    ).read_text()
)['execution_sources']

COMMAND = r"""#!/bin/bash
set -eu
name=${0##*/}
printf '%s' "$name" >> "$CALLS"
printf ' <%s>' "$@" >> "$CALLS"
printf '\n' >> "$CALLS"
lock_present=0; token_present=0; owner_present=0; matched=0
[ ! -d "$LOCK_PATH" ] || lock_present=1
[ -z "${EDI_PRODUCER_LOCK_HELD:-}" ] || token_present=1
owner=''
if [ -f "$LOCK_PATH/owner" ]; then IFS= read -r owner < "$LOCK_PATH/owner" || true; fi
[ -z "$owner" ] || owner_present=1
[ "$token_present" = 0 ] || [ "$owner" != "$EDI_PRODUCER_LOCK_HELD" ] || matched=1
printf 'ownership <%s> <%s> <%s> <%s>\n' "$lock_present" "$token_present" \
  "$owner_present" "$matched" >> "$CALLS"
case "$name $*" in
  *"$FAIL"*) [ -z "$FAIL" ] || exit 23 ;;
esac
case "$name" in
  cmake)
    if [ "$1" = -S ]; then mkdir -p "$4"; fi ;;
  python)
    case "$1" in
      tools/ci/crysta_sdk.py) printf 'crysta: isolated SDK\n%s\n' "$SDK" ;;
      -c) printf '%s\n' "$HEAD_SHA" ;;
    esac ;;
  git)
    case " $* " in
      *' rev-parse HEAD '*) printf '%s\n' "$HEAD_SHA" ;;
      *' cat-file '*) [ "$OBJECT_PRESENT" = 1 ] ;;
    esac ;;
esac
"""


def _prepare_scripts(root, path, source):
    scripts = root / 'tools/ci'
    scripts.mkdir(parents=True)
    (root / 'CMakeLists.txt').touch()
    (scripts / Path(path).name).write_text(source)
    for name in ('build-crysta.sh', 'crysta-src.sh'):
        if name != Path(path).name:
            (scripts / name).write_text(
                '#!/bin/bash\nset -e\nboundary '
                + name
                + '\nexec /bin/bash tools/ci/observed-'
                + name
                + '\n'
            )
            (scripts / ('observed-' + name)).write_text(FROZEN['tools/ci/' + name])
    (scripts / 'producer-lock.sh').write_text(FROZEN['tools/ci/producer-lock.sh'])
    (scripts / 'crysta-source.sh').write_text(
        'crysta_url() { echo https://example.invalid/crysta; }\n'
        'crysta_remote() { shift; git "$@"; }\n'
        '_crysta_redact() { printf "%s" "$1"; }\n'
        'CRYSTA_REMOTE_OUT=refused\nCRYSTA_REMOTE_ERR=refused\n'
    )
    sdk = root / 'sdk/share/crysta-sdk'
    sdk.mkdir(parents=True)
    (sdk / 'manifest.json').write_text(json.dumps({'source_sha': SHA}))


def _plant_lock(root, scenario, env):
    if scenario.startswith('inherited-') or scenario == 'foreign-lock':
        lock = root / 'build/.core-build.lock.d'
        lock.mkdir()
        if scenario != 'inherited-missing-owner':
            (lock / 'owner').write_text('parent-token\n')
        if scenario != 'foreign-lock':
            env['EDI_PRODUCER_LOCK_HELD'] = 'parent-token'
        if scenario == 'inherited-wrong-token':
            env['EDI_PRODUCER_LOCK_HELD'] = 'wrong-token'
        elif scenario == 'inherited-missing-token':
            env.pop('EDI_PRODUCER_LOCK_HELD')
        elif scenario == 'inherited-wrong-owner':
            (lock / 'owner').write_text('wrong-owner\n')
    elif scenario == 'standalone-token':
        env['EDI_PRODUCER_LOCK_HELD'] = 'unproven-token'


def observe(path, source, scenario, failure=''):
    # Bash ignores leading comments; share their identical command observations.
    while source.startswith('#'):
        source = source.partition('\n')[2]
    return _observe(path, source, scenario, failure)


@lru_cache(maxsize=512)
def _observe(path, source, scenario, failure=''):
    with tempfile.TemporaryDirectory(prefix='ci-script-') as temporary:
        root = Path(temporary)
        _prepare_scripts(root, path, source)
        prefix = root / 'build/crysta-prefix'
        prefix.mkdir(parents=True)
        if scenario != 'missing-stamp':
            (prefix / '.crysta-sha').write_text(SHA + '\n')
        consumer = root / 'build/crysta-consumer-prefix'
        consumer.mkdir()
        (consumer / '.crysta-sha').write_text(SHA + '\n')
        src = root / 'build/crysta-src'
        src.mkdir()
        if scenario in {'cached', 'cached-witness', 'stale-head', 'object-present'}:
            (src / '.git').mkdir()
            (src / 'CRYSTA_SOURCE_SHA').write_text(SHA + '\n')
        if scenario in {'witness', 'cached-witness'}:
            witness = src / 'tests/fixtures/web_simd/fork/reference.mjs'
            witness.parent.mkdir(parents=True)
            witness.write_text("export const BASE='" + '2' * 40 + "';\n")
        bin_dir = root / 'bin'
        bin_dir.mkdir()
        for name in ('cmake', 'git', 'boundary', 'python'):
            program = bin_dir / name
            program.write_text(COMMAND)
            program.chmod(0o755)
        env = {
            'PATH': str(bin_dir) + ':/usr/bin:/bin',
            'CALLS': str(root / 'calls'),
            'FAIL': failure,
            'HEAD_SHA': 'stale' if scenario == 'stale-head' else SHA,
            'OBJECT_PRESENT': '1' if scenario in {'cached', 'object-present'} else '0',
            'EDI_CORE_BUILD_LOCK_WAIT_S': '0',
            'EDI_CORE_TARGETS': 'edi_tests extra_target',
            'LOCK_PATH': str(root / 'build/.core-build.lock.d'),
            'SDK': str(root / 'sdk'),
            'PIXI_PLATFORM': 'linux-64',
            'PIXI_ENVIRONMENT_NAME': 'default',
        }
        if scenario == 'consumer':
            env.update(CRYSTA_SDK_DIR=str(consumer), EDI_USE_CONSUMER_BUILD='1')
        elif scenario == 'artifact':
            env['EDI_NATIVE_ARTIFACT'] = '1'
        elif scenario == 'held-lock':
            (root / 'build/.core-build.lock.d').mkdir()
        elif scenario == 'consumer-invalid':
            env['CRYSTA_SDK_DIR'] = str(consumer)
        elif scenario == 'worker':
            env['PYTEST_XDIST_WORKER'] = 'gw0'
        _plant_lock(root, scenario, env)
        result = subprocess.run(
            ['/bin/bash', path], cwd=root, env=env, capture_output=True, timeout=2, check=False
        )
        calls = root / 'calls'
        trace = (
            calls.read_text().replace(str(root), '<root>').splitlines() if calls.exists() else []
        )
        outputs = tuple(
            (name, (root / name).read_text() if (root / name).exists() else None)
            for name in (
                'build/ci/.crysta-linked-sha',
                'build/ci-consumer/.crysta-linked-sha',
                'build/crysta-src/CRYSTA_SOURCE_SHA',
            )
        )
        lock = root / 'build/.core-build.lock.d'
        outputs += (('producer-lock-retained', lock.exists()),)
        outputs += (('producer-owner-retained', (lock / 'owner').exists()),)
        return result.returncode, tuple(trace), outputs


def platform_source(path, source):
    """Normalize correct retired aliases, preserving every other source operation."""
    if path == 'tools/ci/build-crysta.sh':
        source = re.sub(
            r'(?m)^(  linux-64 \| )linux-64-app \| '
            r'(?=Linux-X64 \| Linux-x86_64\) PLATFORM=linux-64 ;;$)',
            r'\1',
            source,
        )
        source = re.sub(
            r'(?m)^(  osx-arm64 \| )osx-arm64-app \| '
            r'(?=macOS-ARM64 \| Darwin-arm64\) PLATFORM=osx-arm64 ;;$)',
            r'\1',
            source,
        )
        source = re.sub(
            r'(?m)(^  osx-arm64 \| macOS-ARM64 \| Darwin-arm64\) PLATFORM=osx-arm64 ;;\n)'
            r'  osx-arm64-app\) PLATFORM=osx-arm64 ;;(?:  #[^\n]*)?\n',
            r'\1',
            source,
        )
        return '\n'.join(line for line in source.splitlines() if not line.lstrip().startswith('#'))
    tree = ast.parse(source)
    function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == 'sdk_platform'
    )
    start = next(
        i
        for i, node in enumerate(function.body)
        if isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
        and node.targets[0].id == 'table'
    )
    entries = []
    end = start
    for node in function.body[start:]:
        if end != start and not (
            isinstance(node, ast.AugAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == 'table'
            and isinstance(node.op, ast.BitOr)
        ):
            break
        if not isinstance(node.value, ast.Dict):
            raise TypeError('platform table must remain a literal mapping')
        entries.extend(zip(node.value.keys, node.value.values, strict=True))
        end += 1
    # Flatten adjacent literal updates without discarding duplicate keys or evaluation order.
    entries = [
        (key, value)
        for key, value in entries
        if not (
            isinstance(key, ast.Constant)
            and isinstance(value, ast.Constant)
            and (key.value, value.value)
            in {('linux-64-app', 'linux-64'), ('osx-arm64-app', 'osx-arm64')}
        )
    ]
    function.body[start].value = ast.Dict(
        keys=[key for key, _ in entries], values=[value for _, value in entries]
    )
    del function.body[start + 1 : end]
    return ast.dump(tree, include_attributes=False)


def accepted_remote_source(baseline, actual):
    accepted = json.loads(
        (
            Path(__file__).resolve().parents[3]
            / 'tests/fixtures/ci_cadence/accepted-remote-streams.json'
        ).read_text()
    )
    return baseline == accepted['before'] and actual == accepted['after']


def retains_work(path, baseline, actual):
    if baseline == actual or path in {
        'tools/ci/crysta-source.sh',
        'tools/ci/build-crysta.sh',
        'tools/ci/edi_native.py',
    }:
        try:
            return baseline == actual or (
                accepted_remote_source(baseline, actual)
                if path == 'tools/ci/crysta-source.sh'
                else platform_source(path, baseline) == platform_source(path, actual)
            )
        except (SyntaxError, StopIteration, TypeError, ValueError):
            return False
    if path not in OBSERVED:
        return False
    if path.endswith('core-build.sh'):
        scenarios = ('fresh', 'consumer', 'artifact', 'worker', 'held-lock', 'consumer-invalid')
        cases = [(scenario, '') for scenario in scenarios]
        cases.extend(
            ('fresh', failure)
            for failure in (
                'boundary build-crysta.sh',
                'boundary crysta-src.sh',
                'python tools/ci/crysta_sdk.py fetch',
                'cmake -S',
                'cmake --build build/ci -j',
                'cmake --build build/ci --target',
            )
        )
        cases.append(('artifact', 'python tools/ci/edi_native.py restore'))
    else:
        scenarios = (
            'fresh',
            'cached',
            'stale-head',
            'object-present',
            'missing-stamp',
            'consumer',
            'witness',
            'cached-witness',
        )
        cases = [(scenario, '') for scenario in scenarios]
        cases.extend(
            ('fresh', failure)
            for failure in (
                ' fetch -q --depth 1 https://example.invalid/crysta ' + SHA,
                ' checkout ',
                ' clean ',
            )
        )
    try:
        for scenario, failure in cases:
            before_rc, before, before_outputs = observe(path, baseline, scenario, failure)
            after_rc, after, after_outputs = observe(path, actual, scenario, failure)
            # Added work is permitted, but existing operations retain their order and status.
            remaining = iter(after)
            retained = all(any(call == item for item in remaining) for call in before)
            if (
                bool(before_rc) != bool(after_rc)
                or not retained
                or before_outputs != after_outputs
            ):
                return False
    except (OSError, subprocess.TimeoutExpired):
        return False
    return True
