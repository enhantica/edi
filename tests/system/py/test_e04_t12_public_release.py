"""Public tree checks against the dated content review and local snapshot invariants.

No network operation is performed here. Live CI, deployment and settings are
operator evidence; these gates check the versioned inputs and local rehearsal.
"""

from __future__ import annotations

import ast
import bz2
import gzip
import io
import json
import lzma
import re
import runpy
import struct
import subprocess
import sys
import tarfile
import tomllib
import zipfile
import zlib
from functools import cache
from pathlib import Path

import pytest
import yaml
from compression import zstd

ROOT = Path(__file__).resolve().parents[3]
ORACLE = json.loads((ROOT / 'tests/fixtures/e04_t12_public_release/oracle.json').read_text())
# Construct forbidden spellings so the scanner does not manufacture a private reference.
PROCESS = re.compile(r'\b(?:[CE]\d{2}-T\d+[a-z]?|I-\d{4}|ORG-\d{4}|re[l]ay)\b', re.IGNORECASE)
PRIVATE = re.compile(
    r'crysta\s+A[D]R-\d+|enhantica/c[r]ysta/(?:blob|tree)/'
    r'|c[r]ysta/(?:tests|docs|knowledge|core)/'
    r'|(?:~|/h[o]me/[^/\s]+)/ru[n]s/|/h[o]me/[^/\s]+/|/U[s]ers/[^/\s]+/'
)
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


def test_tree_has_no_personal_paths_or_private_citations():
    findings = [
        name
        for name, text in publication_texts()
        if any(prefix in text for prefix in ('crysta', '/home/', '/Users/', '~/r' + 'uns/'))
        and PRIVATE.search(text)
    ]
    assert not findings, (
        'the prepared public tree must contain no personal paths, run pointers or private '
        'source/architecture citations; affected files: ' + ', '.join(findings[:20])
    )


def process_findings(entries):
    findings = []
    for name, text in entries:
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
    # Before: only the renamed Licence label was checked. After: the labelled app
    # link must open the local notice, whose GPL/BSD split replaces the sentence.
    assert re.search(
        r'"title"\s*:\s*qsTr\("(?:Licence|End User Licence Agreement)"\)\s*,\s*'
        r'"url"\s*:\s*ApplicationInfo\.appLicenseUrl',
        about,
    ), 'the About application licence label must bind to the application notice metadata'
    assert 'about.licence"' not in about and 'This app is distributed under' not in about, (
        'the About window must omit the superseded distribution sentence'
    )
    assert re.search(
        r'QString appLicenseUrl\(\) const\s*\{\s*return QStringLiteral\('
        r'"qrc:/app/DISTRIBUTION-LICENSE\.md"\);\s*\}',
        info,
    ), 'the About app link must target its distribution notice rather than the source licence'
    assert '${PROJECT_SOURCE_DIR}/app/DISTRIBUTION-LICENSE.md' in cmake, (
        'the app resources must include the application distribution notice file'
    )
    assert '"app/DISTRIBUTION-LICENSE.md"' in info, (
        'the licence resource reader must admit the application notice linked from About'
    )
    viewer = (ROOT / 'app/qml/Pages/Home/LicenceTextDialog.qml').read_text()
    assert 'licenceDialog.showText(link.modelData.title, link.modelData.url)' in about and (
        'ApplicationInfo.licenceText(dialog.url)' in viewer
    ), 'activating the About licence link must display the selected bundled resource'
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
    condition = str(condition)
    if '||' in condition or '!' in condition.replace('!=', ''):
        return False
    return any(
        token
        in [
            term.strip(' ()')
            for term in condition.replace('${{', '').replace('}}', '').split('&&')
        ]
        for token in (
            'github.event.pull_request.head.repo.fork == false',
            'github.event.pull_request.head.repo.full_name == github.repository',
            "github.event_name == 'push'",
            "github.event_name == 'workflow_dispatch'",
        )
    )


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
    findings = []
    for filename, doc in workflows():
        for name, job in doc.get('jobs', {}).items():
            if 'uses' in job:
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
                if private and not (nonfork(job.get('if', '')) or nonfork(step.get('if', ''))):
                    findings.append(filename + ':' + name + ':unguarded private token')
                if private and not job.get('environment'):
                    findings.append(filename + ':' + name + ':token outside reviewed environment')
    assert not findings, (
        'public CI must use hosted runners; private credentials need a non-fork guard and '
        'reviewed '
        'environment: ' + ', '.join(findings)
    )


def test_public_artifacts_exclude_engine_object_code_and_runner_names():
    findings = []
    for filename, doc in workflows():
        for name, job in doc.get('jobs', {}).items():
            for step in job.get('steps', []):
                if 'upload-artifact' not in step.get('uses', ''):
                    continue
                options = step.get('with', {})
                artifact, paths = options.get('name', ''), options.get('path', '')
                if 'runner.name' in artifact or 'edi-native' in artifact:
                    findings.append(filename + ':' + name + ':private artifact identity')
                # Explicitly safe output types; an opaque archive/build directory needs a
                # reviewed packaging gate, not a claim that its contents happen to be safe.
                for path in paths.splitlines():
                    if path.startswith('!'):
                        continue
                    if path and not (
                        Path(path).suffix
                        in {'.json', '.log', '.txt', '.csv', '.tsv', '.png', '.svg'}
                        or path in {'build/app/ui-actual', 'build/app/ui-diff'}
                    ):
                        findings.append(filename + ':' + name + ':opaque/binary artifact ' + path)
    assert not findings, (
        'public uploads must expose reviewed text/image outputs and no private engine object code '
        'or runner names: ' + ', '.join(findings)
    )


def test_pages_builds_docs_and_reserves_unlisted_webapp():
    pages = [doc for _, doc in workflows() if 'actions/deploy-pages' in json.dumps(doc)]
    assert pages, 'the public site needs a GitHub Pages deployment workflow'
    serialized = json.dumps(pages)
    assert 'mkdocs' in serialized or 'docs-build' in serialized, (
        'Pages must build the docs from this source tree'
    )
    assert 'actions/upload-pages-artifact' in serialized and 'webapp' in serialized, (
        'the published Pages artifact must include the reserved webapp directory'
    )
    config = yaml.load((ROOT / 'mkdocs.yml').read_text(), Loader=yaml.BaseLoader)
    assert 'webapp' not in json.dumps(config.get('nav', [])), (
        'the app folder is served but remains absent from the public docs navigation'
    )
    assert 'site_url' in config, 'the public docs must declare their published canonical URL'


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


def test_secret_scanner_checks_the_prepared_tree():
    findings = secret_findings(publication_texts())
    assert not findings, (
        'the independent publication check must reject credentials in decoded members: '
        + ', '.join(findings[:20])
    )
    scanner = script('scan.py')
    try:
        # Leave room for the independent predicate within the existing system
        # tier's five-second bound. A slow/incomplete scan cannot certify a tree.
        result = run(sys.executable, str(scanner), '--tree', str(ROOT), timeout=3)
    except subprocess.TimeoutExpired:
        pytest.fail('the full publication scanner must complete within the system-test budget')
    require_success(result, 'the final release secrets scan must inspect the entire prepared tree')


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
