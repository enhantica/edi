"""F12: a diagnostic SDK reaches the existing runtime/provenance consumers."""

from __future__ import annotations

import json
import runpy
import shutil
import subprocess
import sys

import pytest

from tests.fixtures.e09_t75_commands import assert_no_swallowed_refusal
from tests.integration.py.test_e09_t75_sdk_consumer import ROOT, SHA, consumer

# Only the unavailable native ABI is substituted. The source importer, provenance,
# manifest CLI, C++ consumer launcher and pytest policy are copied unchanged.
NATIVE = """
WITNESS = {witness!r}
__build_commit__ = 'independent-artifact'
class Meta(type):
    def __getattr__(cls, name): return name
class Value(metaclass=Meta): pass
class Project(Value):
    def fit(self): pass
    def fit_independent(self): pass
    def fit_joint(self): pass
    def fit_sequential(self): pass
def __getattr__(name):
    if name.startswith('__'): raise AttributeError(name)
    value = type(name, (Value,), {{}})
    globals()[name] = value
    return value
"""


def cmake_transport(base):
    """Only the native compile is replaced; complete requests select their artifacts."""
    cmake = base / 'bin/cmake'
    cmake.write_text(
        '#!'
        + sys.executable
        + '\n'
        + r"""import json, os, sys
from pathlib import Path
r = Path(os.environ['PIXI_PROJECT_ROOT'])
b = r.parent
a = sys.argv[1:]
prefix = str(r / 'build/crysta-consumer-prefix')
forms = {
    'core': ['-S', '.', '-B', 'build/ci-consumer', '-G', 'Ninja',
             '-DCMAKE_BUILD_TYPE=Release', '-DCMAKE_PREFIX_PATH=' + prefix,
             '-DCMAKE_OSX_DEPLOYMENT_TARGET=11.0'],
    'cpp': ['-S', str(r / 'tools/ci/crysta-consumer'), '-B', str(r / 'build/crysta-consumer'),
            '-G', 'Ninja', '--no-warn-unused-cli', '-DCMAKE_BUILD_TYPE=Release',
            '-DCMAKE_PREFIX_PATH=' + prefix, '-DCMAKE_DISABLE_FIND_PACKAGE_Python=ON',
            '-DCMAKE_DISABLE_FIND_PACKAGE_Python2=ON', '-DCMAKE_DISABLE_FIND_PACKAGE_Python3=ON'],
}
for kind, form in forms.items():
    build = form[3]
    configured = b / ('configured-' + kind)
    if a == form:
        configured.write_text(json.dumps(a))
        sys.exit(0)
    if a == ['--build', build, '-j'] and configured.exists():
        if json.loads(configured.read_text()) != form:
            break
        if kind == 'core':
            dest = r / build / 'python/edi/_edi.py'
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text((b / 'native-consumer.py').read_text())
        else:
            dest = r / build / 'crysta_consumer'
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text('#!/bin/sh\necho candidate-cpp-executed\n')
            dest.chmod(0o755)
        sys.exit(0)
with (b / 'unsupported-commands.jsonl').open('a') as f:
    f.write(json.dumps(['cmake', *a]) + '\n')
sys.exit(64)
"""
    )
    cmake.chmod(0o755)


def runtime_case(base, caller, explicit, *, accident=None):  # noqa: PLR0912, PLR0915
    base.mkdir()
    env, repo, _ = consumer(base, platform='linux-64', prepare_only=True)
    for k in list(env):
        if k.startswith('EDI_') or k == 'CRYSTA_CONSUMER_SRC':
            env.pop(k)
    if explicit:
        env['EDI_USE_CONSUMER_BUILD'] = '1'
    env.update(PYTHONPATH=str(repo / 'lib'), PYTHONNOUSERSITE='1')
    shutil.copytree(ROOT / 'lib/edi', repo / 'lib/edi')
    shutil.copytree(ROOT / 'tools/checks', repo / 'tools/checks')
    shutil.copytree(ROOT / 'tools/testing', repo / 'tools/testing')
    (repo / 'pyproject.toml').write_text('[project]\nname="runtime-fixture"\n')
    (repo / 'CMakeLists.txt').write_text('project(independent)\n')
    (repo / 'knowledge/verification').mkdir(parents=True)
    for build, witness, pin in [('ci', 'ordinary', 'b6' * 20), ('ci-consumer', 'consumer', SHA)]:
        dest = repo / 'build' / build / 'python/edi'
        dest.mkdir(parents=True)
        if build == 'ci':
            (dest / '_edi.py').write_text(NATIVE.format(witness=witness))
        else:
            (base / 'native-consumer.py').write_text(NATIVE.format(witness=witness))
        (repo / 'build' / build / '.crysta-linked-sha').write_text(pin + '\n')
    source = repo / 'build/crysta-src'
    source.mkdir()
    (source / 'CRYSTA_SOURCE_SHA').write_text('b6' * 20 + '\n')
    (source / 'tests/fitting').mkdir(parents=True)
    (source / 'tests/fitting/manifest.yml').write_text('cases: []\n')
    prefix = repo / 'build/crysta-prefix'
    prefix.mkdir()
    (prefix / '.crysta-sha').write_text('b6' * 20 + '\n')
    cmake_transport(base)

    def call(argv):
        result = subprocess.run(
            argv, cwd=repo, env=env, text=True, capture_output=True, check=False, timeout=3
        )
        if result.returncode == 0:
            assert_no_swallowed_refusal(base, True)
        return result

    built = call(['bash', 'tools/ci/core-build.sh'])
    if built.returncode:
        return built, None
    if caller == 'import':
        result = call([sys.executable, '-c', 'import edi, edi._edi; print(edi._edi.WITNESS)'])
    elif caller == 'provenance':
        result = call([
            sys.executable,
            '-c',
            'from edi.verification import engine_label; print(engine_label("crysta"))',
        ])
    elif caller == 'surface':
        # Direction text is a schema identifier, not the expected selected artifact.
        schema = runpy.run_path(str(ROOT / 'tools/checks/python_surface_superset.py'))
        for name, public in [
            ('crysta-consumer-prefix', {'Project': {'kind': 'class', 'members': ['fit']}}),
            ('crysta-prefix', {'UNDECLARED_ORDINARY_ARTIFACT': {'kind': 'function'}}),
        ]:
            target = repo / 'build' / name / 'share/crysta/python-surface.json'
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(
                json.dumps({
                    'schema': 4,
                    'directionality': schema['DIRECTIONALITY'],
                    'public': public,
                })
            )
        result = call([sys.executable, 'tools/checks/python_surface_superset.py'])
    elif caller == 'cpp-consumer':
        if accident:
            script = repo / 'tools/ci/crysta-consumer.sh'
            text = script.read_text()
            text = (
                text.replace(
                    '-DCMAKE_PREFIX_PATH="$PREFIX"',
                    '-DCMAKE_PREFIX_PATH="$ROOT/build/crysta-prefix"',
                )
                if accident == 'ordinary-prefix'
                else text.replace(
                    'cmake --build "$BUILD" -j', 'cmake --build "$ROOT/build/wrong" -j'
                )
            )
            script.write_text(text)
        result = call(['bash', 'tools/ci/crysta-consumer.sh'])
    else:
        # Run the plugin lifecycle entry. A diagnostic has no consumer corpus source;
        # it must stay unknown, never stage the ordinary build's unrelated corpus.
        result = call([
            sys.executable,
            '-c',
            (
                'from tools.testing import fit_policy as p; p.pytest_configure(None); '
                'print("ordinary-corpus" if p._source_corpus.get("source") '
                'else "unknown-corpus"); '
                'p.pytest_sessionfinish(None,0)'
            ),
        ])
    return built, result


@pytest.mark.parametrize(
    'caller', ['import', 'provenance', 'surface', 'cpp-consumer', 'corpus-policy']
)
def test_diagnostic_sdk_cannot_build_one_artifact_and_prove_the_ordinary_one(tmp_path, caller):
    built, good = runtime_case(tmp_path / 'control', caller, True)
    assert built.returncode == 0, (
        f' F12 explicit selector must build the qualified candidate: {built.stderr}'
    )
    assert good is not None and good.returncode == 0, (
        f' F12 retained {caller} control must execute: {good}'
    )

    def selected(result):
        text = result.stdout + result.stderr
        return {
            'import': 'consumer',
            'provenance': SHA[:7],
            'cpp-consumer': 'candidate-cpp-executed',
            'corpus-policy': 'unknown-corpus',
        }.get(caller, 'python-surface superset OK') in text

    assert selected(good), (
        f' F12 explicit {caller} must observe the candidate artifact: {good.stdout}'
    )
    built, bad = runtime_case(tmp_path / 'subject', caller, False)
    if built.returncode:
        assert 'EDI_USE_CONSUMER_BUILD' in built.stdout + built.stderr, (
            ' F12 a narrowed SDK route must explain its required explicit runtime selector'
        )
    else:
        assert bad is not None and bad.returncode == 0 and selected(bad), (
            ' F12 SDK-only build must never silently import, label, check '
            'or authorize the ordinary artifact'
        )


@pytest.mark.parametrize('accident', ['ordinary-prefix', 'wrong-build'])
def test_cpp_request_accident_cannot_manufacture_the_candidate_witness(tmp_path, accident):
    built, good = runtime_case(tmp_path / 'control', 'cpp-consumer', True)
    assert built.returncode == 0 and good is not None and good.returncode == 0, (
        ' F12 exact configure/build requests must create the candidate witness'
    )
    assert 'candidate-cpp-executed' in good.stdout, (
        ' F12 the configured executable must run before the request accident'
    )
    built, bad = runtime_case(tmp_path / 'subject', 'cpp-consumer', True, accident=accident)
    assert built.returncode == 0 and bad is not None and bad.returncode != 0, (
        ' F12 wrong package or build destination must refuse at the CMake boundary'
    )
    assert (tmp_path / 'subject/unsupported-commands.jsonl').exists(), (
        ' F12 unsupported configuration must persist its refusal'
    )
    assert 'candidate-cpp-executed' not in bad.stdout, (
        ' F12 configuration text cannot impersonate the candidate executable'
    )
