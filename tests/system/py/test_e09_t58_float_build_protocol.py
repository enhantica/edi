"""F6/F7/F8: execute the real shell orchestration against controlled build I/O.

Git objects and checkouts are real, the remote is deterministic, and compilation is a
test double. These controls prove source selection and record flow, not compiled physics.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from edi import verification

from tests.integration.py import test_e09_t75_sdk_consumer as sdk_fixture

ROOT = Path(__file__).resolve().parents[3]

TOOL_DOUBLE = r"""
import json
import os
from pathlib import Path
import subprocess
import sys

root = Path(os.environ['FLOAT_TEST_ROOT'])
args = sys.argv[1:]
name = Path(sys.argv[0]).name
if name == 'git':
    with (root / 'git-calls.jsonl').open('a') as output:
        output.write(json.dumps(args) + '\n')
    if 'ls-remote' in args:
        state = json.loads((root / 'remote.json').read_text())
        if state['sha'] is None:
            print('fixture remote: authenticated crysta resolve refused', file=sys.stderr)
            sys.exit(128)
        print(state['sha'] + '\trefs/heads/main')
        sys.exit(0)
    args = [
        str(root / 'sibling')
        if arg == 'https://github.com/enhantica/c' + 'rysta'
        or (
            arg.startswith('https://x-access-token:')
            and arg.endswith('@github.com/enhantica/crysta')
        )
        else arg
        for arg in args
    ]
    sys.exit(subprocess.run([os.environ['FLOAT_TEST_GIT'], *args], check=False).returncode)
if name in ('cc', 'c++'):
    print('fixed test compiler identity')
    sys.exit(0)
if name == 'cmake':
    if '--install' in args:
        Path(args[args.index('--prefix') + 1]).mkdir(parents=True, exist_ok=True)
    elif '--build' in args:
        build = Path(args[args.index('--build') + 1]).resolve()
        build.mkdir(parents=True, exist_ok=True)
        if build.name in ('ci', 'ci-consumer'):
            # Independent witness of the source consumed at the simulated LINK boundary.
            prefix = 'crysta-consumer-prefix' if build.name == 'ci-consumer' else 'crysta-prefix'
            stamp = root / ('edi/build/' + prefix + '/.crysta-sha')
            (build / '.test-linked-source').write_text(stamp.read_text())
        executable = build / ('crysta_consumer' if build.name == 'crysta-consumer' else 'crysta')
        executable.write_text('#!/bin/sh\nexit 0\n')
        executable.chmod(0o755)
    elif '-B' in args:
        Path(args[args.index('-B') + 1]).mkdir(parents=True, exist_ok=True)
    else:
        raise AssertionError('unexpected build interface: ' + repr(args))
    sys.exit(0)
raise AssertionError('unexpected tool name: ' + name)
"""


class _BuildHarness:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.edi = root / 'edi'
        scripts = self.edi / 'tools/ci'
        scripts.mkdir(parents=True)
        # Before: four self-contained float scripts. After: the complete SDK helper graph.
        shutil.copytree(ROOT / 'tools/ci', scripts, dirs_exist_ok=True)
        (self.edi / 'CMakeLists.txt').write_text('# test build surface\n', encoding='utf-8')
        self.sibling = root / 'sibling'
        self.sibling.mkdir()
        real_git = shutil.which('git')
        assert real_git, 'F6 source protocol control requires a real local git executable'
        self.git = real_git
        self._git('init', '-q')
        source = self.sibling / 'CMakeLists.txt'
        source.write_text('# source A\n', encoding='utf-8')
        self._git('add', 'CMakeLists.txt')
        self._git('commit', '-qm', 'source A')
        self.first = self._git('rev-parse', 'HEAD').strip()
        source.write_text('# source B\n', encoding='utf-8')
        self._git('add', 'CMakeLists.txt')
        self._git('commit', '-qm', 'source B')
        self.second = self._git('rev-parse', 'HEAD').strip()
        self._git('update-ref', 'refs/remotes/origin/main', self.first)
        binaries = root / 'bin'
        binaries.mkdir()
        for name in ('git', 'cmake', 'cc', 'c++'):
            executable = binaries / name
            executable.write_text(f'#!{sys.executable}\n{TOOL_DOUBLE}', encoding='utf-8')
            executable.chmod(0o755)
        self.env = os.environ.copy()
        for name in (
            'CRYSTA_PIN_SPIKE',
            'CRYSTA_CONSUMER_SRC',
            'EDI_EXTENSION_DIR',
            'EDI_USE_CONSUMER_BUILD',
            'GITHUB_TOKEN',
            'GH_TOKEN',
            'GITHUB_EVENT_NAME',
            'GITHUB_HEAD_REF',
            'GITHUB_OUTPUT',
            'CRYSTA_SOURCE_SHA',
            'PYTEST_XDIST_WORKER',
            'CRYSTA_SDK_DIR',
            'EDI_NATIVE_ARTIFACT',
            'EDI_CORE_TARGETS',
            'EDI_PRODUCER_LOCK_HELD',
            'RUNNER_TEMP',
            'GITHUB_ENV',
            'GIT_CONFIG_COUNT',
        ):
            self.env.pop(name, None)
        self.env.update({
            'PATH': str(binaries) + os.pathsep + self.env['PATH'],
            'FLOAT_TEST_ROOT': str(root),
            'FLOAT_TEST_GIT': self.git,
            'CRYSTA_SRC': str(self.sibling),
            'CC': str(binaries / 'cc'),
            'CXX': str(binaries / 'c++'),
        })
        # SDK payloads use real independent A/B commit identities. The compiler alone
        # is virtualized: acquisition and qualification execute the production reader.
        self._prepare_sdks(root, binaries)
        self.remote(self.first)

    def _prepare_sdks(self, root, binaries):
        saved = sdk_fixture.SHA
        try:
            for name, sha in (('ordinary-sdk', self.first), ('candidate-sdk', self.second)):
                folder = root / name
                folder.mkdir()
                sdk_fixture.SHA = sha
                fixture_env, fixture_repo, sdk = sdk_fixture.consumer(
                    folder, platform='linux-64', download=True, prepare_only=True
                )
                if name == 'ordinary-sdk':
                    self.release = folder
                    for file in ('pixi.toml', 'pixi.lock'):
                        shutil.copyfile(fixture_repo / file, self.edi / file)
                    shutil.copyfile(folder / 'bin/curl', binaries / 'curl')
                    (binaries / 'curl').chmod(0o755)
                    self.env['DOWNLOAD_FIXTURE'] = str(folder)
                    self.env['GITHUB_TOKEN'] = fixture_env['GITHUB_TOKEN']
                    self.env['PIXI_PLATFORM'] = 'linux-64'
                    self.env['PIXI_ENVIRONMENT_NAME'] = 'default'
                    self.env['MACOSX_DEPLOYMENT_TARGET'] = '11.0'
                else:
                    self.candidate = sdk
        finally:
            sdk_fixture.SHA = saved

    def _git(self, *args: str) -> str:
        return subprocess.check_output(
            [
                self.git,
                '-C',
                str(self.sibling),
                '-c',
                'user.name=Protocol Fixture',
                '-c',
                'user.email=fixture@example.invalid',
                *args,
            ],
            text=True,
        )

    def remote(self, sha: str | None) -> None:
        (self.root / 'remote.json').write_text(json.dumps({'sha': sha}), encoding='utf-8')

    def run(self, script: str, *args: str) -> subprocess.CompletedProcess[str]:
        if script == 'core-build.sh':
            if self.env.get('CRYSTA_CONSUMER_SRC') == str(self.sibling):
                self.env['CRYSTA_SDK_DIR'] = str(self.candidate)
            else:
                self.env.pop('CRYSTA_SDK_DIR', None)
        return subprocess.run(
            ['bash', str(self.edi / 'tools/ci' / script), *args],
            cwd=self.edi,
            env=self.env,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )

    def record(self, relative: str) -> str:
        return (self.edi / relative).read_text(encoding='utf-8').strip()

    def git_calls(self) -> list[list[str]]:
        return [
            json.loads(line)
            for line in (self.root / 'git-calls.jsonl').read_text(encoding='utf-8').splitlines()
        ]


def test_ci_token_authenticates_both_remote_operations_and_clears_checkout_header(
    tmp_path: Path,
) -> None:
    harness = _BuildHarness(tmp_path)
    token = str(id(harness))
    authenticated_remote = f'https://x-access-token:{token}@github.com/enhantica/crysta'
    harness.env['GITHUB_TOKEN'] = token

    # Before: main resolution + fetch. After ADR-0017: SDK API GET + pinned source fetch.
    outcome = harness.run('core-build.sh')
    assert outcome.returncode == 0, (
        '/ authenticated SDK and source acquisition must succeed: ' + outcome.stderr
    )
    assert token not in outcome.stdout and token not in outcome.stderr, (
        ' authenticated acquisition must never print the token value'
    )
    downloads = [
        json.loads(line) for line in (harness.release / 'downloads').read_text().splitlines()
    ]
    assert downloads and all('Authorization: Bearer ' + token in call for call in downloads), (
        '/ every SDK API request must carry the supplied token'
    )
    remote_calls = [call for call in harness.git_calls() if authenticated_remote in call]
    assert remote_calls and all(
        'fetch' in call and harness.first in call for call in remote_calls
    ), '/ source acquisition fetches exactly the SDK commit without floating'
    for call in remote_calls:
        config = call.index('-c')
        assert call[config + 1] == 'http.https://github.com/.extraheader=', (
            " each authenticated request clears checkout's inherited auth header"
        )


@pytest.mark.parametrize('sibling_available', [True, False], ids=['fallback', 'refusal'])
def test_failed_remote_has_a_validated_fallback_or_named_refusal(
    tmp_path: Path, *, sibling_available: bool
) -> None:
    harness = _BuildHarness(tmp_path)
    # Before: failed float lookup fell back to sibling main. After ADR-0017: an
    # unavailable pinned SDK refuses, irrespective of a usable sibling checkout.
    state = harness.release / 'download.json'
    data = json.loads(state.read_text())
    data['retained_tags'] = []
    state.write_text(json.dumps(data))
    if not sibling_available:
        harness.env['CRYSTA_SRC'] = str(tmp_path / 'absent-sibling')
    outcome = harness.run('build-crysta.sh')
    assert outcome.returncode != 0, '/ unavailable pinned SDK cannot fall back to sibling source'
    assert 'crysta_sdk.py' in outcome.stderr and 'REFUSED' in outcome.stderr, (
        '/ unavailable pinned SDK must reach the named acquisition refusal'
    )
    assert not (harness.edi / 'build/crysta-prefix/.crysta-sha').exists(), (
        '/ unavailable SDK cannot produce an installation attestation'
    )


def test_remote_advance_cannot_mix_linked_and_recorded_sources(tmp_path: Path) -> None:
    harness = _BuildHarness(tmp_path)
    first = harness.run('core-build.sh')
    assert first.returncode == 0, 'F7 first ordinary core build must succeed: ' + first.stderr
    linked = harness.record('build/ci/.test-linked-source')
    assert linked == harness.first, 'F7 the first artifact must actually consume source A'
    harness.remote(harness.second)
    second = harness.run('crysta-consumer.sh')
    assert second.returncode == 0, (
        'F7 consumer must retain the run source or rebuild coherently: ' + second.stderr
    )
    assert (
        harness.record('build/crysta-src/CRYSTA_SOURCE_SHA')
        == harness.record('build/crysta-prefix/.crysta-sha')
        == harness.record('build/ci/.test-linked-source')
    ), 'F7 remote advancement must never leave source records naming a different linked engine'


def _alias_extension(edi_root: Path, extension: Path) -> Path:
    alias = edi_root / 'build/ci/python/selected'
    alias.parent.mkdir(parents=True, exist_ok=True)
    alias.symlink_to(extension, target_is_directory=True)
    assert alias.resolve() == extension.resolve(), (
        'F3 the alias witness must resolve to the distinct consumer artifact'
    )
    return alias


@pytest.mark.parametrize(
    'selector', ['consumer-source', 'extension-dir', 'extension-precedence', 'extension-alias']
)
def test_selected_artifact_controls_verification_provenance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, selector: str
) -> None:
    # Review-8 F3: A and B are real, distinct git identities. The selected extension's adjacent
    # stamp is the independent link-time witness; the ordinary source record must not label it.
    harness = _BuildHarness(tmp_path)
    ordinary = harness.run('core-build.sh')
    assert ordinary.returncode == 0, (
        'F3 the ordinary source-A build must succeed: ' + ordinary.stderr
    )
    assert harness.record('build/crysta-src/CRYSTA_SOURCE_SHA') == harness.first, (
        'F3 the ordinary build record must identify the source-A artifact it consumed'
    )

    harness.env['CRYSTA_CONSUMER_SRC'] = str(harness.sibling)
    consumer = harness.run('core-build.sh')
    assert consumer.returncode == 0, (
        'F3 the explicit source-B build must succeed: ' + consumer.stderr
    )
    assert harness.record('build/ci-consumer/.crysta-linked-sha') == harness.second, (
        'F3 the consumer linked record must identify the selected source-B artifact'
    )

    monkeypatch.setattr(verification, '_repo_root', lambda: harness.edi)
    monkeypatch.setattr(verification, '_edi_display_version', lambda: 'test')
    # Review-9 F3: selector changes must reach BOTH consumers. Previously monkeypatch
    # changed only the label process, while run() kept a different saved environment.
    harness.env.pop('CRYSTA_CONSUMER_SRC', None)
    harness.env.pop('EDI_EXTENSION_DIR', None)
    expected, configuration = harness.second, 'consumer'
    if selector == 'consumer-source':
        harness.env['CRYSTA_CONSUMER_SRC'] = str(harness.sibling)
    else:
        if selector == 'extension-precedence':
            harness.env['CRYSTA_CONSUMER_SRC'] = str(harness.sibling)
            expected, configuration = harness.first, 'ordinary'
        build = 'ci' if configuration == 'ordinary' else 'ci-consumer'
        extension = harness.edi / f'build/{build}/python/edi'
        extension.mkdir(parents=True, exist_ok=True)
        if selector == 'extension-alias':
            # Review-10 F3: the last component itself resolves across configurations.
            # Resolving only its parent incorrectly chooses ordinary source A.
            extension = _alias_extension(harness.edi, extension)
        harness.env['EDI_EXTENSION_DIR'] = str(extension)
    for name in ('CRYSTA_CONSUMER_SRC', 'EDI_EXTENSION_DIR'):
        monkeypatch.delenv(name, raising=False)
        if name in harness.env:
            monkeypatch.setenv(name, harness.env[name])

    label = verification.engine_label('crysta')
    unselected = harness.first if expected == harness.second else harness.second
    assert expected[:7] in label and unselected[:7] not in label, (
        'F3 the verification label must identify the artifact selected by ' + selector
    )

    installed = harness.run('crysta-consumer.sh')
    if selector == 'extension-alias' and installed.returncode != 0:
        assert 'EDI_EXTENSION_DIR' in installed.stderr and unselected not in installed.stdout, (
            'F3 an alias refusal must identify the selector without proving the unselected source'
        )
        return
    assert installed.returncode == 0, (
        'F3 the installed-consumer check must accept the selected artifact: ' + installed.stderr
    )
    assert expected in installed.stdout and f'{configuration} configuration' in installed.stdout, (
        'F3 the installed-consumer check must identify the same selected source and configuration'
    )

    build = 'ci' if configuration == 'ordinary' else 'ci-consumer'
    linked = harness.edi / f'build/{build}/.crysta-linked-sha'
    # The ordinary label's established record is CRYSTA_SOURCE_SHA; consumer labels
    # read the adjacent linked stamp. Corrupt the selected record in either shape.
    provenance = (
        harness.edi / 'build/crysta-src/CRYSTA_SOURCE_SHA'
        if configuration == 'ordinary'
        else linked
    )
    provenance.write_text('not-a-commit\n', encoding='utf-8')
    assert 'crysta ?' in verification.engine_label('crysta'), (
        'F3 malformed selected-artifact provenance must render unknown, never the other artifact'
    )
    refused = harness.run('crysta-consumer.sh')
    assert refused.returncode != 0 and 'records disagree' in refused.stderr, (
        'F3 the installed-consumer check must refuse a malformed selected-artifact record'
    )
    provenance.write_text(expected + '\n', encoding='utf-8')
    linked.write_text(unselected + '\n', encoding='utf-8')
    disagreement = harness.run('crysta-consumer.sh')
    assert disagreement.returncode != 0 and 'records disagree' in disagreement.stderr, (
        'F3 the installed-consumer check must refuse valid but disagreeing source identities'
    )


def test_consumer_gate_does_not_treat_source_path_as_a_runtime_selector(
    tmp_path: Path,
) -> None:
    harness = _BuildHarness(tmp_path)
    ordinary = harness.run('core-build.sh')
    assert ordinary.returncode == 0, (
        ' control requires a complete ordinary artifact: ' + ordinary.stderr
    )
    harness.env['CRYSTA_CONSUMER_SRC'] = '-not-a-source-tree'
    checked = harness.run('crysta-consumer.sh')
    assert checked.returncode == 0 and '(ordinary configuration)' in checked.stdout, (
        ' a non-tree source-path string must not silently select stale ci-consumer output: '
        + checked.stdout
        + checked.stderr
    )


def test_consumer_gate_retains_the_literal_hidden_control_on_an_explicit_selector(
    tmp_path: Path,
) -> None:
    harness = _BuildHarness(tmp_path)
    harness.env['CRYSTA_CONSUMER_SRC'] = str(harness.sibling)
    consumer = harness.run('core-build.sh')
    assert consumer.returncode == 0, (
        ' control requires a complete consumer artifact: ' + consumer.stderr
    )
    harness.env.pop('CRYSTA_CONSUMER_SRC')
    harness.env['EDI_USE_CONSUMER_BUILD'] = 'hidden-surface-control'
    checked = harness.run('crysta-consumer.sh')
    assert checked.returncode == 0 and '(consumer configuration)' in checked.stdout, (
        ' must retain the deliberate literal hidden-control through the explicit consumer '
        'selector: ' + checked.stdout + checked.stderr
    )


def test_stale_consumer_artifact_cannot_follow_a_changed_live_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    harness = _BuildHarness(tmp_path)
    ordinary = harness.run('core-build.sh')
    assert ordinary.returncode == 0, (
        ' mismatch control requires the ordinary source-A artifact: ' + ordinary.stderr
    )
    harness.env['CRYSTA_CONSUMER_SRC'] = str(harness.sibling)
    consumer = harness.run('core-build.sh')
    assert consumer.returncode == 0, (
        ' mismatch control requires the consumer source-B artifact: ' + consumer.stderr
    )
    source = harness.sibling / 'CMakeLists.txt'
    source.write_text('# source C\n', encoding='utf-8')
    harness._git('add', 'CMakeLists.txt')
    harness._git('commit', '-qm', 'source C')
    live = harness._git('rev-parse', 'HEAD').strip()

    monkeypatch.setattr(verification, '_repo_root', lambda: harness.edi)
    monkeypatch.setattr(verification, '_edi_display_version', lambda: 'test')
    monkeypatch.setenv('CRYSTA_CONSUMER_SRC', str(harness.sibling))
    monkeypatch.delenv('EDI_EXTENSION_DIR', raising=False)
    label = verification.engine_label('crysta')
    assert harness.second[:7] not in label, (
        ' verification must not attribute changed live source C to the stale source-B '
        f'consumer artifact; live={live}, stale={harness.second}, label={label}'
    )
    assert harness.first[:7] in label or 'crysta ?' in label, (
        ' verification must select the explicit ordinary source-A contract or visibly '
        f'refuse the stale mismatch; label={label}'
    )

    checked = harness.run('crysta-consumer.sh')
    diagnostic = checked.stdout + checked.stderr
    if checked.returncode != 0:
        assert harness.second[:7] in diagnostic and live[:7] in diagnostic, (
            ' a consumer-gate refusal must identify both stale and live source identities: '
            + diagnostic
        )
        return
    assert '(ordinary configuration)' in checked.stdout and harness.first in checked.stdout, (
        ' the installed-consumer gate must select the explicit ordinary artifact or refuse '
        'the stale source-B versus live-source-C mismatch: ' + diagnostic
    )


def test_ordinary_core_build_cannot_accept_a_spike_as_the_float(tmp_path: Path) -> None:
    # core-build is the ordinary verify dependency, not the explicit consumer-contract route.
    harness = _BuildHarness(tmp_path)
    harness.env['CRYSTA_PIN_SPIKE'] = harness.second
    result = harness.run('core-build.sh')
    if result.returncode != 0:
        assert 'CRYSTA_PIN_SPIKE' in result.stderr, (
            'F8 an override refusal must identify the forbidden spike input'
        )
        assert not (harness.edi / 'build/ci/.test-linked-source').exists(), (
            'F8 refused spike selection must never reach the ordinary link boundary'
        )
    else:
        assert harness.record('build/ci/.test-linked-source') == harness.first, (
            'F8/ ignoring an override must still link the pinned SDK commit'
        )
        assert harness.record('build/crysta-src/CRYSTA_SOURCE_SHA') == harness.first, (
            'F8/ ordinary green must attribute the pinned SDK rather than the spike'
        )
