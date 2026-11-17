"""Public tree checks against the dated content review and local snapshot invariants.

No network operation is performed here. Live CI, deployment and settings are
operator evidence; these gates check the versioned inputs and local rehearsal.
"""

from __future__ import annotations

import ast
import bz2
import gzip
import hashlib
import io
import json
import lzma
import os
import re
import runpy
import shlex
import struct
import subprocess
import sys
import tarfile
import time
import tomllib
import zipfile
import zlib
from functools import cache
from pathlib import Path

import pytest
import yaml
from compression import zstd

from tests.fixtures.e09_t75_workflow import active

ROOT = Path(__file__).resolve().parents[3]
ORACLE = json.loads((ROOT / 'tests/fixtures/e04_t12_public_release/oracle.json').read_text())
# Construct forbidden spellings so the scanner does not manufacture a private reference.
PROCESS = re.compile(r'\b(?:[CE]\d{2}-T\d+[a-z]?|I-\d{4}|ORG-\d{4}|re[l]ay)\b', re.IGNORECASE)
PRIVATE = re.compile(
    r'crysta\s+A[D]R-\d+|enhantica/c[r]ysta/(?:blob|tree)/'
    r'|c[r]ysta/(?:tests|docs|knowledge|core)/'
    r'|(?:~|/h[o]me/[^/\s]+)/ru[n]s/|/h[o]me/[^/\s]+/|/U[s]ers/[^/\s]+/'
)
# Exact npm release files and upstream members pinned in the dependency notice.
VENDOR = json.loads((ROOT / 'tests/fixtures/report_transport/vendor.json').read_text())
SCRIPTS = ROOT / 'tools/public-release'
SECRET = re.compile(
    r'\bgh[pousr]_[A-Za-z0-9]{36,}\b|\bgithub_pat_[A-Za-z0-9_]{60,}\b'
    r'|\b(?:AKIA|ASIA)[0-9A-Z]{16}\b|\bxox[abposr]-[A-Za-z0-9-]{10,}\b'
    r'|\bAIza[0-9A-Za-z_-]{35}\b|-----BEGIN (?:[A-Z]+ )*PRIVATE KEY(?: BLOCK)?-----'
    r'|(?i:\baws_?secret_?(?:access_?)?key\s*[:=]\s*["\']?[A-Za-z0-9/+=]{40}\b)'
)


def decoded_texts(name, raw, depth=0):
    """Independent publication observer: containers never stand in for their contents."""
    try:
        yield from _decoded_texts(name, raw, depth)
    except (
        OSError,
        EOFError,
        ValueError,
        RuntimeError,
        zipfile.BadZipFile,
        tarfile.TarError,
        lzma.LZMAError,
        zstd.ZstdError,
        zlib.error,
        struct.error,
    ) as error:
        raise AssertionError(
            'publication checks must refuse unreadable container: ' + name
        ) from error


def png_texts(name, raw, depth):
    # PNG stores publication prose in compressed text chunks too.
    yield name, raw.decode('utf-8', errors='replace')
    offset = 8
    while offset < len(raw):
        size, kind = struct.unpack('>I4s', raw[offset : offset + 8])
        body = raw[offset + 8 : offset + 8 + size]
        assert len(body) == size and offset + size + 12 <= len(raw), (
            'publication checks must refuse truncated PNG chunks'
        )
        offset += size + 12
        keyword, _, rest = body.partition(b'\0')
        if kind == b'zTXt':
            content = zlib.decompress(rest[1:])
        elif kind == b'iTXt' and rest[:1] == b'\x01':
            _language, _, rest = rest[2:].partition(b'\0')
            _translated, _, text = rest.partition(b'\0')
            content = zlib.decompress(text)
        else:
            continue
        yield from decoded_texts(name + '!' + keyword.decode('latin-1'), content, depth + 1)


def _decoded_texts(name, raw, depth):
    assert depth < 8, 'publication checks must refuse excessive archive nesting'
    lower = name.lower()
    if raw.startswith(b'\x89PNG\r\n\x1a\n'):
        yield from png_texts(name, raw, depth)
        return
    if lower.endswith('.zip') or zipfile.is_zipfile(io.BytesIO(raw)):
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            yield name + '!metadata', archive.comment.decode('utf-8', errors='replace')
            for info in archive.infolist():
                yield (
                    name + '!metadata',
                    info.filename + info.comment.decode('utf-8', errors='replace'),
                )
                assert info.file_size <= 64 * 1024 * 1024, (
                    'publication checks must refuse oversized archive members'
                )
                if not info.is_dir():
                    yield from decoded_texts(
                        name + '!' + info.filename, archive.read(info), depth + 1
                    )
        return
    codecs = (
        (('.gz', '.tgz'), b'\x1f\x8b', gzip.decompress),
        (('.bz2', '.tbz2'), b'BZh', bz2.decompress),
        (('.xz', '.txz'), b'\xfd7zXZ\x00', lzma.decompress),
        (('.zst',), b'\x28\xb5\x2f\xfd', zstd.decompress),
    )
    for endings, signature, decompress in codecs:
        if lower.endswith(endings) or raw.startswith(signature):
            content = decompress(raw)
            assert len(content) <= 64 * 1024 * 1024, (
                'publication checks must refuse oversized decompressed streams'
            )
            inner = next(
                (name[: -len(suffix)] for suffix in endings if lower.endswith(suffix)),
                name + '.decoded',
            )
            if lower.endswith(('.tgz', '.tbz2', '.txz')):
                inner += '.tar'
            yield from decoded_texts(name + '!' + inner.rsplit('/', 1)[-1], content, depth + 1)
            return
    if lower.endswith('.tar') or raw[257:263] in {b'ustar\x00', b'ustar '}:
        with tarfile.open(fileobj=io.BytesIO(raw), mode='r:') as archive:
            for member in archive:
                yield name + '!metadata', member.name + '\n' + member.linkname
                assert member.isfile() or member.isdir(), (
                    'publication checks must refuse members that cannot be read as files'
                )
                assert member.size <= 64 * 1024 * 1024, (
                    'publication checks must refuse oversized archive members'
                )
                if member.isfile():
                    handle = archive.extractfile(member)
                    assert handle is not None, 'publication checks must read every file member'
                    yield from decoded_texts(name + '!' + member.name, handle.read(), depth + 1)
        return
    assert not lower.endswith((
        '.7z',
        '.rar',
        '.lz4',
        '.lzma',
        '.br',
        '.z',
    )) and not raw.startswith((b'7z\xbc\xaf\x27\x1c', b'Rar!\x1a\x07', b'\x04\x22\x4d\x18')), (
        'publication checks must refuse unsupported compressed containers'
    )
    yield name, raw.decode('utf-8', errors='replace')


def run(*args, cwd=ROOT, env=None, timeout=None):
    return subprocess.run(
        args, cwd=cwd, env=env, timeout=timeout, capture_output=True, text=True, check=False
    )


def require_success(result, requirement):
    assert result.returncode == 0, (
        'public release requirement failed: '
        + requirement
        + '\n'
        + result.stdout[-3000:]
        + result.stderr[-3000:]
    )


def tracked_texts():
    listing = run('git', 'ls-files', '-z', cwd=ROOT)
    require_success(listing, 'the public scan must enumerate the complete tracked tree')
    for relative in listing.stdout.split('\0'):
        path = ROOT / relative
        if relative and path.is_file():
            yield from decoded_texts(relative, path.read_bytes())


@cache
def publication_texts():
    # One immutable inventory for the independent predicates in this module.
    # The first predicate records the decoding cost in its own measured call.
    return tuple(tracked_texts())


def test_test_and_tool_identity_is_independent_of_checkout_name():
    findings = []
    for directory in ('tests', 'tools'):
        for path in sorted((ROOT / directory).rglob('*.py')):
            tree = ast.parse(path.read_text(encoding='utf-8'))
            findings.extend(
                f'{path.relative_to(ROOT)}:{node.lineno}'
                for node in ast.walk(tree)
                if isinstance(node, ast.Attribute)
                and node.attr in {'name', 'stem'}
                and isinstance(node.value, ast.Name)
                and node.value.id in {'ROOT', 'REPO'}
            )
    assert not findings, (
        'Public tests and tools must use declared product identities rather than the '
        'checkout root basename: ' + ', '.join(findings)
    )


def private_findings(entries):
    synthetic = 'tests/fixtures/onboarding/privacy_representations.json'
    expected = '73855c7ef29eb9a2c6c7ecd9733cfb494b4ad9930a0033a53e0bac8f256a0491'
    return [
        name
        for name, text in entries
        if not (name == synthetic and hashlib.sha256(text.encode()).hexdigest() == expected)
        and any(prefix in text for prefix in ('crysta', '/home/', '/Users/', '~/r' + 'uns/'))
        and PRIVATE.search(text)
    ]


def test_tree_has_no_personal_paths_or_private_citations():
    findings = private_findings(publication_texts())
    assert not findings, (
        'The public tree has no personal or private references; only exact synthetic privacy '
        'test inputs retain their independently authored redaction witnesses: '
        + ', '.join(findings[:20])
    )


def process_findings(entries):
    findings = []
    for name, text in entries:
        release = VENDOR.get(name)
        if release and hashlib.sha256(text.encode()).hexdigest() == release['sha256']:
            continue
        if not any(prefix in text.casefold() for prefix in ('-t', 'i-', 'org-', 're' + 'lay')):
            continue
        if not PROCESS.search(text):
            continue
        for number, original_line in enumerate(text.splitlines(), 1):
            if not PROCESS.search(original_line):
                continue
            line = original_line
            # Only actual Python test function names and test path strings keep labels.
            if re.match(r'\s*(?:async\s+)?def test_[\w]+\(', line):
                line = re.sub(r'(?<=test_)[\w]+(?=\()', '', line)
            # Native case labels and serialized node ids are actual test names too.
            line = re.sub(
                r'(TEST_CASE(?:_METHOD)?\s*\(\s*(?:[\w:<>]+\s*,\s*)?)"[^"\n]+"', r'\1""', line
            )
            line = re.sub(
                r'(?:tests/)?(?:[\w.-]+/)*test_[\w.-]+\.(?:py|cpp|qml)(?:::[^\t"\n]+)?', '', line
            )
            if PROCESS.search(line):
                findings.append(f'{name}:{number}')
    return findings


def test_process_references_are_confined_to_test_names():
    findings = process_findings(publication_texts())
    assert not findings, (
        'public prose and production comments must replace process tags with local ADR reasons; '
        'only test names retain their labels: ' + ', '.join(findings[:20])
    )


def test_source_and_application_licences_are_complete():
    source = ROOT / 'LICENSE'
    application = ROOT / 'COPYING'
    assert source.is_file() and application.is_file(), (
        'the public tree must ship the source BSD licence and the built application GPL text'
    )
    source_text, app_text = source.read_text(), application.read_text()
    for clause in (
        'BSD 3-Clause',
        'Copyright',
        'Redistribution and use',
        'Neither the name',
        'AS IS',
    ):
        assert clause in source_text, (
            'the source licence must contain the complete BSD grant: ' + clause
        )
    for clause in (
        'GNU GENERAL PUBLIC LICENSE',
        'Version 3',
        'Corresponding Source',
        'Installation Information',
        'No Surrender',
    ):
        assert clause in app_text, 'the app must carry the full GPL version 3 licence: ' + clause
    cmake = '\n'.join(p.read_text() for p in (ROOT / 'app').rglob('CMakeLists.txt'))
    assert 'COPYING' in cmake, (
        'the built application distribution must install its GPL licence text'
    )


@pytest.mark.parametrize('component', sorted(ORACLE['components']))
def test_dependency_notice_covers_review_component(component):
    notice = ROOT / 'THIRD-PARTY-NOTICES'
    assert notice.is_file(), 'the release must bundle the complete dependency notices locally'
    text = notice.read_text()
    if component in {'diffraction-lib', 'easydiffractionbeta'}:
        acknowledgements = re.search(r'(?ms)^Acknowledgements\n-+\n(.*?)(?=^## |\Z)', text)
        if component == 'diffraction-lib':
            assert acknowledgements and component in acknowledgements[1], (
                'The element-data source retains its acknowledgement without claiming bundling'
            )
        assert not re.search(r'(?m)^## ' + re.escape(component) + r'$', text), (
            'A reference-only project has no redistributed component notice section'
        )
        matrix = (ROOT / 'DEPENDENCIES.md').read_text()
        assert not re.search(r'(?m)^\|\s*' + re.escape(component) + r'\s*\|', matrix), (
            'A reference-only project is absent from the bundled dependency matrix'
        )
        return
    # Check a component's own section, not a licence token elsewhere in the document.
    match = re.search(r'(?im)^.*(?:#+|\[|<h\d).*' + re.escape(component) + r'.*$', text)
    assert match, 'every reviewed shipped component must have a named notice section: ' + component
    section = re.split(r'(?m)^#{1,3}\s|(?i:<h[1-3])', text[match.end() :], maxsplit=1)[0]
    for licence in ORACLE['components'][component]:
        assert licence.casefold() in section.casefold(), (
            'each component must carry its own correct licence and applicable exception: '
            + component
            + ' requires '
            + licence
        )
    assert 'copyright' in section.casefold(), (
        'each redistributed component notice must retain its attribution: ' + component
    )


def test_about_exposes_bundled_notices_and_named_copyright():
    about = (ROOT / 'app/qml/Pages/Home/AboutDialog.qml').read_text()
    info = '\n'.join(p.read_text() for p in (ROOT / 'app/src').glob('app_info.*'))
    cmake = (ROOT / 'app/CMakeLists.txt').read_text()
    assert 'qrc:/THIRD-PARTY-NOTICES' in about + info, (
        'the About window must resolve the bundled notices without a private repository link'
    )
    assert 'THIRD-PARTY-NOTICES' in cmake and 'qt_add_resources' in cmake, (
        'the app resource bundle must include the actual dependency notice file'
    )
    assert (
        all(
            name in about
            for name in (
                'about.licences',
                'ApplicationInfo.appLicenceIds',
                'about.thirdParty',
            )
        )
        and 'appLicenceUrls' in info
    ), 'The links expose complete own licences and component terms'
    assert all(token in info for token in ('BSD-3-Clause', 'GPL-3.0-only')) and re.search(
        r'QStringList appLicenceUrls\(\) const\s*\{\s*return \{licenseUrl\(\), copyingUrl\(\)\};',
        info,
    ), 'The two displayed licence identifiers resolve in order to complete BSD and GPL resources'
    assert 'about.licence.summary' not in about and 'This app is distributed under' not in about, (
        'The identifier links replace the superseded distribution summary'
    )
    assert re.search(
        r'QString appLicenseUrl\(\) const\s*\{\s*return QStringLiteral\('
        r'"qrc:/app/DISTRIBUTION-LICENSE\.md"\);\s*\}',
        info,
    ), 'The application distribution notice remains a bundled resource'
    assert '${PROJECT_SOURCE_DIR}/app/DISTRIBUTION-LICENSE.md' in cmake, (
        'The app resources must include the application distribution notice file'
    )
    assert '"app/DISTRIBUTION-LICENSE.md"' in info, (
        'The licence resource reader must admit the application distribution notice'
    )
    assert all(name in about for name in ('about.licencePopup', 'about.thirdPartyPopup')) and (
        'onClicked: ApplicationInfo.aboutOpenLicence()' in about
        and 'onClicked: thirdPartyPopup.open()' in about
    ), 'The identifier and third-party links open their actual local licence and component popups'
    opening = 'void ApplicationInfo::aboutOpenLicence() const {'
    assert info.count(opening) == 1, (
        'The About license delegate has one authoritative native owner'
    )
    delegate = info.split(opening, 1)[1].split('\n}', 1)[0]
    assert all(
        token in delegate
        for token in (
            'assistantContextField(f, "licenceEntry", "modelData")',
            'assistantContextField(f, "ApplicationInfo", "appLicenceUrls")',
            'assistantContextField(f, "licenceEntry", "index")',
            'panelUsageDeferredMemberCall(f, info, "licenceText"',
            'assistantMemberWrite(f, next, "licence", licence)',
            'projectInvoke(f, "licencePopup", "open")',
        )
    ), 'The native delegate resolves the clicked license index and opens its actual bundled text'
    notice = (ROOT / 'app/DISTRIBUTION-LICENSE.md').read_text()
    assert 'GPL-3.0' in notice and 'BSD 3-Clause' in notice, (
        'both the built application GPL status and source BSD status must be reachable from About'
    )
    assert '[COPYING](../COPYING)' in notice and '[LICENSE](../LICENSE)' in notice, (
        'the notice reached from About must identify both complete licence texts'
    )
    assert re.search(
        r'(?:Copyright|©).*?(?:contributors|Enhantica|EasyScience)', about + info, re.IGNORECASE
    ), 'the About copyright must identify its holder'
    assert not re.search(r'https://github.com/enhantica/c[r]ysta', about + info), (
        'the public About window cannot point users to the private engine repository'
    )


def test_python_distribution_includes_binding_licences():
    project = tomllib.loads((ROOT / 'pyproject.toml').read_text())['project']
    patterns = project.get('license-files', [])
    assert patterns, 'the Python source distribution must declare its binding licence files'
    selected = [p for pattern in patterns for p in ROOT.glob(pattern) if p.is_file()]
    for name in ('nanobind', 'robin'):
        assert any(name in p.as_posix().casefold() for p in selected), (
            'the binding redistribution must include the real dependency licence: ' + name
        )


def test_production_sources_carry_bsd_spdx():
    findings = []
    for name, text in publication_texts():
        if (
            name.startswith(('core/', 'lib/', 'app/src/', 'app/qml/'))
            and Path(name).suffix
            in {
                '.py',
                '.cpp',
                '.hpp',
                '.qml',
            }
            and 'SPDX-License-Identifier: BSD-3-Clause' not in text
        ):
            findings.append(name)
    assert not findings, (
        'all product source, including the app source, uses the agreed BSD SPDX identifier: '
        + ', '.join(findings[:20])
    )


def workflows():
    result = []
    from tests.integration.py.test_e09_t75_native_workflow import (  # noqa: PLC0415 - defer cross-module test wiring
        jobs,
        public_profile,
    )

    directory = (
        ROOT / '.github/workflows'
        if public_profile(jobs())
        else ROOT / 'tools/public-release/github/workflows'
    )
    for path in sorted(directory.glob('*.y*ml')):
        doc = yaml.load(path.read_text(), Loader=yaml.BaseLoader)
        if isinstance(doc, dict):
            result.append((path.name, doc))
    assert result, 'the public repository must declare its hosted verification workflows'
    return result


def nonfork(condition):
    # Before: every OR and non-status negation refused, including qualification
    # alternatives dominated by a trusted dispatch guard. After: every admitted
    # route must carry a positive trusted guard; an unguarded OR arm still refuses.
    condition = str(condition).strip().removeprefix('${{').removesuffix('}}').strip()
    condition = condition.replace('&&', ' and ').replace('||', ' or ')
    condition = re.sub(r'!(?!=)', ' not ', condition)
    condition = re.sub(r'\bfalse\b', 'False', condition)
    condition = re.sub(r'\btrue\b', 'True', condition)
    try:
        node = ast.parse(condition.strip(), mode='eval').body
    except SyntaxError:
        return False

    def guarded(node):
        if isinstance(node, ast.BoolOp):
            combine = any if isinstance(node.op, ast.And) else all
            return combine(guarded(child) for child in node.values)
        return ast.unparse(node) in {
            'github.event.pull_request.head.repo.fork == False',
            'github.event.pull_request.head.repo.full_name == github.repository',
            "github.event_name == 'push'",
            "github.event_name == 'workflow_dispatch'",
        }

    return guarded(node)


def runner_values(job):
    value = job.get('runs-on', '')
    if isinstance(value, list):
        return value
    if '${{' not in value:
        return [value]
    matrix = job.get('strategy', {}).get('matrix', {})
    key = re.search(r'matrix\.(\w+)', value)
    assert key, 'runner expressions must resolve to the declared platform matrix'
    values = matrix.get(key[1], [])
    values += [row[key[1]] for row in matrix.get('include', []) if key[1] in row]
    assert values, 'every runner matrix expression must have a finite declared expansion'
    flattened = [
        runner for value in values for runner in (value if isinstance(value, list) else [value])
    ]
    assert all(isinstance(runner, str) for runner in flattened), (
        'every declared runner label must be a string before checking fork reachability'
    )
    return flattened


def test_public_ci_uses_hosted_runners_and_guards_private_tokens():
    findings = public_token_findings(workflows())
    assert not findings, (
        'public CI must use hosted runners; private credentials need a non-fork guard and '
        'reviewed environment: ' + ', '.join(findings)
    )


def public_token_findings(documents):
    findings = []
    for filename, doc in documents:
        for name, job in doc.get('jobs', {}).items():
            if 'uses' in job:
                targets = dict(documents)
                target = targets.get('crysta-sdk.yml', {})
                called = target.get('on', {})
                if not (
                    job['uses'] == './.github/workflows/crysta-sdk.yml'
                    and isinstance(called, dict)
                    and 'workflow_call' in called
                ):
                    findings.append(filename + ':' + name + ':unreviewed reusable workflow')
                continue
            runners = runner_values(job)
            hosted = all(
                re.fullmatch(r'(?:ubuntu|macos|windows)-(?:latest|\d[\w.-]*)', r) for r in runners
            )
            dispatch = "github.event_name == 'workflow_dispatch'" in str(
                job.get('if', '')
            ) and nonfork(job.get('if', ''))
            if not hosted and not dispatch:
                findings.append(filename + ':' + name + ':fork-reachable private runner')
            for step in job.get('steps', []):
                serialized = json.dumps(step)
                private = 'create-github-app-token' in serialized or bool(
                    re.search(r'secrets\.(?!GITHUB_TOKEN\b)\w+', serialized)
                )
                disabled = job.get('if') is False or job.get('if') == 'false'
                if private and not (
                    disabled or nonfork(job.get('if', '')) or nonfork(step.get('if', ''))
                ):
                    findings.append(filename + ':' + name + ':unguarded private token')
                environment = job.get('environment')
                if isinstance(environment, dict):
                    environment = environment.get('name')
                public_jobs = {
                    'pages.yml': {'publish-docs', 'publish-wasm'},
                    'installers.yml': {'publish-installers'},
                    'release-publish.yml': {'publish-downloads'},
                }
                reviewed = (
                    environment == 'public-site'
                    if name in public_jobs.get(filename, set())
                    else bool(environment)
                )
                if private and not reviewed:
                    findings.append(filename + ':' + name + ':token outside reviewed environment')
    return findings


@pytest.mark.parametrize('defect', ['unguarded', 'negated', 'disjunction', 'environment', 'pages'])
def test_private_token_guards_still_refuse_forks_after_public_switch(defect):
    import copy  # noqa: PLC0415

    documents = workflows()
    assert not public_token_findings(documents), (
        'the hosted workflow must refuse fork credentials before every guard escape'
    )
    damaged = copy.deepcopy(documents)
    sdk = next(doc for name, doc in damaged if name == 'crysta-sdk.yml')
    job = sdk['jobs']['build']
    if defect == 'pages':
        pages = next(doc for name, doc in damaged if name == 'pages.yml')
        pages['jobs']['publish-docs']['if'] = 'true'
    elif defect == 'environment':
        job.pop('environment')
    else:
        job['if'] = {
            'unguarded': '${{ !inputs.core_only }}',
            'negated': '${{ !inputs.core_only && '
            'github.event.pull_request.head.repo.fork != false }}',
            'disjunction': '${{ !inputs.core_only || '
            'github.event.pull_request.head.repo.fork == false }}',
        }[defect]
    assert public_token_findings(damaged), (
        'core-only skips and Pages publication must never mask a fork token or environment escape'
    )


@pytest.mark.parametrize('event', ['pull_request', 'push', 'schedule', 'workflow_dispatch'])
def test_private_token_guard_is_required_in_every_job_even_off_pr(event):
    import copy  # noqa: PLC0415

    documents = workflows()
    assert not public_token_findings(documents), (
        'Every actual credential site starts with its reviewed environment and fork guard'
    )
    sites = [
        (filename, name, index)
        for filename, doc in documents
        for name, job in doc['jobs'].items()
        for index, step in enumerate(job.get('steps', []))
        if 'create-github-app-token' in str(step.get('uses', ''))
    ]
    assert sites, 'The credential control must reach the actual token-minting steps'
    for filename, name, index in sites:
        damaged = copy.deepcopy(documents)
        doc = next(doc for path, doc in damaged if path == filename)
        job = doc['jobs'][name]
        doc['on'] = {event: {}}
        job['steps'][index].pop('if', None)
        for condition in ('!cancelled()', "!cancelled() && github.event_name != 'pull_request'"):
            job['if'] = condition
            assert f'{filename}:{name}:unguarded private token' in public_token_findings(
                damaged
            ), (
                f'Every event rejects a token site stripped of its trusted guard: '
                f'{filename}/{name}/{event}/{condition}'
            )


def test_public_artifacts_exclude_engine_object_code_and_runner_names():
    assert not public_artifact_findings(workflows()), (
        'Public uploads expose reviewed evidence, exact qualified delivery products or same-run '
        'native transport, without runner identities or arbitrary binary directories'
    )


def required_artifact_programs(job):
    outcomes, programs = {}, []
    resolved = True
    for candidate in job.get('steps', []):
        try:
            enabled = active(candidate, 'pull_request', outputs=outcomes)
        except AssertionError:
            resolved = False
            enabled = False
        if enabled and not candidate.get('continue-on-error'):
            programs.append(candidate.get('run', ''))
        if 'id' in candidate:
            outcomes[candidate['id'], 'outcome'] = 'success' if enabled else 'skipped'
    return '\n'.join(programs), resolved


def public_artifact_findings(documents):
    from tests.fixtures.public_artifact_contract import reviewed_delivery  # noqa: PLC0415

    findings = []
    for filename, doc in documents:
        for name, job in doc.get('jobs', {}).items():
            required_programs = ''
            if name == 'app-wasm':
                required_programs, resolved = required_artifact_programs(job)
                if not resolved:
                    findings.append(filename + ':' + name + ':unresolved producer condition')
            for step in job.get('steps', []):
                if 'upload-artifact' not in step.get('uses', ''):
                    continue
                options = step.get('with', {})
                artifact, paths = options.get('name', ''), options.get('path', '')
                reviewed = reviewed_delivery(filename, name, job, step)
                if 'runner.name' in artifact or ('edi-native' in artifact and not reviewed):
                    findings.append(filename + ':' + name + ':private artifact identity')
                webapp = (
                    filename == 'ci.yml'
                    and name == 'app-wasm'
                    and (
                        (artifact == 'edi-webapp' and paths == 'build/wasm/site')
                        or (
                            artifact == 'edi-webapp-checks'
                            and paths == '${{ runner.temp }}/edi-webapp-checks'
                        )
                    )
                    and 'wasm-build' in required_programs
                    and 'wasm-check' in required_programs
                    and 'e04_t11_wasm_delivery.py' in required_programs
                )
                for path in paths.splitlines():
                    if path.startswith('!'):
                        continue
                    if path and not (
                        Path(path).suffix
                        in {'.json', '.log', '.txt', '.csv', '.tsv', '.png', '.svg'}
                        or path in {'build/app/ui-actual', 'build/app/ui-diff'}
                        or webapp
                        or reviewed
                    ):
                        findings.append(filename + ':' + name + ':opaque/binary artifact ' + path)
    return findings


@pytest.mark.parametrize(
    'defect',
    [
        'native-path',
        'native-name',
        'runner-name',
        'other-job',
        'no-build',
        'no-check',
        'disabled-check',
        'optional-check',
    ],
)
def test_webapp_artifact_allowance_refuses_native_object_escapes(defect):
    import copy  # noqa: PLC0415

    doc = yaml.safe_load((ROOT / '.github/workflows/ci.yml').read_text())
    assert not public_artifact_findings([('ci.yml', doc)]), (
        'the prescribed webapp and evidence uploads must pass before each native escape'
    )
    damaged = copy.deepcopy(doc)
    job = damaged['jobs']['app-wasm']
    upload = next(s for s in job['steps'] if s.get('with', {}).get('name') == 'edi-webapp')
    if defect == 'native-path':
        upload['with']['path'] = 'build/ci'
    elif defect == 'native-name':
        upload['with']['name'] = 'edi-native-linux-64'
    elif defect == 'runner-name':
        upload['with']['name'] = '${{ runner.name }}'
    elif defect == 'other-job':
        damaged['jobs']['native']['steps'].append(copy.deepcopy(upload))
    elif defect in {'disabled-check', 'optional-check'}:
        check = next(s for s in job['steps'] if 'wasm-check' in s.get('run', ''))
        check['if' if defect == 'disabled-check' else 'continue-on-error'] = (
            defect != 'disabled-check'
        )
    else:
        token = 'wasm-build' if defect == 'no-build' else 'wasm-check'
        job['steps'] = [s for s in job['steps'] if token not in s.get('run', '')]
    assert public_artifact_findings([('ci.yml', damaged)]), (
        'the webapp allowance must refuse native identity, objects and missing packaging checks'
    )


def pages_operation(steps, token, *, condition=None):
    matches = [
        (index, step)
        for index, step in enumerate(steps)
        if any(
            token in line
            for line in step.get('run', '').splitlines()
            if not line.lstrip().startswith('#')
        )
        or token in step.get('uses', '')
    ]
    assert len(matches) == 1, 'Pages requires one actual source publication operation: ' + token
    index, step = matches[0]
    enabled = active(step, 'push') if condition is None else step.get('if') == condition
    assert enabled and not step.get('continue-on-error'), (
        'Each publication operation executes in its declared leg and propagates actual failure'
    )
    return index, step


def publication_shell_operation(steps, script):
    index, step = pages_operation(steps, script)
    commands = [
        (line, shlex.split(command))
        for line, command in enumerate(step['run'].splitlines())
        if command.strip() and not command.lstrip().startswith('#')
    ]
    commands = [
        (line, command)
        for line, command in commands
        if len(command) >= 2
        and command[0] in {'bash', 'python', 'python3', 'gh'}
        and command[1] == script
    ]
    assert len(commands) == 1, (
        'Publication executes its actual helper, not a quoted or missing call'
    )
    line, command = commands[0]
    assert not any(any(symbol in token for symbol in ';|&<>') for token in command), (
        'Publication helper failures cannot be masked by shell control or redirection'
    )
    return (index, line), step, command


def publication_option(command, name):
    assert command.count(name) == 1 and command.index(name) + 1 < len(command), (
        'The actual site assembly declares each required input exactly once: ' + name
    )
    return command[command.index(name) + 1]


def public_site_boundary(publish, component, incoming, artifact_index):
    assert (
        publish['concurrency']['group'] == 'pages-publication'
        and str(publish['concurrency']['cancel-in-progress']).lower() == 'false'
    ), 'Independent public-site publication serializes without cancelling a counterpart update'
    steps = publish['steps']
    token_index, token = pages_operation(steps, 'actions/create-github-app-token@')
    assert (
        token['with']['owner'] == 'enhantica' and token['with']['repositories'] == 'edi-sites'
    ), 'The public-site publisher mints access only to the intended site repository'
    fetch_position, fetch, fetch_command = publication_shell_operation(
        steps, 'tools/ci/fetch_deploy_branch.sh'
    )
    assembly_position, _assembly, assembly_command = publication_shell_operation(
        steps, 'tools/ci/pages_update.py'
    )
    push_position, push, push_command = publication_shell_operation(
        steps, 'tools/ci/push_deploy_branch.sh'
    )
    assert len(fetch_command) == 4 and fetch_command[2] == 'deploy-docs', (
        'Counterpart content comes from the public documentation branch, never developer Pages'
    )
    assert (
        publication_option(assembly_command, '--component') == component
        and publication_option(assembly_command, '--incoming') == incoming
        and publication_option(assembly_command, '--repo') == '$GITHUB_REPOSITORY'
        and publication_option(assembly_command, '--base') == fetch_command[3]
    ), 'Actual assembly overlays the addressed component onto the fetched public counterpart'
    site = publication_option(assembly_command, '--site')
    assert len(push_command) == 4 and push_command[2:] == [site, 'deploy-docs'], (
        'Publication pushes exactly the assembled site to the intended public documentation branch'
    )
    assert (
        artifact_index < fetch_position[0]
        and token_index < fetch_position[0]
        and fetch_position < assembly_position < push_position
    ), (
        'Each publisher receives its component, fetches its counterpart, assembles '
        'and publishes in order'
    )
    expected_token = '${{ steps.' + token['id'] + '.outputs.token }}'
    assert all(
        step.get('env', {}).get('SITES_TOKEN') == expected_token for step in (fetch, push)
    ), 'Fetching and publishing use the same repository-narrowed public-site token'


def public_main_destinations(documents):
    for filename in ('pages.yml', 'installers.yml', 'release-publish.yml'):
        doc = documents[filename]
        assert doc.get('permissions', {}).get('pages') != 'write', (
            'Main public publication has no developer Pages deployment permission'
        )
        for job in doc['jobs'].values():
            environment = job.get('environment')
            if isinstance(environment, dict):
                environment = environment.get('name')
            assert environment != 'github-pages', (
                'Main public publishers never enter the developers GitHub Pages environment'
            )
            assert job.get('permissions', {}).get('pages') != 'write', (
                'No main publisher retains developer Pages deployment permission'
            )
            assert not any(
                any(
                    action in step.get('uses', '')
                    for action in (
                        'actions/deploy-pages@',
                        'actions/upload-pages-artifact@',
                    )
                )
                for step in job.get('steps', [])
            ), 'Main public workflows never upload or deploy the developers GitHub Pages site'


# Before: component publication required a composed Pages artifact and deploy-pages.
# After: the addressed artifact overlays its counterpart from edi-sites/deploy-docs,
# then the assembled site is pushed to that branch, without touching developer Pages.
def pages_component_boundary(doc, component, producer, artifact, incoming):
    build = doc['jobs'][producer]
    steps = build['steps']
    operations = (
        ('pages-check', 'notebooks-run', 'site-build --require-outputs')
        if component == 'docs'
        else ('wasm-toolchain', 'wasm-build')
    )
    positions = [pages_operation(steps, operation)[0] for operation in operations]
    upload_index, upload = pages_operation(steps, 'actions/upload-artifact@')
    assert positions == sorted(positions) and positions[-1] < upload_index, (
        'Actual docs or wasm inputs are checked and built before their artifact is uploaded'
    )
    assert upload['with']['name'] == artifact, (
        'Each public component uploads its exact addressed artifact'
    )
    assert upload['with']['path'] == ('site' if component == 'docs' else 'build/wasm/site'), (
        'The component upload contains the real source-built publication output'
    )
    publish = doc['jobs']['publish-' + component]
    assert publish['needs'] in (producer, [producer]), (
        'Each publication waits for its own completed build'
    )
    steps = publish['steps']
    download_index, download = pages_operation(steps, 'actions/download-artifact@')
    assert download['with']['name'] == artifact and download['with']['path'] == incoming, (
        'The publisher downloads the exact artifact produced by its own component builder'
    )
    assert download['with'].get(
        'run-id', '${{ github.run_id }}'
    ) == '${{ github.run_id }}' and not download['with'].get('pattern'), (
        'Component publication cannot substitute a foreign run or merged artifact selection'
    )
    public_site_boundary(publish, component, incoming, download_index)


def installers_publication_boundary(doc):
    publish = doc['jobs']['publish-installers']
    assert publish['needs'] in ('installers', ['installers']), (
        'Public installer publication waits for actual installer qualification'
    )
    steps = publish['steps']
    fresh = [
        (index, step)
        for index, step in enumerate(steps)
        if 'actions/download-artifact@' in step.get('uses', '')
        and step.get('with', {}).get('path') == 'components'
    ]
    assert len(fresh) == 1, 'The public installer publisher receives one addressed component set'
    artifact_index, download = fresh[0]
    assert download['with'] == {
        'pattern': 'installer-components-*-${{ github.run_attempt }}',
        'merge-multiple': 'true',
        'path': 'components',
    }, 'Fresh installer components belong to the current qualified attempt without foreign runs'
    assert download.get('if') == "inputs.preview_run == ''" and not download.get(
        'continue-on-error'
    ), 'Fresh installer artifacts are used only without a recovered preview run'
    recovery_index, recovery = pages_operation(
        steps, 'tools/release/preview.py', condition="inputs.preview_run != ''"
    )
    assert (
        "inputs.preview_run != ''" in recovery.get('if', '')
        and recovery.get('env', {}).get('PREVIEW_RUN') == '${{ inputs.preview_run }}'
        and '--run "$PREVIEW_RUN"' in recovery['run']
        and 'mv preview/components components' in recovery['run']
    ), 'Recovered qualified preview components feed the same public-site assembly'
    qualification = next(
        (
            index
            for index, step in enumerate(steps)
            if 'components/testing' in step.get('run', '') and 'Updates.xml' in step.get('run', '')
        ),
        None,
    )
    assert (
        qualification is not None
        and artifact_index < qualification
        and steps[qualification].get('if') == "inputs.preview_run == ''"
        and not steps[qualification].get('continue-on-error')
    ), 'Fresh installer components retain their selected-platform metadata qualification'
    public_site_boundary(publish, 'installers', 'components', max(recovery_index, qualification))


def released_publication_boundary(doc):
    publish = doc['jobs']['publish']
    steps = publish['steps']
    finalize_index, finalize = pages_operation(steps, '--finalize')
    assert 'tools/release/publish_assets.py' in finalize['run'], (
        'The published tag follows actual verified release finalization'
    )
    push_position, _push, command = publication_shell_operation(
        steps, 'tools/ci/push_deploy_branch.sh'
    )
    assert command[2:] == ['released-webapp/webapp', 'deploy-app'], (
        'The released web app reaches the released-app public branch, separate from main previews'
    )
    assert finalize_index < push_position[0], (
        'The released app is published only after the verified release assets are finalized'
    )
    downloads = doc['jobs']['publish-downloads']
    assert downloads['needs'] in ('publish', ['publish']), (
        'Download repositories are requested only after successful release publication'
    )
    _, token = pages_operation(downloads['steps'], 'actions/create-github-app-token@')
    assert (
        token['with']['owner'] == 'enhantica' and token['with']['repositories'] == 'edi-download'
    ), 'The download dispatch token is narrowed to the actual download repository'
    token_index = downloads['steps'].index(token)
    dispatch_position, dispatch, command = publication_shell_operation(
        downloads['steps'], 'workflow'
    )
    assert (
        command[:4] == ['gh', 'workflow', 'run', 'publish.yml']
        and publication_option(command, '--repo') == 'enhantica/edi-download'
        and publication_option(command, '--ref') == 'main'
        and publication_option(command, '-f') == 'tag=$TAG'
    ), 'Every release dispatches its addressed tag to the intended download publishing workflow'
    assert (
        token_index < dispatch_position[0]
        and dispatch.get('env', {}).get('GH_TOKEN')
        == '${{ steps.' + token['id'] + '.outputs.token }}'
        and dispatch.get('env', {}).get('TAG') == '${{ needs.publish.outputs.tag }}'
    ), 'The download dispatch consumes its own narrow token and the completed release tag'
    published_tag_boundary(publish, finalize_index)


def published_tag_boundary(publish, finalize_index):
    steps = publish['steps']
    output = publish.get('outputs', {}).get('tag', '')
    match = re.fullmatch(r'\$\{\{ steps\.([\w-]+)\.outputs\.tag \}\}', output)
    assert match, 'The download request is bound to an actual release-job tag output'
    tags = [(index, step) for index, step in enumerate(steps) if step.get('id') == match[1]]
    assert len(tags) == 1 and finalize_index < tags[0][0], (
        'The published tag is exported only after the real release has finalized'
    )
    tag = tags[0][1]
    assert (
        active(tag, 'workflow_dispatch')
        and not tag.get('continue-on-error')
        and 'publication/release.json' in tag.get('run', '')
        and 'tag=v$(' in tag['run']
        and '$GITHUB_OUTPUT' in tag['run']
    ), 'The actual output tag comes from the finalized immutable release metadata'


def test_pages_builds_docs_and_publishes_the_linked_webapp():
    documents = dict(workflows())
    assert 'pages.yml' in documents, 'The public site has its declared Pages publication workflow'
    doc = documents['pages.yml']
    pages_component_boundary(doc, 'docs', 'docs', 'pages-docs', 'documentation')
    pages_component_boundary(doc, 'wasm', 'wasm', 'pages-webapp', 'webapp')
    public_main_destinations(documents)
    installers_publication_boundary(documents['installers.yml'])
    released_publication_boundary(documents['release-publish.yml'])
    config = yaml.load((ROOT / 'mkdocs.yml').read_text(), Loader=yaml.BaseLoader)
    address = 'https://app.easydiffraction.org/'
    assert address in json.dumps(config.get('nav', [])), (
        'Docs navigation links the publicly released web app'
    )
    assert all(
        address in (ROOT / path).read_text() for path in ('docs/index.md', 'docs/user/index.md')
    ), 'Both landing pages link the actual published application domain'
    assert 'noindex' not in json.dumps(doc) and 'Disallow: /webapp/' not in json.dumps(doc), (
        'Published documentation and the web app remain visible to indexing'
    )
    assert 'site_url' in config, 'The public documentation declares its canonical published URL'


def selected_pages_ref(expression, *, prerelease, preview_ref):
    """Resolve the bounded Actions selector without assuming which ref it selects."""
    value = expression.strip().removeprefix('${{').removesuffix('}}').strip()
    for atom, replacement in {
        'github.event.release.prerelease': prerelease,
        'vars.EDI_PREVIEW_PAGES_REF': preview_ref,
        'github.event.repository.default_branch': 'main',
    }.items():
        value = value.replace(atom, repr(replacement))
    tree = ast.parse(value.replace('&&', ' and ').replace('||', ' or '), mode='eval')
    assert all(
        isinstance(node, (ast.Expression, ast.BoolOp, ast.And, ast.Or, ast.Constant))
        for node in ast.walk(tree)
    ), 'The release refresh ref must resolve from its declared release and repository inputs'
    return eval(compile(tree, '<pages-ref>', 'eval'), {'__builtins__': {}})  # noqa: S307


def dispatched_pages_ref(doc, route, tmp_path):
    triggers = doc.get('on', doc.get(True, {}))
    jobs = doc['jobs']
    assert 'workflow_dispatch' in triggers, (
        'Release-note refreshes can dispatch the actual Pages workflow'
    )
    refresh = jobs['refresh-release-notes']
    prerelease = route != 'stable-notes'
    assert active(refresh, 'release', 'refs/tags/v2026.11.22', prerelease=prerelease), (
        'Both stable releases and prereleases reach the release-note dispatch job'
    )
    preview_ref = 'dev' if route == 'preview-ref' else 'main'
    selected = selected_pages_ref(
        refresh['env']['PAGES_REF'], prerelease=prerelease, preview_ref=preview_ref
    )
    assert selected == 'main', (
        'Stable and prerelease notes rebuild public main even with a configured preview ref'
    )
    _position, step = pages_operation(refresh['steps'], 'gh workflow run pages.yml')
    assert active(step, 'release', prerelease=prerelease), (
        'The release-note dispatch step executes on the actual release event'
    )
    executable = tmp_path / 'gh'
    executable.write_text('#!/bin/sh\nprintf "%s\\n" "$@" >> "$CAPTURE"\n')
    executable.chmod(0o755)
    capture = tmp_path / 'dispatch-arguments'
    result = run(
        'bash',
        '-e',
        '-c',
        step['run'],
        env={
            **os.environ,
            'PATH': str(tmp_path) + os.pathsep + os.environ['PATH'],
            'CAPTURE': str(capture),
            'GITHUB_REPOSITORY': 'enhantica/edi',
            'PAGES_REF': selected,
        },
    )
    require_success(result, 'the actual release-note shell dispatch must complete')
    assert capture.is_file(), 'Release-note refresh executes the workflow dispatch command'
    arguments = capture.read_text().splitlines()
    assert arguments[:3] == ['workflow', 'run', 'pages.yml'], (
        'Release-note refresh invokes the actual Pages workflow'
    )
    assert (
        publication_option(arguments, '--repo') == 'enhantica/edi'
        and publication_option(arguments, '--ref') == selected
        and publication_option(arguments, '-f') == 'component=docs'
    ), 'The actual dispatch preserves its configured ref and selects documentation only'
    return selected


def pages_route_boundary(doc, route, tmp_path):
    # The reviewed public-site policy admits main branches and v* tags. These are
    # independent event inputs, not a claim to observe GitHub's live settings.
    triggers = doc.get('on', doc.get(True, {}))
    assert 'published' in triggers.get('release', {}).get('types', []), (
        'Published releases retain the tag build and release-note refresh routes'
    )
    jobs = doc['jobs']
    if route == 'stable-tag':
        event, ref, component = 'release', 'refs/tags/v2026.11.22', 'wasm'
        assert active(jobs['crysta-sdk'], event, ref, prerelease=False), (
            'A stable release tag reaches its pinned SDK before building its own web app'
        )
    else:
        selected = dispatched_pages_ref(doc, route, tmp_path)
        event, component = 'workflow_dispatch', 'docs'
        ref = ('refs/tags/' if selected.startswith('v') else 'refs/heads/') + selected

    build, publish = jobs[component], jobs['publish-' + component]
    assert build.get('needs') in ('crysta-sdk', ['crysta-sdk']) and active(
        jobs['crysta-sdk'], event, ref
    ), 'Each real publication route reaches and waits for its pinned SDK producer'
    assert active(build, event, ref, states={'crysta-sdk': 'success'}, component=component), (
        'The real stable-tag or configured-preview event reaches its component producer'
    )
    assert publish['needs'] in (component, [component]) and active(
        publish, event, ref, states={component: 'success'}, component=component
    ), 'The real publication route waits for and reaches its own successful component artifact'
    environment = publish.get('environment')
    if isinstance(environment, dict):
        environment = environment.get('name')
    assert environment == 'public-site', (
        'Stable-tag and configured-preview routes reach the reviewed public-site environment'
    )
    outcomes = {}
    for step in [*build['steps'], *publish['steps']]:
        assert active(step, event, ref, outputs=outcomes, component=component) and not step.get(
            'continue-on-error'
        ), 'Build, artifact, token, assembly and push steps execute on the actual publication ref'
        if 'id' in step:
            outcomes[step['id'], 'outcome'] = 'success'
    pages_component_boundary(
        doc,
        component,
        component,
        'pages-webapp' if component == 'wasm' else 'pages-docs',
        'webapp' if component == 'wasm' else 'documentation',
    )


@pytest.mark.parametrize('route', ['stable-tag', 'stable-notes', 'preview-main', 'preview-ref'])
def test_public_site_publication_routes_reach_reviewed_environment(route, tmp_path):
    pages_route_boundary(dict(workflows())['pages.yml'], route, tmp_path)


@pytest.mark.parametrize('component', ['docs', 'wasm'])
@pytest.mark.parametrize('ref', ['refs/heads/dev', 'refs/tags/v2026.11.21'])
def test_public_site_preview_dispatch_builds_without_publication(component, ref):
    jobs = dict(workflows())['pages.yml']['jobs']
    assert active(
        jobs[component],
        'workflow_dispatch',
        ref,
        states={'crysta-sdk': 'success'},
        component=component,
    ), 'A non-main preview dispatch keeps its component build available for checking'
    assert not active(
        jobs['publish-' + component],
        'workflow_dispatch',
        ref,
        states={component: 'success'},
        component=component,
    ), 'Preview branches and dispatched tags cannot mint or push a public-site credential'


@pytest.mark.parametrize(
    ('route', 'defect'),
    [
        ('stable-tag', 'missing-release-trigger'),
        ('stable-tag', 'sdk-main-only'),
        ('stable-tag', 'build-main-only'),
        ('stable-tag', 'build-step-main-only'),
        ('stable-tag', 'missing-sdk-dependency'),
        ('stable-tag', 'publish-main-only'),
        ('stable-tag', 'step-main-only'),
        ('stable-tag', 'wrong-environment'),
        ('preview-ref', 'missing-dispatch-trigger'),
        ('preview-ref', 'disabled-refresh'),
        ('preview-ref', 'publish-preview-ref'),
        ('preview-ref', 'wrong-dispatch-ref'),
        ('preview-ref', 'wrong-component'),
        ('preview-ref', 'publish-preview-only'),
        ('preview-ref', 'wrong-environment'),
    ],
)
def test_public_site_publication_routes_reject_ref_bypasses(route, defect, tmp_path):
    import copy  # noqa: PLC0415

    document = dict(workflows())['pages.yml']
    pages_route_boundary(document, route, tmp_path)
    # Each mutation replays independently, so a prior captured dispatch cannot
    # make a removed or disabled command appear to have executed.
    for path in tmp_path.iterdir():
        path.unlink()
    damaged = copy.deepcopy(document)
    jobs = damaged['jobs']
    component = 'wasm' if route == 'stable-tag' else 'docs'
    main_only = "github.ref == 'refs/heads/main'"
    triggers = damaged.get('on', damaged.get(True, {}))
    if defect == 'missing-release-trigger':
        triggers.pop('release')
    elif defect == 'missing-dispatch-trigger':
        triggers.pop('workflow_dispatch')
    elif defect in {'sdk-main-only', 'build-main-only'}:
        jobs['crysta-sdk' if defect == 'sdk-main-only' else component]['if'] = main_only
    elif defect == 'build-step-main-only':
        _index, step = pages_operation(jobs[component]['steps'], 'wasm-build')
        step['if'] = main_only
    elif defect == 'missing-sdk-dependency':
        jobs[component].pop('needs')
    elif defect in {'publish-main-only', 'publish-preview-only'}:
        jobs['publish-' + component]['if'] = (
            main_only if defect == 'publish-main-only' else "github.ref == 'refs/heads/dev'"
        )
    elif defect == 'step-main-only':
        jobs['publish-' + component]['steps'][-1]['if'] = main_only
    elif defect == 'wrong-environment':
        jobs['publish-' + component]['environment'] = 'github-pages'
    elif defect == 'disabled-refresh':
        jobs['refresh-release-notes']['if'] = 'false'
    elif defect == 'publish-preview-ref':
        jobs['refresh-release-notes']['env']['PAGES_REF'] = '${{ vars.EDI_PREVIEW_PAGES_REF }}'
    else:
        _index, step = pages_operation(
            jobs['refresh-release-notes']['steps'], 'gh workflow run pages.yml'
        )
        step['run'] = step['run'].replace(
            '"$PAGES_REF"' if defect == 'wrong-dispatch-ref' else 'component=docs',
            'dev' if defect == 'wrong-dispatch-ref' else 'component=wasm',
        )
    with pytest.raises(AssertionError):
        pages_route_boundary(damaged, route, tmp_path)


def damage_component_artifact(steps, defect):
    _index, download = pages_operation(steps, 'actions/download-artifact@')
    if defect == 'foreign-artifact':
        download['with']['name'] = 'unrelated-component'
    elif defect == 'foreign-run':
        download['with']['run-id'] = '${{ inputs.another_run }}'
    else:
        download['with']['pattern'] = 'pages-*'
        download['with']['merge-multiple'] = 'true'


def damage_branch_publication(steps, defect):
    index, push = pages_operation(steps, 'tools/ci/push_deploy_branch.sh')
    if defect == 'publish-first':
        steps.insert(0, steps.pop(index))
    elif defect == 'optional-publish':
        push['continue-on-error'] = 'true'
    else:
        push['run'] = push['run'].replace('deploy-docs', 'deploy-app')


@pytest.mark.parametrize('component', ['docs', 'wasm'])
@pytest.mark.parametrize(
    'defect',
    [
        'missing-build',
        'disabled-placement',
        'publish-first',
        'foreign-artifact',
        'foreign-run',
        'merged-artifact',
        'wrong-source-branch',
        'wrong-base',
        'wrong-target-branch',
        'placement-before-fetch',
        'optional-publish',
        'developer-pages',
    ],
)
def test_pages_publication_rejects_missing_or_bypassed_real_app(defect, component, monkeypatch):
    import copy  # noqa: PLC0415

    test_pages_builds_docs_and_publishes_the_linked_webapp()
    damaged = copy.deepcopy(workflows())
    pages = dict(damaged)['pages.yml']
    steps = pages['jobs']['publish-' + component]['steps']
    if defect == 'missing-build':
        build_steps = pages['jobs'][component]['steps']
        token = 'wasm-build' if component == 'wasm' else 'site-build --require-outputs'
        build_steps[:] = [step for step in build_steps if token not in step.get('run', '')]
    elif defect in {'foreign-artifact', 'foreign-run', 'merged-artifact'}:
        damage_component_artifact(steps, defect)
    elif defect == 'developer-pages':
        steps.append({'uses': 'actions/deploy-pages@v4'})
    elif defect in {'publish-first', 'optional-publish', 'wrong-target-branch'}:
        damage_branch_publication(steps, defect)
    else:
        _index, assembly = pages_operation(steps, 'tools/ci/pages_update.py')
        if defect == 'disabled-placement':
            assembly['if'] = 'false'
        elif defect == 'wrong-source-branch':
            assembly['run'] = assembly['run'].replace(
                'fetch_deploy_branch.sh deploy-docs', 'fetch_deploy_branch.sh deploy-app'
            )
        elif defect == 'wrong-base':
            assembly['run'] = assembly['run'].replace(
                '--base "$RUNNER_TEMP/deployed"', '--base "$RUNNER_TEMP/unrelated"'
            )
        else:
            assembly['run'] = '\n'.join(reversed(assembly['run'].splitlines()))
    monkeypatch.setattr(sys.modules[__name__], 'workflows', lambda: damaged)
    with pytest.raises(AssertionError):
        test_pages_builds_docs_and_publishes_the_linked_webapp()


@pytest.mark.parametrize(
    ('workflow', 'job'),
    [
        ('pages.yml', 'publish-docs'),
        ('pages.yml', 'publish-wasm'),
        ('installers.yml', 'publish-installers'),
        ('release-publish.yml', 'publish-downloads'),
    ],
)
@pytest.mark.parametrize('defect', ['missing', 'other'])
def test_public_site_tokens_require_the_reviewed_environment(workflow, job, defect):
    import copy  # noqa: PLC0415

    documents = workflows()
    assert not public_token_findings(documents), (
        'Every actual public publisher starts inside its reviewed credential boundary'
    )
    damaged = copy.deepcopy(documents)
    target = dict(damaged)[workflow]['jobs'][job]
    if defect == 'missing':
        target.pop('environment')
    else:
        target['environment'] = 'github-pages'
    assert f'{workflow}:{job}:token outside reviewed environment' in public_token_findings(
        damaged
    ), 'A missing or substituted environment cannot mint the public destination credential'


@pytest.mark.parametrize(
    'defect',
    [
        'missing-components',
        'foreign-run',
        'missing-recovery',
        'wrong-base',
        'wrong-target-branch',
        'developer-pages',
    ],
)
def test_public_installer_destination_rejects_bypasses(defect, monkeypatch):
    import copy  # noqa: PLC0415

    test_pages_builds_docs_and_publishes_the_linked_webapp()
    damaged = copy.deepcopy(workflows())
    steps = dict(damaged)['installers.yml']['jobs']['publish-installers']['steps']
    if defect in {'missing-components', 'foreign-run'}:
        index = next(
            index
            for index, step in enumerate(steps)
            if step.get('with', {}).get('path') == 'components'
        )
        if defect == 'missing-components':
            steps.pop(index)
        else:
            steps[index]['with']['run-id'] = '${{ inputs.another_run }}'
    elif defect == 'missing-recovery':
        index, _step = pages_operation(
            steps, 'tools/release/preview.py', condition="inputs.preview_run != ''"
        )
        steps.pop(index)
    elif defect == 'developer-pages':
        steps.append({'uses': 'actions/deploy-pages@v4'})
    else:
        script = (
            'tools/ci/push_deploy_branch.sh'
            if defect == 'wrong-target-branch'
            else 'tools/ci/pages_update.py'
        )
        _index, step = pages_operation(steps, script)
        step['run'] = (
            step['run'].replace('deploy-docs', 'deploy-app')
            if defect == 'wrong-target-branch'
            else step['run'].replace(
                '--base "$RUNNER_TEMP/deployed"', '--base "$RUNNER_TEMP/unrelated"'
            )
        )
    monkeypatch.setattr(sys.modules[__name__], 'workflows', lambda: damaged)
    with pytest.raises(AssertionError):
        test_pages_builds_docs_and_publishes_the_linked_webapp()


@pytest.mark.parametrize(
    'defect',
    [
        'no-dependency',
        'wrong-token-repository',
        'wrong-dispatch-repository',
        'wrong-tag',
        'disabled-dispatch',
        'dispatch-first',
        'wrong-app-branch',
        'developer-pages',
    ],
)
def test_released_public_destinations_reject_bypasses(defect, monkeypatch):
    import copy  # noqa: PLC0415

    test_pages_builds_docs_and_publishes_the_linked_webapp()
    damaged = copy.deepcopy(workflows())
    release = dict(damaged)['release-publish.yml']
    downloads = release['jobs']['publish-downloads']
    steps = downloads['steps']
    if defect == 'no-dependency':
        downloads['needs'] = 'unrelated-job'
    elif defect == 'wrong-token-repository':
        _index, token = pages_operation(steps, 'actions/create-github-app-token@')
        token['with']['repositories'] = 'edi-sites'
    elif defect in {
        'wrong-dispatch-repository',
        'wrong-tag',
        'disabled-dispatch',
        'dispatch-first',
    }:
        index, dispatch = pages_operation(steps, 'gh workflow run')
        if defect == 'wrong-dispatch-repository':
            dispatch['run'] = dispatch['run'].replace(
                'enhantica/edi-download', 'enhantica/edi-sites'
            )
        elif defect == 'wrong-tag':
            dispatch['env']['TAG'] = 'v-unrelated-release'
        elif defect == 'disabled-dispatch':
            dispatch['if'] = 'false'
        else:
            steps.insert(0, steps.pop(index))
    elif defect == 'wrong-app-branch':
        _index, push = pages_operation(
            release['jobs']['publish']['steps'], 'tools/ci/push_deploy_branch.sh'
        )
        push['run'] = push['run'].replace('deploy-app', 'deploy-docs')
    else:
        steps.append({'uses': 'actions/deploy-pages@v4'})
    monkeypatch.setattr(sys.modules[__name__], 'workflows', lambda: damaged)
    with pytest.raises(AssertionError):
        test_pages_builds_docs_and_publishes_the_linked_webapp()


def script(name):
    path = SCRIPTS / name
    assert path.is_file(), 'the local public preparation must provide its reviewed script: ' + name
    return path


def test_scrub_is_repeatable_and_preserves_sdk_use(tmp_path):
    target = tmp_path / 'input'
    target.mkdir()
    bad_home = chr(47) + 'home/alice/work'
    bad_reference = 'crysta' + chr(32) + 'ADR-0001'
    (target / 'README.md').write_text(
        f'Private notes: {bad_home}\n{bad_reference}\nre' + chr(108) + 'ay ' + chr(69) + '04-T7\n'
    )
    (target / 'model.cpp').write_text(
        f'// {bad_reference}\n#include <crysta/model.hpp>\ncrysta::Project p;\n'
    )
    scrubber = script('scrub.py')
    require_success(
        run(sys.executable, str(scrubber), '--tree', str(target)),
        'the scrub must operate on a disposable local tree',
    )
    first = {
        p.relative_to(target).as_posix(): p.read_bytes() for p in target.rglob('*') if p.is_file()
    }
    assert (target / 'README.md').is_file() and (target / 'model.cpp').is_file(), (
        'the scrub must preserve source and user documents rather than remove whole files'
    )
    assert not any(
        PRIVATE.search(raw.decode()) or PROCESS.search(raw.decode()) for raw in first.values()
    ), 'the scrub must clear both personal and private/process references'
    assert (
        '#include <crysta/model.hpp>' in (target / 'model.cpp').read_text()
        and 'crysta::Project p;' in (target / 'model.cpp').read_text()
    ), 'scrubbing citations must preserve the supported SDK include and symbol use'
    require_success(
        run(sys.executable, str(scrubber), '--tree', str(target)), 'a second scrub must succeed'
    )
    second = {
        p.relative_to(target).as_posix(): p.read_bytes() for p in target.rglob('*') if p.is_file()
    }
    assert first == second, 'scrubbing an already prepared tree must be byte-idempotent'


def git_commit(repo, message):
    require_success(
        run('git', 'add', '.', cwd=repo), 'the synthetic source must stage its local content'
    )
    require_success(
        run(
            'git',
            '-c',
            'user.name=Snapshot fixture',
            '-c',
            'user.email=fixture@example.invalid',
            'commit',
            '-qm',
            message,
            cwd=repo,
        ),
        'the synthetic source must commit its local content',
    )


def test_cutover_resnapshots_newer_main_without_mutating_source(tmp_path):
    source = tmp_path / 'upstream'
    source.mkdir()
    require_success(
        run('git', 'init', '-q', '-b', 'main', cwd=source),
        'the rehearsal source must be a local main repository',
    )
    (source / 'README.md').write_text('Older user text\n' + chr(47) + 'home/alice/work' + '\n')
    git_commit(source, 'Original source')
    snapshotter = script('snapshot.py')
    old = tmp_path / 'old-public'
    require_success(
        run(sys.executable, str(snapshotter), '--source', str(source), '--output', str(old)),
        'the snapshot rehearsal must prepare the older local main',
    )
    (source / 'README.md').write_text('Newer user text\n' + chr(47) + 'home/alice/work' + '\n')
    git_commit(source, 'Newer source')
    head = run('git', 'rev-parse', 'HEAD', cwd=source).stdout
    output = tmp_path / 'new-public'
    require_success(
        run(sys.executable, str(snapshotter), '--source', str(source), '--output', str(output)),
        'the cutover rehearsal must prepare the newer local main',
    )
    assert 'Newer user text' in (output / 'README.md').read_text(), (
        're-snapshotting must include upstream changes made after preparation'
    )
    assert 'Older user text' not in (output / 'README.md').read_text(), (
        'the second snapshot must not reuse stale upstream bytes'
    )
    assert not PRIVATE.search((output / 'README.md').read_text()), (
        'the newer snapshot must reapply the content scrub'
    )
    assert run('git', 'rev-list', '--count', 'HEAD', cwd=output).stdout.strip() == '1', (
        'the prepared snapshot must have one fresh commit'
    )
    assert not run('git', 'status', '--porcelain', cwd=output).stdout.strip(), (
        'the prepared snapshot must commit every preparation change'
    )
    assert (
        run('git', 'rev-parse', 'HEAD', cwd=source).stdout == head
        and not run('git', 'status', '--porcelain', cwd=source).stdout.strip()
    ), 'the local rehearsal must leave source history and content untouched'
    assert not run('git', 'remote', '-v', cwd=output).stdout.strip(), (
        'the fixture snapshot must remain local with no publishing remote'
    )


def test_cutover_checklist_covers_settings_and_owner_boundary():
    path = ROOT / 'docs/dev/public-release-checklist.md'
    assert path.is_file(), 'the public cutover must have a reviewed operational checklist'
    text = path.read_text().casefold()
    for requirement in (
        'secret',
        'variable',
        'ruleset',
        'label',
        'pages',
        're-anchor',
        'delta',
        'rename',
        'visibility',
    ):
        assert requirement in text, (
            'the cutover checklist must cover this operation: ' + requirement
        )
    assert 'owner' in text and ('personally' in text or 'only' in text), (
        'rename and visibility steps must explicitly belong to the owner'
    )
    for path in SCRIPTS.rglob('*'):
        if path.is_file() and path.suffix in {'.py', '.sh'}:
            text = path.read_text()
            assert not re.search(
                r'gh\s+repo\s+(?:rename|edit)|--visibility|"(?:PATCH|POST)"\s*,?\s*["\x27]/repos',
                text,
            ), 'local preparation scripts cannot rename or publish remote repositories'


@pytest.fixture(scope='module')
def one_commit_tree(tmp_path_factory):
    destination = tmp_path_factory.mktemp('single-history')
    paths = [
        'tests/system/py/test_c34_t28_frozen_api.py',
        'tests/system/py/test_c34_t28_native_surface.py',
        'tests/fixtures/c14_t4_neutron/freeze_page_pins.py',
        'tests/fixtures/c13_t12_ids/baseline.json',
        'tests/fixtures/e04_t12_public_release/history',
        'tests/fixtures/c34_t28_baseline/api_witness_adaptation.py',
        'tests/fixtures/c34_t28_baseline/api_witness_adaptation.json',
    ]
    listing = run('git', 'ls-files', 'tests')
    require_success(listing, 'the history fixture must enumerate retained API witnesses')
    paths += [p for p in listing.stdout.splitlines() if 'c34_t26' in p or 'c34_t27' in p]
    archive = subprocess.run(
        ['git', 'archive', 'HEAD', *paths], cwd=ROOT, capture_output=True, check=False
    )
    assert archive.returncode == 0, (
        'fresh-history verification needs a complete committed source snapshot'
    )
    with tarfile.open(fileobj=io.BytesIO(archive.stdout)) as stream:
        stream.extractall(destination, filter='data')
    require_success(
        run('git', 'init', '-q', '-b', 'main', cwd=destination),
        'the source snapshot must initialize one local history',
    )
    git_commit(destination, 'Fresh source snapshot')
    require_success(
        run('git', 'update-ref', 'refs/remotes/origin/main', 'HEAD', cwd=destination),
        'the local fixture must expose the same single commit as main',
    )
    return destination


def test_frozen_api_gate_survives_one_commit_history(one_commit_tree):
    path = one_commit_tree / 'tests/system/py/test_c34_t28_frozen_api.py'
    module = runpy.run_path(str(path))
    # Exercise the real pre-existing freeze gate, including its loss/edit controls;
    # this is not a parallel weaker reconstruction of its property.
    try:
        blobs = module['frozen_blobs']()
        module['require_frozen'](one_commit_tree, blobs)
    except (AssertionError, subprocess.CalledProcessError) as error:
        pytest.fail(
            'the immutable API witness gate must keep its property on fresh history: ' + str(error)
        )


def test_live_edi_history_anchors_resolve_in_one_commit_tree(one_commit_tree):
    findings = []
    # Only live edi consumers, not archived provenance or foreign SDK references.
    paths = (
        'tests/system/py/test_c34_t28_native_surface.py',
        'tests/fixtures/c14_t4_neutron/freeze_page_pins.py',
    )
    for relative in paths:
        tree = ast.parse((one_commit_tree / relative).read_text())
        for statement in tree.body:
            if (
                isinstance(statement, ast.Assign)
                and any(
                    isinstance(t, ast.Name) and t.id in {'ANCHOR', 'BASE'}
                    for t in statement.targets
                )
                and isinstance(statement.value, ast.Constant)
                and isinstance(statement.value.value, str)
            ):
                anchor = statement.value.value
                if (
                    re.fullmatch(r'[0-9a-f]{7,40}', anchor)
                    and run(
                        'git', 'cat-file', '-e', anchor + '^{commit}', cwd=one_commit_tree
                    ).returncode
                ):
                    findings.append(relative)
    baseline = json.loads(
        (one_commit_tree / 'tests/fixtures/c13_t12_ids/baseline.json').read_text()
    )
    anchor = baseline.get('history_anchor')
    if (
        anchor
        and run('git', 'cat-file', '-e', str(anchor) + '^{commit}', cwd=one_commit_tree).returncode
    ):
        findings.append('frozen project population anchor')
    assert not findings, (
        'live history consumers must use retained content rather than missing old commits: '
        + ', '.join(findings)
    )


def test_secret_scanner_rejects_a_credential_control(tmp_path):
    scanner = script('scan.py')
    safe = tmp_path / 'safe'
    safe.mkdir()
    (safe / 'README.md').write_text('Public project documentation\n')
    require_success(
        run(sys.executable, str(scanner), '--tree', str(safe)),
        'the release scanner must admit a public local tree',
    )
    # Synthetic, unusable token; assembled so the gate never leaks a real credential.
    (safe / '.env').write_text('GITHUB_TOKEN=' + 'gh' + 'p_' + 'A' * 36 + '\n')
    result = run(sys.executable, str(scanner), '--tree', str(safe))
    assert result.returncode != 0, 'the release secrets scanner must reject the planted token'
    assert 'secret' in (result.stdout + result.stderr).casefold(), (
        'the credential control must fail for a named secret finding, not a missing scanner'
    )


@pytest.mark.parametrize(
    ('condition', 'expected'),
    [
        ('github.event.pull_request.head.repo.fork == false', True),
        ('!cancelled() && github.event.pull_request.head.repo.fork == false', True),
        ('!cancelled() && github.event.pull_request.head.repo.fork != false', False),
        ('!cancelled() || github.event.pull_request.head.repo.fork == false', False),
        ('!cancelled() && !(github.event.pull_request.head.repo.fork == false)', False),
        ("github.event_name == 'workflow_dispatch'", True),
        ('github.event.pull_request.head.repo.fork == false || always()', False),
        ("contains('github.event_name == \"push\"', 'push')", False),
        ('!(github.event.pull_request.head.repo.fork == false)', False),
        ('github.event.pull_request.head.repo.fork != false', False),
    ],
)
def test_fork_guard_cannot_admit_or_negate_the_attacker(condition, expected):
    assert nonfork(condition) is expected, (
        'the private-token policy must accept only a positive complete non-fork conjunct'
    )


def test_independent_private_pattern_controls():
    slash = chr(47)
    for forbidden in (
        slash + 'home/alice/project',
        slash + 'Users/alice/project',
        '~' + slash + 'runs/proof.log',
        slash + 'home/alice/runs/proof.log',
        'crysta' + chr(32) + 'ADR-0099',
        'enhantica' + slash + 'crysta' + slash + 'blob/main/model.cpp',
        'enhantica' + slash + 'crysta' + slash + 'tree/main/core',
    ):
        assert PRIVATE.search(forbidden), (
            'each personal-path and private-citation branch must reach its deliberate control'
        )
    for forbidden in (
        chr(67) + '11-T48',
        chr(69) + '04-T12',
        chr(73) + '-0163',
        'OR' + 'G-0033',
        're' + 'lay',
    ):
        assert PROCESS.search(forbidden), (
            'each forbidden process-reference family must reach its deliberate control'
        )
    assert not PRIVATE.search('#include <crysta/model.hpp>\ncrysta::Project p;'), (
        'the public content scanner must retain permitted SDK include and symbol use'
    )
    source = Path(__file__).read_text(encoding='utf-8')
    assert not PRIVATE.search(source) and not PROCESS.search(source), (
        'scanner definitions and controls must avoid manufacturing forbidden source residue'
    )


def secret_findings(entries):
    prefixes = (
        'ghp_',
        'gho_',
        'ghu_',
        'ghs_',
        'ghr_',
        'github_pat_',
        'AKIA',
        'ASIA',
        'xoxa-',
        'xoxb-',
        'xoxp-',
        'xoxo-',
        'xoxs-',
        'xoxr-',
        'AIza',
        '-----BEGIN',
    )
    return [
        name
        for name, text in entries
        if (any(prefix in text for prefix in prefixes) or 'aws' in text.casefold())
        and SECRET.search(text)
    ]


def test_independent_secret_predicate_checks_every_decoded_member():
    findings = secret_findings(publication_texts())
    assert not findings, (
        'the independent publication check must reject credentials in decoded members: '
        + ', '.join(findings[:20])
    )


@pytest.fixture(scope='module')
def publication_scan_files():
    tracked = run('git', 'ls-files', '-z', '--cached')
    untracked = run('git', 'ls-files', '-z', '--others', '--exclude-standard')
    require_success(tracked, 'publication partitions must enumerate every committed file')
    require_success(untracked, 'publication partitions must enumerate every additional input')
    # Partition every source byte. Archives remain intact and literal symlink targets survive.
    excluded = ('.git/', '.pixi/', 'build/', 'site/', 'node_modules/', '__pycache__/')
    names = set(tracked.stdout.split('\0')) | {
        name for name in untracked.stdout.split('\0') if not name.startswith(excluded)
    }
    return sorted(
        name for name in names if name and ((ROOT / name).is_file() or (ROOT / name).is_symlink())
    )


@pytest.mark.parametrize('part', range(32))
def test_secret_scanner_checks_the_prepared_tree(tmp_path, publication_scan_files, part):
    # Each path belongs to exactly one part. Hard links preserve every source byte;
    # symlinks preserve their literal targets, never substitute target content.
    prepared = tmp_path / 'publication'
    prepared.mkdir()
    # The measured runtime table is plain line-oriented TSV, larger than one
    # bounded scanner call. Retain every complete record, exactly once across
    # contiguous slices. Archive members and symlink targets are never split.
    runtime_table = 'tests/per-pr-runtimes.tsv'
    ordinary = [name for name in publication_scan_files if name != runtime_table]
    if runtime_table in publication_scan_files:
        source = ROOT / runtime_table
        assert source.is_file() and not source.is_symlink(), (
            'Only the regular plain-text runtime table may be divided at record boundaries'
        )
        lines = source.read_bytes().splitlines(keepends=True)
        target = prepared / runtime_table
        target.parent.mkdir(parents=True)
        target.write_bytes(
            b''.join(lines[len(lines) * part // 32 : len(lines) * (part + 1) // 32])
        )
    for relative in ordinary[part::32]:
        source, target = ROOT / relative, prepared / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_symlink():
            target.symlink_to(source.readlink())
        else:
            os.link(source, target)
    deadline = time.monotonic() + 5
    try:
        result = run(
            sys.executable,
            str(script('scan.py')),
            '--tree',
            str(prepared),
            timeout=max(0, deadline - time.monotonic()),
        )
    except subprocess.TimeoutExpired:
        pytest.fail('each full-byte publication partition must meet the system-test budget')
    require_success(result, 'the production scanner must inspect every prepared-tree partition')


ARCHIVE_FORMS = (
    'zip',
    'tar',
    'tar.gz',
    'tar.bz2',
    'tar.xz',
    'gz',
    'bz2',
    'xz',
    'zst',
    'nested.zip',
    'renamed.bin',
    'ztxt.png',
    'itxt.png',
)


def compressed_control(form, content):
    """Author a container independently of the production scanner or scrubber."""
    if form.endswith('.png'):

        def chunk(kind, body):
            return (
                struct.pack('>I', len(body))
                + kind
                + body
                + struct.pack('>I', zlib.crc32(kind + body))
            )

        metadata = (
            chunk(b'zTXt', b'Comment\0\0' + zlib.compress(content))
            if form == 'ztxt.png'
            else chunk(b'iTXt', b'Comment\0\1\0\0\0' + zlib.compress(content))
        )
        return (
            b'\x89PNG\r\n\x1a\n'
            + chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 0, 0, 0, 0))
            + metadata
            + chunk(b'IDAT', zlib.compress(b'\0\0'))
            + chunk(b'IEND', b'')
        )
    if form in {'zip', 'nested.zip', 'renamed.bin'}:
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            if form == 'nested.zip':
                archive.writestr('inner.zip', compressed_control('zip', content))
            else:
                archive.writestr('member.txt', content)
        return stream.getvalue()
    if form.startswith('tar'):
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode='w') as archive:
            member = tarfile.TarInfo('member.txt')
            member.size = len(content)
            archive.addfile(member, io.BytesIO(content))
        raw = stream.getvalue()
        return {
            'tar': lambda data: data,
            'tar.gz': gzip.compress,
            'tar.bz2': bz2.compress,
            'tar.xz': lzma.compress,
        }[form](raw)
    return {'gz': gzip.compress, 'bz2': bz2.compress, 'xz': lzma.compress, 'zst': zstd.compress}[
        form
    ](content)


@pytest.mark.parametrize('form', ARCHIVE_FORMS)
@pytest.mark.parametrize('kind', ['private', 'process', 'secret'])
def test_compressed_member_reaches_independent_and_production_checks(tmp_path, form, kind):
    samples = {
        'private': ('crysta' + chr(32) + 'ADR-0099').encode(),
        'process': (chr(67) + '11-T42').encode(),
        'secret': ('gh' + 'p_' + 'A' * 36).encode(),
    }
    name = 'payload.' + form
    data = compressed_control(form, samples[kind])
    entries = list(decoded_texts(name, data))
    finding = {
        'private': lambda: any(PRIVATE.search(text) for _, text in entries),
        'process': lambda: bool(process_findings(entries)),
        'secret': lambda: bool(secret_findings(entries)),
    }[kind]()
    assert finding, 'each compressed member must reach its independent publication predicate'
    (tmp_path / name).write_bytes(data)
    result = run(sys.executable, str(script('scan.py')), '--tree', str(tmp_path))
    assert result.returncode != 0 and name in result.stdout + result.stderr, (
        'the production publication scanner must reject a named compressed-member escape: '
        + form
        + '/'
        + kind
    )


@pytest.mark.parametrize('form', ['zip', 'tar', 'gz', 'bz2', 'xz', 'zst', '7z'])
def test_unreadable_containers_refuse_publication(tmp_path, form):
    name = 'broken.' + form
    with pytest.raises(AssertionError, match='publication checks must refuse'):
        list(decoded_texts(name, b'not an archive'))
    (tmp_path / name).write_bytes(b'not an archive')
    result = run(sys.executable, str(script('scan.py')), '--tree', str(tmp_path))
    assert result.returncode != 0 and name in result.stdout + result.stderr, (
        'an unreadable or unsupported compressed container must refuse publication by name'
    )


@pytest.mark.parametrize('form', ['zip', 'tar.gz', 'nested.zip'])
def test_archive_process_allowance_matches_ordinary_test_names(form):
    label = chr(67) + '11-T42'
    text = 'def test_' + label.replace('-', '_').lower() + '_witness(): pass\n'
    native = 'TEST_CASE("' + label + ' witness") {}\n'
    payload = (text + native).encode()
    assert not process_findings(
        decoded_texts('allowed.' + form, compressed_control(form, payload))
    ), 'decoded members must retain the same actual Python and native test-name allowance'
    contaminated = payload + ('# ordinary context ' + label).encode()
    assert process_findings(
        decoded_texts('blocked.' + form, compressed_control(form, contaminated))
    ), 'permitted test names must not exempt ordinary process prose elsewhere in a member'


SECRET_SHAPES = {
    **{'github-' + kind: 'gh' + kind + '_' + 'A' * 36 for kind in 'pousr'},
    **{'slack-' + kind: 'xox' + kind + '-' + 'A' * 10 for kind in 'abposr'},
    'github-fine': 'github' + '_pat_' + 'A' * 60,
    'aws-access': 'AK' + 'IA' + 'A' * 16,
    'aws-session': 'AS' + 'IA' + 'A' * 16,
    'google': 'AI' + 'za' + 'A' * 35,
    'private-key': '-----BEGIN RSA ' + 'PRIVATE KEY-----',
    'aws-secret': 'aWs_SeCrEt_AcCeSs_KeY = ' + 'A' * 40,
}


@pytest.mark.parametrize('shape', sorted(SECRET_SHAPES))
def test_secret_prefix_filter_keeps_every_credential_shape(shape):
    candidate = SECRET_SHAPES[shape]
    assert SECRET.search(candidate), 'each independent credential control must match its format'
    text = '1.2345 6.789\n' * 1000 + candidate + '\n' + '0.1234 5.678\n' * 1000
    assert secret_findings([('numeric-member', text)]) == ['numeric-member'], (
        'the fast prefix filter must retain every credential shape inside numeric member data'
    )


@pytest.mark.parametrize('name', sorted(VENDOR))
def test_vendor_process_allowance_requires_exact_declared_release_bytes(name):
    text = (ROOT / name).read_text()
    assert hashlib.sha256(text.encode()).hexdigest() == VENDOR[name]['sha256'], (
        'A vendor allowance binds the declared version and upstream member to exact release bytes'
    )
    assert not process_findings([(name, text)]), (
        'The declared unmodified third-party release carries no project process citation'
    )
    marker = '\n' + 're' + 'lay' + ' process reference\n'
    assert process_findings([(name, text + marker)]), (
        'Appending a process citation to a declared vendor file must invalidate its allowance'
    )


@pytest.mark.parametrize(
    'name',
    [
        'data/report/vendor/neighbor.js',
        'data/report/vendor/plotly-cartesian-3.7.1.min.js',
        'archive.zip!data/report/vendor/plotly-cartesian-3.7.0.min.js',
    ],
    ids=['neighbor', 'another-version', 'archive-member'],
)
def test_vendor_allowance_does_not_cover_other_paths_or_versions(name):
    text = (ROOT / 'data/report/vendor/plotly-cartesian-3.7.0.min.js').read_text()
    assert process_findings([(name, text)]), (
        'The same process-shaped vendor token remains visible outside its exact declared path'
    )


@pytest.mark.parametrize(
    'damage',
    [
        'name',
        'path',
        'producer',
        'upload-first',
        'missing-proof',
        'disabled-proof',
        'optional-proof',
        'comment-only',
    ],
)
def test_reviewed_delivery_artifacts_reject_identity_and_qualification_escapes(damage):
    import copy  # noqa: PLC0415 - keep the policy control self-contained

    from tests.fixtures.public_artifact_contract import ROUTES, reviewed_delivery  # noqa: PLC0415

    documents = dict(workflows())
    for (filename, producer, artifact), (_paths, proofs) in ROUTES.items():
        job = documents[filename]['jobs'][producer]
        upload = next(
            step for step in job['steps'] if step.get('with', {}).get('name') == artifact
        )
        assert reviewed_delivery(filename, producer, job, upload), (
            'Each published or shared artifact first proves its exact producer and prerequisites: '
            + filename
            + '/'
            + artifact
        )
        changed = copy.deepcopy(job)
        target = next(
            step for step in changed['steps'] if step.get('with', {}).get('name') == artifact
        )
        selected_producer = producer
        if damage in {'name', 'path'}:
            target['with'][damage] = 'unreviewed-binary-output'
        elif damage == 'producer':
            selected_producer = 'unreviewed-producer'
        elif damage == 'upload-first':
            changed['steps'].remove(target)
            changed['steps'].insert(0, target)
        else:
            proof_steps = [step for step in changed['steps'] if proofs[0] in step.get('run', '')]
            assert proof_steps, (
                'The source escape challenge must reach its real qualification producer'
            )
            for proof in proof_steps:
                if damage == 'missing-proof':
                    changed['steps'].remove(proof)
                elif damage == 'disabled-proof':
                    proof['if'] = False
                elif damage == 'optional-proof':
                    proof['continue-on-error'] = True
                else:
                    proof['run'] = '\n'.join('# ' + line for line in proof['run'].splitlines())
        assert not reviewed_delivery(filename, selected_producer, changed, target), (
            'Each artifact route refuses changed identity, producer, order or qualification: '
            + filename
            + '/'
            + artifact
            + '/'
            + damage
        )


@pytest.mark.parametrize(
    'damage', ['changed-home', 'private-citation', 'changed-case', 'other-path', 'archive-copy']
)
def test_synthetic_privacy_input_allowance_binds_exact_declared_reference_bytes(damage):
    name = 'tests/fixtures/onboarding/privacy_representations.json'
    original = (ROOT / name).read_text(encoding='utf-8')
    assert not private_findings([(name, original)]), (
        'The independently authored synthetic privacy cases first admit unchanged'
    )
    candidate, path = original, name
    if damage == 'changed-home':
        candidate = original.replace('Mary Jane', 'actual-account')
    elif damage == 'private-citation':
        candidate += '\ncrysta' + chr(32) + 'ADR-0999\n'
    elif damage == 'changed-case':
        candidate += '\n'
    else:
        path = ('copy/' if damage == 'other-path' else 'archive.zip!') + name
    assert private_findings([(path, candidate)]), (
        'Synthetic data cannot hide changed private inputs, citations or copied members'
    )
