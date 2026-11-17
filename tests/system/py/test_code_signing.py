# SPDX-License-Identifier: BSD-3-Clause
"""Offline installer contract from ADR-0091 and the release signing decisions."""

import ast
import copy
import importlib.util
import json
import re
import subprocess
import xml.etree.ElementTree as ET  # noqa: S405 - locally generated IFW XML
from functools import cache
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from tests.fixtures.e09_t75_workflow import actions_equal

ROOT = Path(__file__).resolve().parents[3]
SECRET_NAMES = {
    'CODESIGN_MAC_CERT_P12_BASE64',
    'CODESIGN_MAC_CERT_P12_PASSWORD',
    'CODESIGN_MAC_NOTARY_APPLE_ID',
    'CODESIGN_MAC_NOTARY_PASSWORD',
    'CODESIGN_WIN_CERT_P12_BASE64',
    'CODESIGN_WIN_CERT_P12_PASSWORD',
    'CODESIGN_WIN_KEYLOCKER_API_KEY',
}
VARIABLE_NAMES = {
    'CODESIGN_MAC_TEAM_ID',
    'CODESIGN_MAC_IDENTITY',
    'CODESIGN_WIN_KEYLOCKER_HOST',
    'CODESIGN_WIN_KEYLOCKER_KEYPAIR_ALIAS',
}


@cache
def workflow():
    return yaml.load(
        (ROOT / '.github/workflows/installers.yml').read_text(), Loader=yaml.BaseLoader
    )


def steps():
    return workflow()['jobs']['installers']['steps']


def signing_steps():
    return [
        step
        for step in steps()
        if re.search(
            r'secrets[.]CODESIGN_|digicert/|apple-actions/import-codesign-certs', str(step)
        )
        or re.search(
            r'package[.]py.*\bseal\b|verify_windows_signature|notarytool|stapler',
            step.get('run', ''),
        )
    ]


def executable_text():
    text = '\n'.join(step.get('run', '') for step in steps())
    for path in (ROOT / 'tools/installer').glob('*.py'):
        tree = ast.parse(path.read_text())
        text += '\n' + '\n'.join(
            node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and not node.value.startswith('Offline ')
        )
    return text


def expression(value, atoms):
    value = str(value).strip().removeprefix('${{').removesuffix('}}')
    for name, item in sorted(atoms.items(), key=lambda pair: len(pair[0]), reverse=True):
        value = re.sub(r'\b' + re.escape(name) + r'\b', repr(item), value)
    value = value.replace('&&', ' and ').replace('||', ' or ')
    value = re.sub(r'!(?!=)', ' not ', value)
    value = re.sub(r'\btrue\b', 'True', value)
    value = re.sub(r'\bfalse\b', 'False', value)
    tree = ast.parse(value.strip(), mode='eval')
    allowed = (
        ast.Expression,
        ast.BoolOp,
        ast.And,
        ast.Or,
        ast.UnaryOp,
        ast.Not,
        ast.Compare,
        ast.Eq,
        ast.NotEq,
        ast.Constant,
    )
    assert all(isinstance(node, allowed) for node in ast.walk(tree)), (
        'Signing conditions must resolve from actual event, repository, branch and environment'
    )
    return condition_value(tree.body)


def context_atoms(event, ref, release, platform, repository, *, preview=False, fork=False):
    atoms = {
        'github.event_name': event,
        'github.repository': repository,
        'github.event.pull_request.head.repo.fork': fork if event == 'pull_request' else '',
        'github.ref': ref,
        'runner.os': platform,
        'inputs.release_plan_run': '1234' if release else '',
        'inputs.prepare_preview_release': preview,
        'env.EDI_RELEASE_PLAN': '/release-plan' if release else '',
    }
    guard = workflow()['jobs']['installers'].get('env', {}).get('EDI_CODESIGN', '')
    atoms['env.EDI_CODESIGN'] = expression(guard, atoms) if guard else ''
    return atoms


def condition(  # noqa: PLR0913 - each argument is an Actions context input
    step,
    event,
    ref,
    release,
    platform,
    *,
    repository='enhantica/edi',
    failed=False,
    preview=False,
    fork=False,
):
    atoms = context_atoms(event, ref, release, platform, repository, preview=preview, fork=fork)
    if 'EDI_CODESIGN' in step.get('env', {}):
        atoms['env.EDI_CODESIGN'] = expression(step['env']['EDI_CODESIGN'], atoms)
    value = str(step.get('if', 'success()'))
    if not re.search(r'\b(?:success|failure|cancelled|always)\(', value) and failed:
        return False
    for name, result in [
        ('success', not failed),
        ('failure', failed),
        ('cancelled', False),
        ('always', True),
    ]:
        value = value.replace(name + '()', repr(result))
    return bool(expression(value, atoms))


def private_access(  # noqa: PLR0913 - each argument is an Actions context input
    step, event, ref, release, platform, *, repository='enhantica/edi', preview=False, fork=False
):
    if not condition(
        step, event, ref, release, platform, repository=repository, preview=preview, fork=fork
    ):
        return False
    values = [
        value
        for field in ('env', 'with')
        for value in step.get(field, {}).values()
        if re.search(r'secrets[.]CODESIGN_', str(value))
    ]
    if not values:
        return True
    atoms = context_atoms(event, ref, release, platform, repository, preview=preview, fork=fork)
    if 'EDI_CODESIGN' in step.get('env', {}):
        atoms['env.EDI_CODESIGN'] = expression(step['env']['EDI_CODESIGN'], atoms)
    for value in values:
        for name in re.findall(r'secrets[.](CODESIGN_[A-Z0-9_]+)', value):
            atoms['secrets.' + name] = 'credential:' + name
    return any(expression(value, atoms) for value in values)


def job_environment(event, ref, release, platform, repository, *, preview=False, fork=False):
    environment = workflow()['jobs']['installers'].get('environment')
    if isinstance(environment, dict):
        environment = environment.get('name')
    atoms = context_atoms(event, ref, release, platform, repository, preview=preview, fork=fork)
    return expression(environment, atoms) if '${{' in str(environment) else environment


def condition_value(node):
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.UnaryOp):
        return not condition_value(node.operand)
    if isinstance(node, ast.BoolOp):
        result = condition_value(node.values[0])
        for item in node.values[1:]:
            if isinstance(node.op, ast.And) and not result:
                break
            if isinstance(node.op, ast.Or) and result:
                break
            result = condition_value(item)
        return result
    values = [condition_value(item) for item in [node.left, *node.comparators]]
    return all(
        actions_equal(left, right) == isinstance(operator, ast.Eq)
        for left, operator, right in zip(values, node.ops, values[1:], strict=False)
    )


@pytest.mark.parametrize('platform', ['macOS', 'Windows'])
def test_signing_is_present_and_never_reaches_pull_requests_or_other_branches(platform):
    selected = signing_steps()
    assert selected, 'Release installers must contain signing steps'
    for release, preview in [(True, False), (False, True)]:
        assert (
            job_environment(
                'workflow_dispatch',
                'refs/heads/main',
                release,
                platform,
                'enhantica/edi',
                preview=preview,
            )
            == 'codesign'
        ), 'Release-plan and preview dispatches must select the reviewed codesign environment'
        assert any(
            private_access(
                step, 'workflow_dispatch', 'refs/heads/main', release, platform, preview=preview
            )
            for step in selected
        ), 'Release-plan and preview dispatches must retain signing credentials on each platform'
    denied = [
        ('push', 'refs/heads/main', False, 'enhantica/edi'),
        ('pull_request', 'refs/pull/53/merge', False, 'enhantica/edi'),
        ('pull_request', 'refs/heads/main', True, 'enhantica/edi'),
        ('push', 'refs/heads/feature', False, 'enhantica/edi'),
        ('workflow_dispatch', 'refs/heads/feature', True, 'enhantica/edi'),
        ('workflow_dispatch', 'refs/heads/main', False, 'enhantica/edi'),
        ('schedule', 'refs/heads/main', False, 'enhantica/edi'),
        ('pull_request', 'refs/pull/53/merge', False, 'outside/edi'),
        ('push', 'refs/heads/main', False, 'outside/edi'),
        ('workflow_dispatch', 'refs/heads/main', True, 'outside/edi'),
    ]
    violations = [
        (event, ref, release, repository, step.get('name', step.get('uses', '')))
        for event, ref, release, repository in denied
        for step in selected
        if private_access(step, event, ref, release, platform, repository=repository)
    ]
    enabled_guards = [
        (event, ref, release, repository)
        for event, ref, release, repository in denied
        if context_atoms(event, ref, release, platform, repository)['env.EDI_CODESIGN']
    ]
    environment_violations = [
        (event, ref, release, repository)
        for event, ref, release, repository in denied
        if job_environment(event, ref, release, platform, repository) == 'codesign'
    ]
    assert not violations, (
        'Only release-plan or preview dispatches on main in the original repository may '
        'access signing credentials; forbidden routes reached: ' + repr(violations)
    )
    assert not environment_violations, (
        'Main pushes, PRs, forks, other branches and non-release dispatches must not receive '
        'the codesign environment: ' + repr(environment_violations)
    )
    assert not enabled_guards, (
        'Unsigned builds, including main pushes, must disable the signing flag: '
        + repr(enabled_guards)
    )
    for ref in ('refs/pull/53/merge', 'refs/heads/main'):
        assert not any(
            private_access(step, 'pull_request', ref, True, platform, fork=True)
            for step in selected
        ), 'A fork PR in the base repository must never reach signing credentials'
        assert (
            job_environment('pull_request', ref, True, platform, 'enhantica/edi', fork=True)
            != 'codesign'
        ), 'Fork PRs must never select the codesign environment'


@pytest.mark.parametrize('platform', ['macOS', 'Windows'])
def test_non_release_main_dispatch_receives_no_signing_credentials(platform):
    atoms = context_atoms('workflow_dispatch', 'refs/heads/main', False, platform, 'enhantica/edi')
    assert not atoms['env.EDI_CODESIGN'], (
        'A diagnostic main dispatch without a release plan or preview request must disable signing'
    )
    assert not any(
        private_access(step, 'workflow_dispatch', 'refs/heads/main', False, platform)
        for step in signing_steps()
    ), 'A non-release main dispatch must receive no certificate, key or notary credentials'
    assert any(
        private_access(step, 'workflow_dispatch', 'refs/heads/main', False, platform, preview=True)
        for step in signing_steps()
    ), 'An explicit preview-release request on main must retain its signing route'


def test_condition_observer_keeps_guard_values_and_refuses_unknown_context():
    assert expression("true && '1' || ''", {}) == '1', (
        'Actions boolean operators must retain the selected guard value'
    )
    disabled = expression("false && '1' || ''", {})
    assert isinstance(disabled, str) and not disabled, (
        'A disabled guard must remain an empty value rather than a truthy string'
    )
    with pytest.raises(AssertionError, match='Signing conditions must resolve'):
        expression("env.UNRECOGNISED == '1'", {})

    for event, fork, expected in [
        ('pull_request', False, False),
        ('pull_request', True, True),
        ('push', False, ''),
        ('workflow_dispatch', False, ''),
    ]:
        atoms = context_atoms(event, 'refs/heads/main', False, 'macOS', 'enhantica/edi', fork=fork)
        assert atoms['github.event.pull_request.head.repo.fork'] == expected, (
            'PR contexts carry the real fork boolean; events without a PR carry an empty property'
        )
        probe = {
            'if': 'github.event.pull_request.head.repo.fork == false',
            'env': {'KEY': '${{ secrets.CODESIGN_MAC_CERT_P12_PASSWORD }}'},
        }
        assert condition(probe, event, 'refs/heads/main', False, 'macOS', fork=fork) == (
            not fork
        ), 'The per-step fork guard must admit same-repo PRs and absent PR objects, refusing forks'
        assert private_access(probe, event, 'refs/heads/main', False, 'macOS', fork=fork) == (
            not fork
        ), 'Private credential observation must preserve the same fork and absent-object semantics'
    for left, right, equal in [
        ('', False, True),
        (False, False, True),
        (True, False, False),
        ('0', False, True),
        ('false', False, False),
        (None, False, True),
    ]:
        assert expression('left == right', {'left': left, 'right': right}) == equal, (
            'The bounded observer must use GitHub numeric coercion for loose equality'
        )


def test_pull_request_bundle_build_keeps_the_internal_ad_hoc_path(tmp_path, monkeypatch):
    for online in (False, True):
        observe_maintenance_package(
            tmp_path / str(online), monkeypatch, release=False, online=online
        )
    candidates = [
        step
        for step in steps()
        if 'tools/installer/build.py' in step.get('run', '')
        and '--collection' in step.get('run', '')
    ]
    assert len(candidates) == 1, 'PR installer checks must retain the ordinary bundle build'
    build = candidates[0]
    assert condition(build, 'pull_request', 'refs/pull/53/merge', False, 'macOS'), (
        'The ordinary macOS bundle build must still run on pull requests'
    )
    for platform in ('macOS', 'Windows'):
        if build in signing_steps():
            assert not private_access(
                build, 'pull_request', 'refs/pull/53/merge', False, platform
            ), 'PR bundle construction must receive no effective private signing credentials'
    assert not condition(build, 'pull_request', 'refs/pull/53/merge', False, 'macOS', fork=True), (
        'The real per-step guard must reject fork PR bundle builds'
    )
    tree = ast.parse((ROOT / 'tools/installer/build.py').read_text())
    function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == 'macos_signing_args'
    )
    for node in ast.walk(function):
        if isinstance(node, ast.Call):
            assert ast.unparse(node.func) in {'os.environ.get', 'RuntimeError'}, (
                'The isolated signing-argument observer may only read config and raise errors'
            )
    namespace = {'os': SimpleNamespace(environ={})}
    module = ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[]))
    exec(compile(module, '<isolated signing arguments>', 'exec'), namespace)  # noqa: S102 - calls restricted above
    for enabled in ('', '0'):
        namespace['os'].environ = {'EDI_CODESIGN': enabled, 'EDI_CODESIGN_MAC_IDENTITY': 'public'}
        assert namespace['macos_signing_args']() == ['--sign', '-'], (
            'An unsigned PR build must choose ad hoc signing even with a public identity present'
        )
    namespace['os'].environ = {'EDI_CODESIGN': '1', 'EDI_CODESIGN_MAC_IDENTITY': 'public'}
    assert namespace['macos_signing_args']() == ['--timestamp', '--sign', 'public'], (
        'Enabled application signing must use the identity and timestamp without hardened runtime'
    )
    namespace['os'].environ = {'EDI_CODESIGN': '1'}
    with pytest.raises(RuntimeError, match='identity'):
        namespace['macos_signing_args']()


def test_signing_entries_keep_the_exact_secret_and_variable_split():
    document = workflow()
    selected = signing_steps()
    assert selected, 'The installer workflow must import its release signing credentials'
    references = re.findall(r'(secrets|vars)[.](CODESIGN_[A-Z0-9_]+)', str(document))
    assert {name for kind, name in references if kind == 'secrets'} == SECRET_NAMES, (
        'ADR-0091 names exactly the seven private signing entries'
    )
    assert {name for kind, name in references if kind == 'vars'} == VARIABLE_NAMES, (
        'ADR-0091 keeps team, identity, Windows host and keypair alias as variables'
    )
    for name in SECRET_NAMES | VARIABLE_NAMES:
        assert name not in str(document.get('env', {})) + str(
            document['jobs']['installers'].get('env', {})
        ), 'Signing entries must be scoped to guarded steps so PR jobs stay secret-free'
    assert any('apple-actions/import-codesign-certs@' in s.get('uses', '') for s in selected), (
        'macOS must import the signing certificate with the Apple action'
    )


def test_macos_installer_is_hardened_timestamped_notarised_stapled_and_verified(
    tmp_path, monkeypatch
):
    observe_installed_maintenance(tmp_path / 'valid', monkeypatch)
    for failure in ('verify', 'authority'):
        observe_installed_maintenance(tmp_path / failure, monkeypatch, failure=failure)
    text = executable_text()
    for command in [
        'codesign',
        '--options',
        'runtime',
        '--timestamp',
        'notarytool',
        'submit',
        '--wait',
        'stapler',
        'staple',
        'spctl',
        '--assess',
        '--verify',
    ]:
        assert command in text, (
            'macOS must sign, timestamp, notarise, staple and verify the installer'
        )
    assert 'notarytool' in text and 'CODESIGN_MAC_NOTARY_PASSWORD' in str(signing_steps()), (
        'Installer notarisation must use the approved Apple ID credentials'
    )


def test_windows_uses_digicert_simple_signing_and_verifies_declared_executables():
    selected = [s for s in signing_steps() if 'digicert/' in s.get('uses', '')]
    assert selected, 'Windows releases must sign with the DigiCert action'
    assert all(s['uses'] == 'digicert/code-signing-software-trust-action@v1' for s in selected), (
        'Windows must use the approved DigiCert signing action version'
    )
    assert all('simple' in str(s.get('with', {})).lower() for s in selected), (
        'The DigiCert action must use simple-signing mode'
    )
    text = executable_text()
    assert all(word in text for word in ['signtool', 'verify', '/pa', '.exe']), (
        'Windows release packaging must verify shipped executables with signtool verify /pa'
    )
    assert 'CODESIGN_WIN_CERT_P12_BASE64' in str(signing_steps()), (
        'Windows signing must decode the approved client certificate'
    )


def test_signing_failure_cannot_upload_release_artifacts(tmp_path, monkeypatch):
    for failure in ('sign', 'verify'):
        with pytest.raises(subprocess.CalledProcessError):
            observe_maintenance_package(
                tmp_path / failure, monkeypatch, release=True, online=False, failure=failure
            )
    selected = signing_steps()
    assert selected, 'Release publication must have required signing predecessors'
    assert all(s.get('continue-on-error', 'false') == 'false' for s in selected), (
        'Signing and verification errors must stop the installer job'
    )
    uploads = [
        s
        for s in steps()
        if s.get('uses') == 'actions/upload-artifact@v4'
        and s.get('with', {}).get('path')
        in {'build/installer/delivery', 'build/installer/components'}
    ]
    assert len(uploads) == 2, (
        'Release deliveries and components must retain their qualified uploads'
    )
    for upload in uploads:
        assert steps().index(upload) > max(steps().index(s) for s in selected), (
            'All release uploads must follow signing and verification'
        )
        assert 'always(' not in upload.get('if', '') and 'failure(' not in upload.get('if', ''), (
            'Release uploads must retain the default successful-predecessor condition'
        )
    for step in selected:
        assert not re.search(r'\|\|\s*(?:true|:)|continue-on-error', step.get('run', '')), (
            'Signing commands must propagate failures instead of suppressing them'
        )

    for upload in uploads:
        for platform in ('Windows', 'macOS'):
            assert not condition(
                upload, 'workflow_dispatch', 'refs/heads/main', True, platform, failed=True
            ), 'A failed signing predecessor must block delivery and component uploads'


def test_prompt_trial_records_live_only_in_contributor_docs():
    user = ROOT / 'website/surfaces/docs'
    assert not (user / 'assistant-prompt-trials.md').exists(), (
        'The internal prompt-trial page must leave user documentation'
    )
    for path in [*user.rglob('*.md'), ROOT / 'website/surfaces/mkdocs.yml']:
        assert 'assistant-prompt-trials' not in path.read_text(), (
            'User pages and navigation must contain no prompt-trial links'
        )
    developer = ROOT / 'docs/dev/assistant-prompt-trials.md'
    assert developer.is_file(), 'Contributor docs must retain the prompt-trial record'
    assert '2026' in developer.read_text(), (
        'The moved trial records must retain their dated evidence'
    )


@pytest.mark.parametrize('interface', ['python', 'cli'])
def test_assistant_tutorial_has_one_plain_dated_sentence(interface):
    text = (ROOT / f'website/surfaces/docs/{interface}/tutorials/assistant.md').read_text()
    lines = [line for line in text.splitlines() if re.search(r'last checked', line, re.IGNORECASE)]
    assert len(lines) == 1, 'Each assistant tutorial must carry one plain prompt-check sentence'
    assert r'2026' in lines[0] and re.search(
        r'another assistant.*different steps', lines[0], re.IGNORECASE
    ), 'The sentence must date the check and say another assistant may take different steps'
    assert not re.search(r'\[[^]]+\]\(', lines[0]), (
        'The prompt-check sentence must be plain prose with no link to internal trial records'
    )


def test_app_signing_omits_hardened_runtime_while_installer_requires_it():
    commands = []
    for path in (ROOT / 'tools/installer').glob('*.py'):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if not isinstance(node, (ast.List, ast.Tuple)):
                continue
            words = [part.value for part in node.elts if isinstance(part, ast.Constant)]
            if 'codesign' in words and '--sign' in words:
                commands.append(words)
    assert any('--options' not in words and 'runtime' not in words for words in commands), (
        'The application must be signed without hardened runtime, as decided for this release'
    )
    assert any(
        '--options' in words and 'runtime' in words and '--timestamp' in words
        for words in commands
    ), 'The downloaded installer must be signed with hardened runtime and a timestamp'


REQUIRED_SIGNED = (
    'windows-app',
    'windows-cli',
    'windows-offline',
    'windows-online',
    'macos-app',
    'macos-cli',
    'macos-offline',
    'macos-online',
)


def signed_members(sources, workflow_steps):
    functions = {
        node.name: node
        for text in sources.values()
        for node in ast.parse(text).body
        if isinstance(node, ast.FunctionDef)
    }

    def words(name, seen=None):
        seen = set() if seen is None else seen
        if name in seen or name not in functions:
            return set()
        seen.add(name)
        result = set()
        for node in ast.walk(functions[name]):
            if isinstance(node, (ast.List, ast.Tuple)):
                result.update(
                    item.value
                    for item in node.elts
                    if isinstance(item, ast.Constant) and isinstance(item.value, str)
                )
                result.update(
                    item.func.id
                    for item in node.elts
                    if isinstance(item, ast.Call) and isinstance(item.func, ast.Name)
                )
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id != 'build_cli'
            ):
                result.update(words(node.func.id, seen))
        return result

    def windows(tokens):
        return {'smctl', 'sign', 'verify', '/pa'} <= tokens

    def macos(tokens, *, notarised=False):
        required = {'codesign', '--sign', '--timestamp', '--verify'}
        if notarised:
            required |= {'notarytool', 'submit', '--wait'}
        return required <= tokens

    observed = set()
    build = functions.get('build')
    if build is not None:
        for call in ast.walk(build):
            if not (isinstance(call, ast.Call) and isinstance(call.func, ast.Name) and call.args):
                continue
            if 'stage' not in ast.unparse(call.args[0]):
                continue
            tokens = words(call.func.id)
            if windows(tokens):
                observed.add('windows-app')
            if macos(tokens):
                observed.add('macos-app')
    cli = words('build_cli')
    if windows(cli):
        observed.add('windows-cli')
    if macos(cli, notarised=True):
        observed.add('macos-cli')
    seal = words('seal_installer')
    for kind, folder in [('offline', 'package'), ('online', 'online')]:
        selected = [
            step
            for step in workflow_steps
            if re.search(r'package[.]py.*\bseal\b', step.get('run', ''))
            and f'build/installer/{folder}' in step.get('run', '')
        ]
        if selected and windows(seal):
            observed.add('windows-' + kind)
        if selected and macos(seal, notarised=True):
            observed.add('macos-' + kind)
    return observed


@pytest.mark.parametrize('member', REQUIRED_SIGNED)
def test_owner_declared_app_cli_and_installer_signatures(member, tmp_path, monkeypatch):
    if member in {'macos-offline', 'macos-online'}:
        observe_maintenance_package(
            tmp_path, monkeypatch, release=True, online=member.endswith('online')
        )
    sources = {
        name: (ROOT / 'tools/installer' / name).read_text()
        for name in ('build.py', 'package.py', 'standalone_cli.py')
    }
    assert member in signed_members(sources, steps()), (
        'The owner-declared signed set requires the app, CLI and both installer kinds on each '
        'platform, including notarisation of the macOS CLI and installers: ' + member
    )


@pytest.mark.parametrize('omitted', REQUIRED_SIGNED)
def test_signature_coverage_refuses_each_omitted_required_member(omitted):
    sources = {
        'control.py': """
def sign_windows(path):
    run(['smctl', 'sign', path])
    run(['signtool', 'verify', '/pa', path])
def sign_macos_app(path):
    run(['codesign', '--sign', 'identity', '--timestamp', path])
    run(['codesign', '--verify', path])
def notarise_macos(path):
    sign_macos_app(path)
    run(['xcrun', 'notarytool', 'submit', path, '--wait'])
def build():
    sign_windows(stage / 'bin/EasyDiffraction.exe')
    sign_macos_app(stage / 'EasyDiffraction.app')
def build_cli():
    sign_windows(binary)
    notarise_macos(binary)
def seal_installer():
    sign_windows(installer)
    notarise_macos(installer)
"""
    }
    workflow_steps = [
        {'run': 'python tools/installer/package.py seal --output build/installer/package'},
        {'run': 'python tools/installer/package.py seal --output build/installer/online'},
    ]
    assert signed_members(sources, workflow_steps) == set(REQUIRED_SIGNED), (
        'The authored positive route control must cover the whole owner-declared signed set'
    )
    changed = copy.deepcopy(workflow_steps)
    if omitted.endswith(('offline', 'online')):
        index = 0 if omitted.endswith('offline') else 1
        changed.pop(index)
    else:
        tree = ast.parse(sources['control.py'])
        target = 'build_cli' if omitted.endswith('cli') else 'build'
        function = next(node for node in tree.body if node.name == target)
        index = 0 if omitted.startswith('windows') else 1
        function.body.pop(index)
        sources['control.py'] = ast.unparse(tree)
    assert omitted not in signed_members(sources, changed), (
        'Omitting a required signing route must remain detectable for each declared member: '
        + omitted
    )


MAC_IDENTITY = 'Developer ID Application: European Spallation Source Eric (W2AG9MPZ43)'


def observe_maintenance_package(  # noqa: PLR0914, PLR0915 - one packaging transaction
    directory, monkeypatch, *, release, online, failure=None
):
    spec = importlib.util.spec_from_file_location(
        'maintenance_package', ROOT / 'tools/installer/package.py'
    )
    package = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(package)
    stage, tools, output = [directory / name for name in ('stage', 'ifw', 'output')]
    app = stage / 'EasyDiffraction.app/Contents/MacOS/EasyDiffraction'
    app.parent.mkdir(parents=True)
    app.write_bytes(b'application')
    assistant = stage / 'libexec/edi/codex/helper'
    assistant.parent.mkdir(parents=True)
    assistant.write_bytes(b'optional helper')
    template = tools / 'bin/installerbase'
    template.parent.mkdir(parents=True)
    template.write_bytes(b'IFW arm64 template')
    template.chmod(0o755)
    events = []
    selected = [
        step
        for step in steps()
        if re.search(r'package[.]py.* maintenance-tool ', step.get('run', ''))
    ]
    assert len(selected) == 1, (
        'The workflow must build the macOS maintenance tool once before both installers'
    )
    build_step = selected[0]
    event, ref = (
        ('workflow_dispatch', 'refs/heads/main')
        if release
        else ('pull_request', 'refs/pull/54/merge')
    )
    assert condition(build_step, event, ref, release, 'macOS'), (
        'Both release and PR macOS builds must prepare a maintenance tool'
    )
    assert not private_access(build_step, 'pull_request', 'refs/pull/54/merge', False, 'macOS'), (
        'PR maintenance builds must receive no effective private signing credentials'
    )
    for folder in ('package', 'online'):
        consumers = [
            step
            for step in steps()
            if re.search(r'package[.]py.* package ', step.get('run', ''))
            and 'build/installer/' + folder + '"' in step.get('run', '')
        ]
        assert len(consumers) == 1 and '--maintenance-tool' in consumers[0]['run'], (
            'Both macOS installer transports must consume the separately built maintenance tool'
        )
        assert steps().index(build_step) < steps().index(consumers[0]), (
            'The separately built maintenance tool must precede each installer package step'
        )

    def maintenance_target(args):
        return args and any(
            word in Path(str(args[-1])).name.lower() for word in ('maintenance', 'installerbase')
        )

    def command(args, **_kwargs):
        args = list(map(str, args))
        events.append(args)
        if args[0] == 'codesign' and maintenance_target(args):
            signing = '--sign' in args
            verifying = '--verify' in args
            if (failure == 'sign' and signing) or (failure == 'verify' and verifying):
                raise subprocess.CalledProcessError(1, args)
        if Path(args[0]).name == 'binarycreator':
            destination = (
                Path(_kwargs['cwd']) / 'MaintenanceTool.app' if '--mt' in args else Path(args[-1])
            )
            if destination.suffix == '.app':
                executable = destination / 'Contents/MacOS' / destination.stem
                executable.parent.mkdir(parents=True, exist_ok=True)
                executable.write_bytes(b'IFW generated binary')
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(b'IFW generated binary')
        if args[0] == 'ditto':
            if '-c' in args:
                Path(args[-1]).write_bytes(b'notary archive')
            else:
                package.shutil.copytree(args[-2], args[-1])
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps({'status': 'Accepted'}) if 'notarytool' in args else '',
            stderr='Authority=' + MAC_IDENTITY,
        )

    def archive(installer, _runtime, **_kwargs):
        events.append(['archive', str(installer)])
        path = installer.with_suffix('.zip')
        path.write_bytes(b'archive')
        return path

    with monkeypatch.context() as patch:
        patch.setattr(package, 'SYSTEM', 'macos')
        patch.setattr(package, 'PLATFORM_ID', 'macos-arm64')
        patch.setattr(package, 'run', command)
        patch.setattr(package.subprocess, 'run', command)
        patch.setattr(package.subprocess, 'check_output', lambda *_a, **_kw: 'arm64')
        patch.setattr(package, 'archive_installer', archive)
        patch.setenv('EDI_CODESIGN', '1' if release else '')
        patch.setenv('EDI_CODESIGN_MAC_IDENTITY', MAC_IDENTITY)
        for name in ('EDI_NOTARY_APPLE_ID', 'EDI_NOTARY_PASSWORD', 'EDI_NOTARY_TEAM_ID'):
            patch.setenv(name, 'offline-fake')
        assert hasattr(package, 'build_maintenance_tool'), (
            'macOS must build a maintenance tool separately from the distribution installers'
        )
        bundle = package.build_maintenance_tool(tools, directory / 'maintenance')
        package.package_app(
            stage,
            tools,
            output,
            '2026.11.1',
            repository_url='file:///local-components/' if online else None,
            maintenance_tool=bundle,
        )

    signed = [
        args
        for args in events
        if args[0] == 'codesign' and '--sign' in args and maintenance_target(args)
    ]
    assert signed, 'Both macOS transports must sign a separate maintenance binary before packaging'
    target = Path(signed[0][-1])
    assert target != template and target.exists(), (
        'The installed maintenance binary must be separate from the IFW template'
    )
    assert template.read_bytes() == b'IFW arm64 template', (
        'Maintenance preparation must preserve the original IFW template'
    )
    sign = signed[0]
    assert sign[sign.index('--sign') + 1] == (MAC_IDENTITY if release else '-'), (
        'Maintenance signing must use the ADR-0091 identity for release and ad hoc for PRs'
    )
    if release:
        assert {'--options', 'runtime', '--timestamp'} <= set(sign), (
            'Release maintenance signing requires hardened runtime and a timestamp'
        )
        verified = [
            args
            for args in events
            if args[0] == 'codesign'
            and '--verify' in args
            and '--strict' in args
            and args[-1] == str(target)
        ]
        assert verified, (
            'A release maintenance signature must pass strict verification before packaging'
        )
    creators = [
        args
        for args in events
        if Path(args[0]).name == 'binarycreator'
        and any(flag in args for flag in ('--hybrid', '--online-only'))
    ]
    assert creators and events.index(sign) < events.index(creators[-1]), (
        'Maintenance signing must finish before the distribution binarycreator runs'
    )
    if release:
        assert events.index(verified[-1]) < events.index(creators[-1]), (
            'A failed maintenance verification must stop before IFW embeds the payload'
        )
    source = output / 'source'
    configurations = list(source.rglob('config.xml'))
    assert configurations, 'Both transports must produce an IFW configuration'
    scripts = '\n'.join(path.read_text() for path in source.rglob('*.qs'))
    configured = any(
        ET.parse(path).getroot().findtext('MaintenanceToolBinary')  # noqa: S314 - generated XML
        for path in configurations
    )
    assert configured or 'installer.setInstallerBaseBinary(' in scripts, (
        'IFW must install the supplied binary rather than regenerate it from the signed installer'
    )
    payloads = [
        path
        for path in source.glob('packages/*/data/**/*')
        if path.is_file() and path.name == 'MaintenanceTool'
    ]
    assert payloads, 'The separately signed maintenance binary must reach the package payload'
    assert all(
        path.read_bytes() == (target / 'Contents/MacOS/MaintenanceTool').read_bytes()
        for path in payloads
    ), 'The packaged maintenance binary must retain its signed bytes'
    assert target.name in scripts or configured, (
        'The installer override must name the packaged maintenance binary'
    )


def observe_installed_maintenance(directory, monkeypatch, failure=None):
    spec = importlib.util.spec_from_file_location(
        'installed_package', ROOT / 'tools/installer/package.py'
    )
    package = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(package)
    installer = directory / 'installer.app'
    executable = installer / 'Contents/MacOS/installer'
    executable.parent.mkdir(parents=True)
    executable.write_bytes(b'installer')
    output = directory / 'exercise'
    target = output / 'installed app'
    maintenance = target / 'MaintenanceTool.app/Contents/MacOS/MaintenanceTool'
    events = []

    def command(args, **_kwargs):
        args = list(map(str, args))
        events.append(args)
        if args[0] == 'codesign' and '--verify' in args and failure == 'verify':
            raise subprocess.CalledProcessError(1, args)
        if 'install' in args:
            maintenance.parent.mkdir(parents=True)
            maintenance.write_bytes(b'signed maintenance')
            app = target / 'EasyDiffraction.app/Contents/MacOS/EasyDiffraction'
            app.parent.mkdir(parents=True)
            app.write_bytes(b'app')
            (target / 'payload-manifest.json').write_text('{}')
        if '--testmode' in args:
            smoke = Path(args[-1])
            smoke.mkdir()
            (smoke / 'window.png').write_bytes(b'window')
            (smoke / 'result.json').write_text(
                json.dumps({
                    'passed': True,
                    'assistant_available': False,
                    'svg_images': ['image.svg'],
                })
            )
        if 'purge' in args:
            package.shutil.rmtree(target)
        authority = (
            'Developer ID Application: Someone Else (OTHERTEAM)'
            if failure == 'authority'
            else MAC_IDENTITY
        )
        return SimpleNamespace(returncode=0, stdout='', stderr='Authority=' + authority + '\n')

    with monkeypatch.context() as patch:
        patch.setattr(package, 'SYSTEM', 'macos')
        patch.setattr(package, 'run', command)
        patch.setattr(package.subprocess, 'run', command)
        patch.setattr(package.subprocess, 'check_output', lambda args, **_kw: command(args).stderr)
        patch.setenv('EDI_CODESIGN', '1')
        patch.setenv('EDI_CODESIGN_MAC_IDENTITY', MAC_IDENTITY)
        if failure:
            with pytest.raises((RuntimeError, subprocess.CalledProcessError)):
                package.exercise_installer(installer, output)
            assert not any('purge' in args for args in events), (
                'An invalid installed signature or wrong Developer ID must stop '
                'before executing MaintenanceTool'
            )
        else:
            package.exercise_installer(installer, output)
            verified = [
                args
                for args in events
                if args[0] == 'codesign'
                and '--verify' in args
                and '--strict' in args
                and args[-1] in {str(maintenance), str(maintenance.parents[2])}
            ]
            assert verified, (
                'Release qualification must strictly verify the installed maintenance tool'
            )
            displayed = [
                args
                for args in events
                if args[0] == 'codesign'
                and any(flag in args for flag in ('--display', '-d', '-dv', '-dvv'))
            ]
            assert displayed, (
                'Installed maintenance qualification must inspect its Developer ID authority'
            )
            purge = next(args for args in events if 'purge' in args)
            assert events.index(verified[-1]) < events.index(purge) and events.index(
                displayed[-1]
            ) < events.index(purge), (
                'Installed signature and Developer ID checks must both precede '
                'maintenance execution'
            )
