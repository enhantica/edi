"""Real CMake runtime-publication contracts over tiny non-runtime fixtures.

Prior art: tests/integration/cmake/check_gui_base.py's project(... NONE) carrier.
The fixture executables are never run and do not qualify an upstream package.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

ROOT = Path(os.environ.get('EDI_TEST_RUNTIME_ROOT', Path(__file__).resolve().parents[3])).resolve()
TARGETS = {'Linux': 'x86_64-unknown-linux-musl', 'Darwin': 'aarch64-apple-darwin'}
REQUIRED = (
    'bin/codex-app-server',
    'bin/codex-code-mode-host',
    'codex-path/rg',
    'codex-resources/zsh/bin/zsh',
)


def _digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def _inventory(root):
    """Observe exact owned filesystem facts without reading links or special files."""
    if not root.exists() and not root.is_symlink():
        return {'absent': True}
    result = {}
    todo = [(root, '')]
    while todo:
        path, name = todo.pop()
        mode = path.lstat().st_mode
        proof = path.lstat()
        row = {'mode': stat.S_IMODE(mode), 'device': proof.st_dev, 'inode': proof.st_ino}
        if stat.S_ISLNK(mode):
            row.update(kind='symlink', target=str(path.readlink()))
        elif stat.S_ISDIR(mode):
            row['kind'] = 'directory'
            todo.extend(
                (child, '/'.join(filter(None, (name, child.name))))
                for child in sorted(path.iterdir())
            )
        elif stat.S_ISREG(mode):
            row.update(kind='file', sha256=_digest(path), bytes=proof.st_size)
        else:
            row['kind'] = 'special'
        result[name] = row
    return result


def _runtime_configure_outcome(result, marker_present, trace, module, caller, marker):
    """Separate actual bundler entry/errors, outer return and configure success."""
    calls = [
        index
        for index, event in enumerate(trace)
        if event.get('cmd') == 'edi_bundle_assistant_runtime' and event.get('file') == str(caller)
    ]
    active = []
    returned = False
    if len(calls) == 1:
        call = trace[calls[0]]
        for event in trace[calls[0] + 1 :]:
            if event.get('frame', 0) <= call.get('frame', 0):
                returned = (
                    event.get('file') == str(caller)
                    and event.get('cmd') == 'file'
                    and event.get('args') == ['WRITE', str(marker), 'original function returned']
                )
                break
            active.append(event)
    entered = any(
        event.get('file') == str(module) and event.get('cmd') not in {'function', 'macro'}
        for event in active
    )
    errors = re.findall(r'^CMake Error[^\n]*', result.stderr, flags=re.MULTILINE)
    error_files = []
    for error in errors:
        match = re.fullmatch(r'CMake Error at (.+):[0-9]+(?: \([^)]*\))?:', error)
        if match is None:
            match = re.fullmatch(r'CMake Error in (.+):', error)
        if match is not None:
            error_files.append(match[1])
    owned_files = {event.get('file') for event in active}
    owned_error = (
        bool(errors)
        and len(error_files) == len(errors)
        and all(path in owned_files for path in error_files)
    )
    return {
        'return_marker_present': marker_present,
        'caller_return_observed': returned,
        'runtime_entered': entered,
        'error_headers': errors,
        'error_files': error_files,
        'all_errors_in_entered_owner': owned_error,
        'configure_accepted': result.returncode == 0
        and marker_present
        and returned
        and entered
        and not errors,
        'runtime_refused': result.returncode > 0 and entered and owned_error,
    }


class RuntimeFixture:
    def __init__(self, root, *, system='Linux', dedicated=False):
        self.root = root
        self.system = system
        self.dedicated = dedicated
        self.target = TARGETS[system]
        self.project = root / 'project'
        self.build = root / 'build'
        self.prefix = root / 'installed-prefix'
        self.package = self.prefix / 'share/edi/assistant/runtime/0.162.1'
        self.payload = self.package / 'payload'
        self.manifest = self.package / 'input.json'
        self.module = Path(
            os.environ.get('EDI_TEST_RUNTIME_CMAKE', ROOT / 'cmake/assistant_runtime.cmake')
        ).resolve()
        self.cmake = shutil.which('cmake')
        assert self.cmake and self.module.is_file(), (
            'The real existing CMake executable/module must be available; missing tools '
            'are not a passing or skipped reuse witness'
        )
        self.project.mkdir(parents=True)
        for name in (*REQUIRED, *(['codex-resources/bwrap'] if system == 'Linux' else [])):
            path = self.payload / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('#!/bin/sh\n# Independent non-runtime configure fixture.\nexit 97\n')
            path.chmod(0o755)
        metadata = {
            'layoutVersion': 1,
            'version': '0.162.1',
            'target': self.target,
            'variant': 'codex-app-server',
            'entrypoint': 'bin/codex-app-server',
            'resourcesDir': 'codex-resources',
            'pathDir': 'codex-path',
        }
        if dedicated:
            patch = self.project / 'tools/assistant-runtime/edi-app-server.patch'
            patch.parent.mkdir(parents=True)
            patch.write_bytes(b'Independent dedicated input patch-identity fixture.\n')
            metadata.update(
                ediPolicySchema='edi.runtime-policy/1',
                ediFlavour='edi-app-server/1',
                upstreamCommit='092d3acd6bec3e3a14bdc7e7a2810ab628ab759d',
                sourcePatchSha256=_digest(patch),
            )
            self.legal = self.project / 'data/assistant/runtime'
        else:
            self.legal = self.payload / 'edi-licenses'
        self.legal.mkdir(parents=True)
        (self.legal / 'LICENSE').write_bytes(b'Independent original legal-closure fixture.\n')
        (self.legal / 'NOTICE').write_bytes(b'Independent original notice fixture.\n')
        (self.payload / 'codex-package.json').write_text(json.dumps(metadata, sort_keys=True))
        self.archive = hashlib.sha256(
            b'Independent fixture archive identity, not upstream.'
        ).hexdigest()
        self.refresh_manifest()
        cmake_dir = self.project / 'cmake'
        cmake_dir.mkdir()
        shutil.copyfile(
            ROOT / 'cmake/assistant_runtime_config.hpp.in',
            cmake_dir / 'assistant_runtime_config.hpp.in',
        )
        (self.project / 'CMakeLists.txt').write_text("""cmake_minimum_required(VERSION 3.26)
project(OriginalAssistantRuntimePublication NONE)
set(CMAKE_SYSTEM_NAME "${TEST_SYSTEM}")
if(TEST_SYSTEM STREQUAL "Darwin")
  set(CMAKE_SYSTEM_PROCESSOR arm64)
else()
  set(CMAKE_SYSTEM_PROCESSOR x86_64)
endif()
set(CMAKE_INSTALL_LIBEXECDIR libexec)
add_custom_target(edi_app_module)
include("${TEST_RUNTIME_MODULE}")
edi_bundle_assistant_runtime()
file(WRITE "${CMAKE_BINARY_DIR}/accepted" "original function returned")
""")
        self.serial = 0

    def refresh_manifest(self):
        members = {
            path.relative_to(self.payload).as_posix(): _digest(path)
            for path in sorted(self.payload.rglob('*'))
            if path.is_file()
        }
        value = {
            'schema': 'edi.assistant.provisioned/1'
            if self.dedicated
            else 'edi.assistant.runtime-package/1',
            'root': str(self.payload) if self.dedicated else 'payload',
            'version': '0.162.1',
            'target': self.target,
            'archive_sha256': self.archive,
            'dedicated': self.dedicated,
            'files': members,
        }
        self.manifest.write_text(json.dumps(value, sort_keys=True))

    def configure(self, label, *, known_paths=()):
        self.serial += 1
        log = self.root / f'{self.serial:02d}-{label}'
        log.mkdir()
        return_marker = self.build / 'accepted'
        return_marker.unlink(missing_ok=True)
        command = [
            self.cmake,
            '-S',
            str(self.project),
            '-B',
            str(self.build),
            f'-DTEST_SYSTEM={self.system}',
            f'-DTEST_RUNTIME_MODULE={self.module}',
            f'-DEDI_ASSISTANT_DEDICATED_RUNTIME={"ON" if self.dedicated else "OFF"}',
            f'-DEDI_CODEX_INPUT_MANIFEST={self.manifest}',
            '--trace-expand',
            '--trace-format=json-v1',
            f'--trace-redirect={log / "trace.jsonl"}',
        ]
        env = {
            **os.environ,
            'PIXI_ENVIRONMENT_PREFIX': str(self.prefix),
            'CONDA_PREFIX': str(self.root / 'nonexistent-other-prefix'),
        }
        # Only named actual source owners and explicitly known referents,
        # never a recursive inventory of changing build/log roots or links.
        input_paths = [
            self.payload,
            self.manifest,
            self.project / 'CMakeLists.txt',
            self.project / 'cmake/assistant_runtime_config.hpp.in',
        ]
        if self.dedicated:
            input_paths.extend((
                self.legal,
                self.project / 'tools/assistant-runtime/edi-app-server.patch',
            ))
        input_paths.extend(known_paths)
        before_inputs = {str(path): _inventory(path) for path in input_paths}
        try:
            run = subprocess.run(
                command, env=env, capture_output=True, text=True, check=False, timeout=5
            )
        except subprocess.TimeoutExpired as error:
            after_inputs = {name: _inventory(Path(name)) for name in before_inputs}
            (log / 'PRESERVATION.json').write_text(
                json.dumps(
                    {
                        'before': before_inputs,
                        'after': after_inputs,
                        'preserved': after_inputs == before_inputs,
                    },
                    indent=2,
                )
            )
            (log / 'TIMEOUT.json').write_text(
                json.dumps({
                    'command': command,
                    'module_sha256': _digest(self.module),
                    'qualification': (
                        'The owned configure reader failed to terminate; no pass/refusal claimed.'
                    ),
                })
            )
            pytest.fail(
                'Missing/nonregular/symlink input must refuse before a blocking read; '
                f'the unchanged five-second configure observation expired: {error}'
            )
        (log / 'stdout').write_text(run.stdout)
        (log / 'stderr').write_text(run.stderr)
        trace = [json.loads(line) for line in (log / 'trace.jsonl').read_text().splitlines()]
        outcome = _runtime_configure_outcome(
            run,
            return_marker.is_file(),
            trace,
            self.module,
            self.project / 'CMakeLists.txt',
            return_marker,
        )
        (log / 'RESULT.json').write_text(
            json.dumps(
                {
                    'command': command,
                    'module_sha256': _digest(self.module),
                    'test_source_sha256': _digest(Path(__file__)),
                    'repo_root': str(ROOT),
                    'config_template_sha256': _digest(
                        ROOT / 'cmake/assistant_runtime_config.hpp.in'
                    ),
                    'exit': run.returncode,
                    'return_marker': str(return_marker),
                    **outcome,
                    'fixture': (
                        'Tiny authored manifest/files; no official runtime '
                        'execution or packaging qualification.'
                    ),
                },
                indent=2,
            )
        )
        after_inputs = {name: _inventory(Path(name)) for name in before_inputs}
        (log / 'PRESERVATION.json').write_text(
            json.dumps(
                {
                    'before': before_inputs,
                    'after': after_inputs,
                    'preserved': after_inputs == before_inputs,
                },
                indent=2,
            )
        )
        assert after_inputs == before_inputs, (
            'Every actual consumed manifest/payload/legal/patch/config source and explicitly '
            'known existing or absent referent remains unchanged; see PRESERVATION.json'
        )
        return run, outcome, trace

    def publication(self):
        header = (self.build / 'assistant_runtime_config.hpp').read_text()
        found = re.findall(
            r'^#define EDI_CODEX_RUNTIME_BUILD_DIR R"\(([^\n]+)\)"$', header, flags=re.MULTILINE
        )
        assert len(found) == 1, (
            'The actual generated public configuration binds one published runtime'
        )
        path = Path(found[0])
        assert (
            path.parent == self.build / 'assistant-runtime' / self.target
            and re.fullmatch(r'runtime-[0-9a-f]{64}', path.name)
            and path.is_dir()
        ), (
            'The normal immutable content-addressed publication is actually reached, not'
            ' a made-up receipt or stage'
        )
        return path


def _successful(run):
    result, outcome, _trace = run
    assert (
        result.returncode == 0
        and outcome['configure_accepted']
        and outcome['return_marker_present']
        and outcome['caller_return_observed']
        and outcome['runtime_entered']
    ), (
        'The original runtime bundler must really return after complete verification: '
        + result.stdout
        + result.stderr
    )


def _refused(run):
    result, outcome, _trace = run
    assert (
        result.returncode > 0
        and outcome['runtime_refused']
        and outcome['runtime_entered']
        and outcome['all_errors_in_entered_owner']
        and not outcome['configure_accepted']
    ), (
        (
            'Invalid source/publication must fail closed, never repair/replace or accept a '
            'partial tree: '
        )
        + result.stdout
        + result.stderr
    )


def _payload_copy_calls(trace, payload):
    source = str(payload)
    calls = []
    for event in trace:
        args = event.get('args', [])
        command = event.get('cmd', '').lower()
        # Actual CMake command trace, not a source-string expectation. The
        # original COPY and ordinary CMake -E/cp entrances remain visible.
        copying = (
            command == 'file' and args and args[0].upper() in {'COPY', 'COPY_FILE', 'INSTALL'}
        )
        copying |= command == 'configure_file' and 'COPYONLY' in args
        copying |= command == 'execute_process' and any(
            part
            in {
                'copy',
                'copy_if_different',
                'copy_if_newer',
                'copy_directory',
                'copy_directory_if_different',
                'copy_directory_if_newer',
                'cp',
            }
            for part in args
        )
        if copying and any(str(part).startswith(source) for part in args):
            calls.append(event)
    return calls


def _assert_no_verified_source_copy(run, fixture):
    assert not _payload_copy_calls(run[2], fixture.payload) and not _payload_copy_calls(
        run[2], fixture.legal
    ), (
        'Existing publication inspection or invalid-input refusal never redundantly copies '
        'the original payload/legal closure before deciding; the real CMake trace must prove it'
    )


@pytest.mark.parametrize(
    ('system', 'dedicated'), [('Linux', False), ('Darwin', False), ('Linux', True)]
)
def test_real_runtime_configure_reuses_verified_publication_without_stage_copy(
    tmp_path, system, dedicated
):
    fixture = RuntimeFixture(tmp_path, system=system, dedicated=dedicated)
    first = fixture.configure('first-missing-publication')
    _successful(first)
    published = fixture.publication()
    before = _inventory(published)
    source = _inventory(fixture.payload)
    checkers = list(fixture.build.glob('verify_assistant_runtime_*.cmake'))
    assert len(checkers) == 1, 'The first real publication owns one immutable verifier'
    checker_before = _inventory(checkers[0])
    assert _payload_copy_calls(first[2], fixture.payload), (
        'The initial genuinely absent publication really enters normal payload staging; '
        'no precreated passing output is seeded'
    )
    assert not (published.parent / 'stage').exists(), (
        'Successful atomic publication leaves no payload stage'
    )
    expected = {
        path.relative_to(fixture.payload).as_posix(): path.read_bytes()
        for path in fixture.payload.rglob('*')
        if path.is_file()
    }
    if dedicated:
        expected.update({
            'edi-licenses/' + path.name: path.read_bytes() for path in fixture.legal.iterdir()
        })
    actual = {
        path.relative_to(published).as_posix(): path.read_bytes()
        for path in published.rglob('*')
        if path.is_file()
    }
    assert actual == expected, (
        'The complete original source/resource/legal closure survives publication exactly'
    )
    for name in REQUIRED:
        assert stat.S_IMODE((published / name).stat().st_mode) == stat.S_IMODE(
            (fixture.payload / name).stat().st_mode
        ), (
            'Actual original executable modes survive without resigning or substituting '
            'runtime bytes'
        )
    # No source/package write is needed to read/verify an already valid result.
    # A true OS permission premise makes redundant cache staging impossible.
    mode = stat.S_IMODE(published.parent.stat().st_mode)
    published.parent.chmod(0o555)
    try:
        assert not os.access(published.parent, os.W_OK), (
            'This fixture user must genuinely lack cache-parent write permission; a '
            'privileged host is an unreached premise, never a reuse pass'
        )
        second = fixture.configure('unchanged-readonly-cache-reuse')
        _successful(second)
        _assert_no_verified_source_copy(second, fixture)
        assert (
            fixture.publication() == published
            and _inventory(published) == before
            and _inventory(fixture.payload) == source
            and _inventory(checkers[0]) == checker_before
        ), (
            'Unchanged verified reuse retains exact path/member/hash/mode/inode '
            'identities in place, including every old reader'
        )
        assert (
            not _payload_copy_calls(second[2], fixture.payload)
            and not (published.parent / 'stage').exists()
        ), (
            'A successful no-op configure must not copy the payload to a temporary stage'
            ' before recognizing its valid publication'
        )
    finally:
        published.parent.chmod(mode)


SOURCE_ESCAPES = (
    'changed_byte_same_mtime',
    'unexpected_member',
    'missing_member',
    'directory_member',
    'symlink_member',
    'fifo_member',
    'symlink_parent',
    'symlink_root',
    'missing_manifest',
    'directory_manifest',
    'symlink_manifest',
    'fifo_manifest',
    'missing_legal',
    'missing_required',
    'nonexecutable_input',
    'wrong_metadata',
    'wrong_flavour',
    'wrong_target',
    'invalid_digest',
    'escaping_member',
)


def _replace_owned_input_entry(path, kind, link_target):
    path.unlink()
    if kind == 'directory':
        path.mkdir()
    elif kind == 'symlink':
        path.symlink_to(link_target)
    elif kind == 'fifo':
        os.mkfifo(path)


def _change_declared_manifest(fixture, escape):
    value = json.loads(fixture.manifest.read_text())
    if escape == 'escaping_member':
        value['files']['../outside'] = hashlib.sha256(b'outside').hexdigest()
    else:
        key, replacement = {
            'wrong_flavour': ('dedicated', True),
            'wrong_target': ('target', 'foreign-unqualified-target'),
            'invalid_digest': ('archive_sha256', 'not-a-digest'),
        }[escape]
        value[key] = replacement
    fixture.manifest.write_text(json.dumps(value))


@pytest.mark.parametrize('escape', SOURCE_ESCAPES)
def test_reuse_fully_revalidates_original_source_before_any_blocking_read(tmp_path, escape):
    fixture = RuntimeFixture(tmp_path)
    _successful(fixture.configure('establish-valid-publication'))
    publication = fixture.publication()
    original = _inventory(publication)
    member = fixture.payload / 'bin/codex-app-server'
    if escape == 'changed_byte_same_mtime':
        old = member.stat()
        member.write_bytes(member.read_bytes() + b'# Changed independently, same old timestamp.\n')
        os.utime(member, ns=(old.st_atime_ns, old.st_mtime_ns))
    elif escape == 'unexpected_member':
        (fixture.payload / 'unexpected').write_bytes(b'Not admitted by the input manifest.')
    elif escape in {'missing_member', 'directory_member', 'symlink_member', 'fifo_member'}:
        _replace_owned_input_entry(
            member, escape.removesuffix('_member'), fixture.payload / 'bin/codex-code-mode-host'
        )
    elif escape == 'symlink_parent':
        held = fixture.root / 'real-original-bin'
        (fixture.payload / 'bin').rename(held)
        (fixture.payload / 'bin').symlink_to(held, target_is_directory=True)
    elif escape == 'symlink_root':
        held = fixture.package / 'actual-payload'
        fixture.payload.rename(held)
        fixture.payload.symlink_to(held, target_is_directory=True)
    elif escape in {'missing_manifest', 'directory_manifest', 'symlink_manifest', 'fifo_manifest'}:
        original_file = fixture.root / 'unrelated-input.json'
        original_file.write_bytes(fixture.manifest.read_bytes())
        _replace_owned_input_entry(
            fixture.manifest, escape.removesuffix('_manifest'), original_file
        )
    elif escape == 'missing_legal':
        (fixture.legal / 'NOTICE').unlink()
        fixture.refresh_manifest()
    elif escape == 'missing_required':
        member.unlink()
        fixture.refresh_manifest()
    elif escape == 'nonexecutable_input':
        member.chmod(0o644)
    elif escape == 'wrong_metadata':
        path = fixture.payload / 'codex-package.json'
        value = json.loads(path.read_text())
        value['variant'] = 'unqualified-cli'
        path.write_text(json.dumps(value))
        fixture.refresh_manifest()
    else:
        _change_declared_manifest(fixture, escape)
    source = _inventory(fixture.payload)
    refused = fixture.configure(
        'source-' + escape,
        known_paths=(
            fixture.root / 'real-original-bin',
            fixture.package / 'actual-payload',
            fixture.root / 'unrelated-input.json',
        ),
    )
    _refused(refused)
    _assert_no_verified_source_copy(refused, fixture)
    assert _inventory(publication) == original and _inventory(fixture.payload) == source, (
        'Invalid source is not made acceptable by a cached receipt/mtime; existing '
        'immutable output and actual source remain untouched'
    )


OUTPUT_ESCAPES = (
    'changed_byte',
    'missing_member',
    'unexpected_member',
    'symlink_member',
    'fifo_member',
    'nonexecutable_output',
    'symlink_root',
    'regular_file_root',
    'corrupt_verifier',
    'symlink_verifier',
    'directory_verifier',
)


@pytest.mark.parametrize('escape', OUTPUT_ESCAPES)
def test_corrupt_or_foreign_immutable_publication_refuses_without_replacement(tmp_path, escape):
    fixture = RuntimeFixture(tmp_path)
    _successful(fixture.configure('establish-valid-publication'))
    publication = fixture.publication()
    source = _inventory(fixture.payload)
    member = publication / 'bin/codex-app-server'
    checker = list(fixture.build.glob('verify_assistant_runtime_*.cmake'))
    assert len(checker) == 1, 'The actual first publication owns exactly one original verifier'
    checker = checker[0]
    if escape == 'changed_byte':
        member.write_bytes(member.read_bytes() + b'# Corrupt immutable output.\n')
    elif escape in {'missing_member', 'symlink_member', 'fifo_member'}:
        member.unlink()
        if escape == 'symlink_member':
            member.symlink_to(fixture.payload / 'bin/codex-app-server')
        elif escape == 'fifo_member':
            os.mkfifo(member)
    elif escape == 'unexpected_member':
        (publication / 'foreign-member').write_bytes(b'Not in the original publication.')
    elif escape == 'nonexecutable_output':
        member.chmod(0o644)
    elif escape in {'symlink_root', 'regular_file_root'}:
        moved = publication.with_name('held-original-publication')
        publication.rename(moved)
        if escape == 'symlink_root':
            publication.symlink_to(moved, target_is_directory=True)
        else:
            publication.write_bytes(b'A regular file cannot stand in for the published tree.')
    elif escape == 'corrupt_verifier':
        checker.write_text('message(FATAL_ERROR "Foreign modified verifier")\n')
    elif escape == 'symlink_verifier':
        checker.unlink()
        checker.symlink_to(fixture.root / 'unrelated-checker')
    elif escape == 'directory_verifier':
        checker.unlink()
        checker.mkdir()
    before = _inventory(publication)
    verifier = _inventory(checker)
    refused = fixture.configure(
        'publication-' + escape,
        known_paths=(
            publication.with_name('held-original-publication'),
            fixture.root / 'unrelated-checker',
        ),
    )
    _refused(refused)
    _assert_no_verified_source_copy(refused, fixture)
    assert (
        _inventory(publication) == before
        and _inventory(checker) == verifier
        and _inventory(fixture.payload) == source
    ), (
        'Existing corrupt/foreign output is never silently deleted, repaired, followed '
        'or replaced, and the original source is read-only'
    )


@pytest.mark.parametrize('change', ['verified_payload', 'archive_identity', 'dedicated_legal'])
def test_changed_verified_identity_publishes_new_complete_tree_and_retains_old_readers(
    tmp_path, change
):
    fixture = RuntimeFixture(tmp_path, dedicated=change == 'dedicated_legal')
    _successful(fixture.configure('first-identity'))
    old = fixture.publication()
    previous = _inventory(old)
    if change == 'verified_payload':
        (fixture.payload / 'codex-resources/independent-resource.txt').write_bytes(
            b'New verified resource.\n'
        )
    elif change == 'archive_identity':
        fixture.archive = hashlib.sha256(
            b'Distinct independently verified archive identity.'
        ).hexdigest()
    else:
        (fixture.legal / 'NOTICE').write_bytes(b'Changed original dedicated notice.\n')
    fixture.refresh_manifest()
    second = fixture.configure('changed-valid-identity')
    _successful(second)
    new = fixture.publication()
    assert new != old and _inventory(old) == previous, (
        'A changed valid content/archive/legal identity publishes separately; existing '
        'readers keep their whole original immutable tree'
    )
    renamed = [
        event
        for event in second[2]
        if event.get('cmd', '').lower() == 'file'
        and event.get('args', [''])[0].upper() == 'RENAME'
        and str(new) in event.get('args', [])
    ]
    assert renamed and all(Path(event['args'][1]) != new for event in renamed), (
        'The genuinely missing new identity is published through the ordinary atomic '
        'rename after staging, never copied over an existing reader'
    )
    assert not (new.parent / 'stage').exists(), (
        'The complete new publication leaves no payload stage'
    )
    expected = {
        path.relative_to(fixture.payload).as_posix(): path.read_bytes()
        for path in fixture.payload.rglob('*')
        if path.is_file()
    }
    if fixture.dedicated:
        expected.update({
            'edi-licenses/' + path.name: path.read_bytes() for path in fixture.legal.iterdir()
        })
    actual = {
        path.relative_to(new).as_posix(): path.read_bytes()
        for path in new.rglob('*')
        if path.is_file()
    }
    assert actual == expected, (
        'Every newly verified payload/resource/legal byte belongs to the complete new publication'
    )


@pytest.mark.parametrize(
    'field', ['ediPolicySchema', 'ediFlavour', 'upstreamCommit', 'sourcePatchSha256']
)
def test_dedicated_reuse_still_checks_original_policy_patch_and_legal_owner(tmp_path, field):
    fixture = RuntimeFixture(tmp_path, dedicated=True)
    _successful(fixture.configure('original-qualified-dedicated-shape'))
    publication = fixture.publication()
    before = _inventory(publication)
    path = fixture.payload / 'codex-package.json'
    metadata = json.loads(path.read_text())
    metadata[field] = 'unqualified-original-owner-mismatch'
    path.write_text(json.dumps(metadata))
    fixture.refresh_manifest()
    refused = fixture.configure('dedicated-' + field)
    _refused(refused)
    _assert_no_verified_source_copy(refused, fixture)
    assert _inventory(publication) == before, (
        'A valid cached directory never bypasses the explicit original dedicated '
        'flavour/upstream/patch policy proof'
    )


@pytest.mark.parametrize('name', ['LICENSE', 'NOTICE'])
@pytest.mark.parametrize('kind', ['missing', 'symlink', 'fifo'])
def test_dedicated_reuse_checks_original_external_legal_members_without_blocking(
    tmp_path, name, kind
):
    fixture = RuntimeFixture(tmp_path, dedicated=True)
    _successful(fixture.configure('dedicated-legal-original'))
    published = fixture.publication()
    before = _inventory(published)
    member = fixture.legal / name
    _replace_owned_input_entry(
        member, kind, fixture.legal / ('NOTICE' if name == 'LICENSE' else 'LICENSE')
    )
    refused = fixture.configure('dedicated-legal-' + name + '-' + kind)
    _refused(refused)
    _assert_no_verified_source_copy(refused, fixture)
    assert _inventory(published) == before, (
        'Cached dedicated output never hides missing, linked or nonregular original legal input; '
        'validation refuses without copying or blocking on those members'
    )


def _unsafe_owned_path(path, kind, outside):
    assert not path.is_dir() or path.is_symlink(), (
        'The fixture never removes a directory or another owner; a real directory is '
        'moved aside explicitly first'
    )
    path.unlink(missing_ok=True)
    if kind == 'directory':
        path.mkdir()
    elif kind == 'file':
        path.write_bytes(b'A file is not an owned module directory.\n')
    elif kind == 'fifo':
        os.mkfifo(path)
    elif kind in {'symlink', 'dangling'}:
        path.symlink_to(outside, target_is_directory=outside.is_dir())
    else:
        assert kind == 'missing', 'Every named filesystem-kind entrance is explicit'


SIDECAR_KINDS = [
    (role, kind)
    for role in ('lock', 'verifier_stage', 'config_header')
    for kind in ('symlink', 'dangling', 'fifo', 'directory')
] + [('verifier', 'fifo')]


@pytest.mark.parametrize(('role', 'kind'), SIDECAR_KINDS)
def test_original_direct_sidecar_io_refuses_unsafe_kind_before_touching_target(
    tmp_path, role, kind
):
    fixture = RuntimeFixture(tmp_path)
    _successful(fixture.configure('prove-valid-original-owner'))
    publication = fixture.publication()
    published = _inventory(publication)
    checkers = list(fixture.build.glob('verify_assistant_runtime_*.cmake'))
    assert len(checkers) == 1
    checker = checkers[0]
    if role == 'lock':
        path = publication.parent / 'stage.lock'
    elif role == 'verifier_stage':
        path = checker.with_name(checker.name + '.stage')
        checker.unlink()  # Reach the original new-verifier WRITE/rename branch.
    elif role == 'verifier':
        path = checker
    else:
        path = fixture.build / 'assistant_runtime_config.hpp'
    outside = fixture.root / 'protected-unrelated-sidecar-target'
    if kind == 'symlink':
        outside.write_bytes(path.read_bytes() if path.is_file() else b'Unrelated bytes.\n')
    _unsafe_owned_path(path, kind, outside)
    unsafe = _inventory(path)
    protected = _inventory(outside)
    refused = fixture.configure(role + '-' + kind, known_paths=(path, outside))
    _refused(refused)
    _assert_no_verified_source_copy(refused, fixture)
    assert (
        _inventory(path) == unsafe
        and _inventory(outside) == protected
        and _inventory(publication) == published
    ), (
        'Unsafe preexisting read/lock/temporary/config output is refused promptly, '
        'never followed, deleted, repaired or replaced; original readers and '
        'unrelated bytes remain untouched'
    )


@pytest.mark.parametrize('role', ['cache_root', 'target_cache', 'stage'])
@pytest.mark.parametrize('kind', ['file', 'fifo', 'symlink', 'dangling'])
def test_original_module_directory_components_cannot_redirect_or_erase_owned_io(
    tmp_path, role, kind
):
    fixture = RuntimeFixture(tmp_path)
    _successful(fixture.configure('prove-directory-owner'))
    publication = fixture.publication()
    if role == 'cache_root':
        path = publication.parent.parent
    elif role == 'target_cache':
        path = publication.parent
    else:
        path = publication.parent / 'stage'
    held = fixture.root / 'held-original-module-tree'
    if role == 'stage':
        # A missing publication must use staging, so an ignored unrelated stage
        # beside an already valid publication cannot fake this entrance.
        publication.rename(held)
    else:
        path.rename(held)
    old_reader = _inventory(held)
    outside = held if kind == 'symlink' else fixture.root / 'absent-redirect-target'
    _unsafe_owned_path(path, kind, outside)
    unsafe = _inventory(path)
    protected = _inventory(outside)
    refused = fixture.configure(role + '-' + kind, known_paths=(path, outside, held))
    _refused(refused)
    _assert_no_verified_source_copy(refused, fixture)
    assert (
        _inventory(path) == unsafe
        and _inventory(outside) == protected
        and _inventory(held) == old_reader
    ), (
        'A module-owned cache/target/stage component has its actual directory role '
        'before descendant lock/read/copy/remove; no unsafe object or original held '
        'reader tree is touched'
    )


@pytest.mark.parametrize('role', ['manifest', 'dedicated_patch'])
@pytest.mark.parametrize('kind', ['missing', 'directory', 'symlink', 'dangling', 'fifo'])
def test_explicit_dedicated_direct_reads_and_hashes_check_kind_before_io(tmp_path, role, kind):
    fixture = RuntimeFixture(tmp_path, dedicated=True)
    _successful(fixture.configure('prove-explicit-dedicated-original'))
    publication = fixture.publication()
    published = _inventory(publication)
    path = (
        fixture.manifest
        if role == 'manifest'
        else fixture.project / 'tools/assistant-runtime/edi-app-server.patch'
    )
    outside = fixture.root / 'protected-explicit-input'
    if kind == 'symlink':
        outside.write_bytes(path.read_bytes())
    _unsafe_owned_path(path, kind, outside)
    unsafe = _inventory(path)
    protected = _inventory(outside)
    refused = fixture.configure('explicit-' + role + '-' + kind, known_paths=(path, outside))
    _refused(refused)
    _assert_no_verified_source_copy(refused, fixture)
    assert (
        _inventory(path) == unsafe
        and _inventory(outside) == protected
        and _inventory(publication) == published
    ), (
        'Explicit manifest READ and source-patch SHA256 are genuine original input '
        'owners too: bad kinds refuse before a blocking read or redirected '
        'authority, preserving all original data'
    )


def test_original_owned_regular_verifier_temporary_still_publishes_exact_checker(tmp_path):
    fixture = RuntimeFixture(tmp_path)
    _successful(fixture.configure('prove-original-regular-temporary-owner'))
    publication = fixture.publication()
    original = _inventory(publication)
    checkers = list(fixture.build.glob('verify_assistant_runtime_*.cmake'))
    assert len(checkers) == 1
    checker = checkers[0]
    original_checker = checker.read_bytes()  # Original actual constructor regression pin.
    checker.unlink()
    temporary = checker.with_name(checker.name + '.stage')
    temporary.write_bytes(b'Original ordinary owned regular temporary bytes.\n')
    successful = fixture.configure('regular-verifier-stage-control')
    _successful(successful)
    _assert_no_verified_source_copy(successful, fixture)
    assert (
        checker.read_bytes() == original_checker
        and not temporary.exists()
        and _inventory(publication) == original
    ), (
        'Kind protection preserves the normal existing regular temporary '
        'write/atomic rename, exact original checker bytes and valid publication, '
        'rather than rejecting every preexisting sidecar'
    )


def test_copy_trace_observes_each_supported_ordinary_operation_for_both_source_owners(tmp_path):
    fixture = RuntimeFixture(tmp_path, dedicated=True)
    for source in (fixture.payload, fixture.legal):
        operations = [
            {'cmd': 'file', 'args': ['COPY', str(source) + '/', 'DESTINATION', 'owned-output']},
            {'cmd': 'file', 'args': ['COPY_FILE', str(source / 'member'), 'owned-output']},
            {'cmd': 'file', 'args': ['INSTALL', 'FILES', str(source / 'member')]},
            {
                'cmd': 'configure_file',
                'args': [str(source / 'member'), 'owned-output', 'COPYONLY'],
            },
        ]
        operations.extend(
            {
                'cmd': 'execute_process',
                'args': ['COMMAND', fixture.cmake, '-E', operation, str(source), 'owned-output'],
            }
            for operation in (
                'copy',
                'copy_if_different',
                'copy_if_newer',
                'copy_directory',
                'copy_directory_if_different',
                'copy_directory_if_newer',
            )
        )
        operations.append({
            'cmd': 'execute_process',
            'args': ['COMMAND', 'cp', str(source / 'member'), 'owned-output'],
        })
        for event in operations:
            assert _payload_copy_calls([event], source) == [event], (
                'Every declared supported ordinary CMake copy operation is recognized for '
                'each independently owned payload and dedicated legal source; no case can '
                'escape the shared real-trace no-copy assertion'
            )
        reads = [
            {'cmd': 'file', 'args': [operation, str(source / 'member'), 'result']}
            for operation in ('READ', 'SHA256')
        ]
        assert not _payload_copy_calls(reads, source), (
            'Full source verification reads and hashes are permitted and never '
            'mislabelled as copies'
        )


def _original_runtime_select_literal_manifest(fixture, original_caller, spelling):
    # Public CMake caller variable only; actual module and every200 owner stay intact.
    call = 'edi_bundle_assistant_runtime()\n'
    assert original_caller.count(call) == 1 and ']==]' not in spelling
    (fixture.project / 'CMakeLists.txt').write_text(
        original_caller.replace(
            call, 'set(EDI_CODEX_INPUT_MANIFEST [==[' + spelling + ']==])\n' + call
        )
    )


@pytest.mark.parametrize('form', ['relative', 'absolute'])
@pytest.mark.parametrize('selection', ['symlink_parent', 'nonexistent_component'])
def test_original_explicit_manifest_spelling_selects_filesystem_owner_without_lexical_collapse(
    tmp_path, form, selection
):
    fixture = RuntimeFixture(tmp_path / 'owner-a', dedicated=True)
    other = RuntimeFixture(tmp_path / 'owner-b', dedicated=True)
    original_caller = (fixture.project / 'CMakeLists.txt').read_text()
    proof = {}
    different = other.payload / 'bin/codex-app-server'
    different.write_bytes(different.read_bytes() + b'# Independent valid selected owner B.\n')
    other.archive = hashlib.sha256(b'Independent distinct valid B archive fixture.').hexdigest()
    other.refresh_manifest()
    proof['a_bytes'] = (fixture.payload / 'bin/codex-app-server').read_bytes()
    proof['b_bytes'] = different.read_bytes()
    assert proof['a_bytes'] != proof['b_bytes'], (
        'The two independently authored valid payload owners are meaningfully different'
    )
    _successful(fixture.configure('prove-valid-selected-owner-a'))
    proof['published_a'] = fixture.publication()
    proof['a_before'] = _inventory(proof['published_a'])
    selected_parent = fixture.root / 'actual-selected-manifest-a'
    (selected_parent / 'child').mkdir(parents=True)
    selected_a = selected_parent / 'input.json'
    selected_a.write_bytes(fixture.manifest.read_bytes())
    competing_b = fixture.project / 'input.json'
    competing_b.write_bytes(other.manifest.read_bytes())
    assert stat.S_ISREG(selected_a.lstat().st_mode) and stat.S_ISREG(competing_b.lstat().st_mode)
    selector = fixture.project / 'selector'
    selector.symlink_to((selected_parent / 'child'), target_is_directory=True)
    refs = (
        selected_parent,
        competing_b,
        selector,
        fixture.project / 'nonexistent_component',
        other.payload,
        other.manifest,
        other.legal,
        other.project / 'tools/assistant-runtime/edi-app-server.patch',
    )
    _original_runtime_select_literal_manifest(fixture, original_caller, str(competing_b))
    _successful(fixture.configure('prove-competing-owner-b-is-valid', known_paths=refs))
    proof['published_b'] = fixture.publication()
    proof['b_before'] = _inventory(proof['published_b'])
    assert (
        proof['published_a'] != proof['published_b']
        and (proof['published_b'] / 'bin/codex-app-server').read_bytes() == proof['b_bytes']
        and _inventory(proof['published_a']) == proof['a_before']
    ), (
        'The lexically competing manifest really passes all ordinary dedicated '
        'metadata/patch/legal/hash rules and publishes B, preserving A; a malformed '
        'alternative cannot fake the selector discriminator'
    )
    component = 'selector' if selection == 'symlink_parent' else 'nonexistent_component'
    suffix = component + '/../input.json'
    selected_path = fixture.project / component / '..' / 'input.json'
    spelling = suffix if form == 'relative' else str(selected_path)
    assert spelling.endswith(suffix), (
        'Neither Python nor the fixture collapses the '
        'original caller spelling before CMake receives it'
    )
    if selection == 'symlink_parent':
        assert (
            selector.is_symlink()
            and selector.readlink() == (selected_parent / 'child')
            and selected_path.samefile(selected_a)
            and selected_path.read_bytes() == selected_a.read_bytes()
        ), (
            'The real filesystem resolves the parent symlink then dot-dot to regular'
            ' manifest A; no terminal symlink or inferred path identity is admitted'
        )
    else:
        assert not (fixture.project / component).exists()
        with pytest.raises(FileNotFoundError):
            selected_path.read_bytes()
    _original_runtime_select_literal_manifest(fixture, original_caller, spelling)
    observed = fixture.configure(
        'literal-' + form + '-' + selection,
        known_paths=(*refs, proof['published_a'], proof['published_b']),
    )
    if selection == 'symlink_parent':
        _successful(observed)
        assert (
            fixture.publication() == proof['published_a']
            and (fixture.publication() / 'bin/codex-app-server').read_bytes() == proof['a_bytes']
        ), (
            'The original literal relative/absolute selection opens regular manifest'
            ' A, not the different valid B that lexical selector-dot-dot collapse '
            'would silently approve'
        )
    else:
        _refused(observed)
    assert (
        _inventory(proof['published_a']) == proof['a_before']
        and _inventory(proof['published_b']) == proof['b_before']
    ), (
        'Selecting or refusing a literal manifest spelling cannot modify either '
        'previously published owner or its complete immutable reader tree'
    )
    (fixture.root / 'LITERAL-SELECTION.json').write_text(
        json.dumps(
            {
                'form': form,
                'selection': selection,
                'literal': spelling,
                'filesystem_expected': 'A' if selection == 'symlink_parent' else 'ENOENT',
                'regular_a': str(selected_a),
                'different_valid_b': str(competing_b),
                'published_a': str(proof['published_a']),
                'published_b': str(proof['published_b']),
                'a_input_sha256': _digest(selected_a),
                'b_input_sha256': _digest(competing_b),
                'qualification': (
                    'Original actual file-open semantics, not lexical resolve, '
                    'copied digest formula or source-mirroring accepted output. No '
                    'terminal link acceptance; all original200 terminal-link '
                    'refusals remain.'
                ),
            },
            indent=2,
        )
    )


@pytest.mark.parametrize(
    ('kind', 'execution', 'expected'),
    [
        ('complete', (0, True, True, True, None), (True, False)),
        ('ordinary-reader-error-returned', (1, True, True, True, 'module'), (False, True)),
        ('fatal-owner-error', (1, False, False, True, 'module'), (False, True)),
        ('setup-before-owner', (1, False, False, False, 'module'), (False, False)),
        ('outer-caller-error', (1, True, True, True, 'caller'), (False, False)),
        ('contradictory-success-error', (0, True, True, True, 'module'), (False, False)),
        ('signal-termination', (-9, True, True, True, 'module'), (False, False)),
        ('missing-positive-marker', (0, False, True, True, None), (False, False)),
    ],
)
def test_original_configure_disposition_keeps_return_and_entered_failure_distinct(
    tmp_path, kind, execution, expected
):
    """Pure evidence classifier controls; no synthetic CMake execution is claimed."""
    code, marker, resumes, entered, error_owner = execution
    accepted, refused = expected
    module = tmp_path / 'runtime.cmake'
    caller = tmp_path / 'CMakeLists.txt'
    path = tmp_path / 'accepted'
    trace = [{'cmd': 'edi_bundle_assistant_runtime', 'file': str(caller), 'frame': 1}]
    if entered:
        trace.append({
            'cmd': 'file',
            'file': str(module),
            'frame': 2,
            'args': ['READ', 'missing-input', 'input'],
        })
    if resumes:
        trace.append({
            'cmd': 'file',
            'file': str(caller),
            'frame': 1,
            'args': ['WRITE', str(path), 'original function returned'],
        })
    error = ''
    if error_owner is not None:
        owner = module if error_owner == 'module' else caller
        error = f'CMake Error at {owner}:25 (file):\n  explicit controlled diagnostic\n'
    run = subprocess.CompletedProcess(['cmake'], code, stdout='', stderr=error)
    proof = _runtime_configure_outcome(run, marker, trace, module, caller, path)
    assert proof['return_marker_present'] is marker, (
        f'{kind}: the raw return-marker fact must not be renamed configure acceptance'
    )
    assert proof['caller_return_observed'] is resumes, (
        f'{kind}: actual outer WRITE trace remains separate from physical marker presence'
    )
    assert proof['runtime_entered'] is entered, (
        f'{kind}: refusal cannot be credited before the original owner is entered'
    )
    assert proof['configure_accepted'] is accepted, (
        f'{kind}: acceptance requires exit zero, positive completion, and no CMake error'
    )
    assert proof['runtime_refused'] is refused, (
        f'{kind}: only positive failed exit with an entered owned error proves refusal'
    )
