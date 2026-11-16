# SPDX-License-Identifier: BSD-3-Clause
"""Offline installer contract from ADR-0091 and the release signing decisions."""

import ast
import re
from pathlib import Path

import pytest
import yaml

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
        if re.search(r'CODESIGN_|codesign|notarytool|stapler|digicert/|signing[.]py', str(step))
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


def condition(step, event, ref, release, platform):
    value = str(step.get('if', 'true')).strip().removeprefix('${{').removesuffix('}}')
    atoms = {
        'github.event_name': event,
        'github.ref': ref,
        'runner.os': platform,
        'inputs.release_plan_run': '1234' if release else '',
        'env.EDI_RELEASE_PLAN': '/release-plan' if release else '',
    }
    for name, item in atoms.items():
        value = re.sub(r'\b' + re.escape(name) + r'\b', repr(item), value)
    value = value.replace('&&', ' and ').replace('||', ' or ')
    value = re.sub(r'!(?!=)', ' not ', value)
    value = re.sub(r'\btrue\b', 'True', value)
    value = re.sub(r'\bfalse\b', 'False', value)
    value = value.replace('success()', 'True').replace('cancelled()', 'False')
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
        'Signing conditions must resolve from the event, branch, release input and platform'
    )
    return bool(condition_value(tree.body))


def condition_value(node):
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.UnaryOp):
        return not condition_value(node.operand)
    if isinstance(node, ast.BoolOp):
        values = [condition_value(item) for item in node.values]
        return all(values) if isinstance(node.op, ast.And) else any(values)
    values = [condition_value(item) for item in [node.left, *node.comparators]]
    return all(
        (left == right) == isinstance(operator, ast.Eq)
        for left, operator, right in zip(values, node.ops, values[1:], strict=False)
    )


@pytest.mark.parametrize('platform', ['macOS', 'Windows'])
def test_signing_is_present_and_never_reaches_pull_requests_or_other_branches(platform):
    selected = signing_steps()
    assert selected, 'Release installers must contain signing steps'
    assert any(condition(s, 'push', 'refs/heads/main', False, platform) for s in selected), (
        'Main pushes must sign each supported installer platform'
    )
    assert any(
        condition(s, 'workflow_dispatch', 'refs/heads/main', True, platform) for s in selected
    ), 'Release dispatches on main must sign each supported installer platform'
    for event, ref, release in [
        ('pull_request', 'refs/pull/53/merge', False),
        ('pull_request', 'refs/heads/main', True),
        ('push', 'refs/heads/feature', False),
        ('workflow_dispatch', 'refs/heads/feature', True),
        ('workflow_dispatch', 'refs/heads/main', False),
        ('schedule', 'refs/heads/main', False),
    ]:
        assert not any(condition(s, event, ref, release, platform) for s in selected), (
            'Only release dispatches on main and main pushes may access signing credentials'
        )


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


def test_macos_installer_is_hardened_timestamped_notarised_stapled_and_verified():
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


def test_windows_uses_digicert_simple_signing_and_verifies_all_shipped_executables():
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


def test_signing_failure_cannot_upload_release_artifacts():
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


def test_windows_signing_covers_recursive_executables_before_and_after_packaging():
    text = executable_text() + str(signing_steps())
    assert any(pattern in text for pattern in ['*.exe', '**/*.exe']), (
        'Windows signing must select every shipped executable, not only a named installer'
    )
    assert any(word in text for word in ['rglob', '-Recurse', 'recurse', '**/*.exe']), (
        'Windows signing must cover executables in nested payload folders'
    )
    windows = [s for s in signing_steps() if 'digicert/' in s.get('uses', '')]
    packaging = [
        i
        for i, step in enumerate(steps())
        if 'package.py' in step.get('run', '') and ' package ' in step.get('run', '')
    ]
    assert windows and packaging, 'Windows release packaging must retain signed payload assembly'
    assert min(steps().index(s) for s in windows) < min(packaging), (
        'App and maintenance executables must be signed before they enter installer payloads'
    )
    assert max(steps().index(s) for s in windows) > max(packaging), (
        'Both generated installers must be signed after package assembly'
    )
