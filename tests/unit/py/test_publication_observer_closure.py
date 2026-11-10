"""A static library or overload cannot silently evade the physical-publication observer."""

from pathlib import Path

import pytest

from tests.fixtures.project_transactions import build

COPY = '_ZNSt10filesystem4copyERKNS_7__cxx114pathES3_NS_12copy_optionsERSt10error_code'
FILE = '_ZNSt10filesystem9copy_fileERKNS_7__cxx114pathES3_NS_12copy_optionsERSt10error_code'
LINK = '_ZNSt10filesystem16create_hard_linkERKNS_7__cxx114pathES3_RSt10error_code'
RENAME = '_ZNSt10filesystem6renameERKNS_7__cxx114pathES3_RSt10error_code'


def instrument(monkeypatch, tmp_path, imports, trace=None):
    native, output = tmp_path / 'native', tmp_path / 'output'
    native.mkdir()
    output.mkdir()
    archives = {}
    for name in imports:
        path = native / name
        path.write_bytes(b'independent static input\n')
        archives[path] = imports[name]
    delegates = {
        'publication_copy': COPY,
        'publication_copy_file': FILE,
        'publication_rename': RENAME,
        'publication_hard_link': LINK,
    }
    calls = []

    def run(command, **_kwargs):
        if '--disassemble-symbols=' in ' '.join(command):
            symbol = next(
                x.partition('=')[2] for x in command if x.startswith('--disassemble-symbols=')
            )
            return delegates[symbol.lstrip('_')] if trace is None else trace
        if '--undefined-only' in command:
            return archives[Path(command[-1])]
        raise AssertionError('The observer uses only its declared typed and archive probes')

    monkeypatch.setattr(build, 'run', run)
    monkeypatch.setattr(build.subprocess, 'run', lambda command, **_kwargs: calls.append(command))
    return native, output, calls


def test_every_relative_and_absolute_static_input_is_observed(monkeypatch, tmp_path):
    native, output, calls = instrument(
        monkeypatch,
        tmp_path,
        {'app.a': ' U ' + FILE, 'sdk.a': ' U ' + COPY + '\n U ' + RENAME + '\n U ' + LINK},
    )
    command = ['c++', 'app.a', str(native / 'sdk.a')]
    rewritten, originals, names = build.observe_publication_files(
        tmp_path, command, output, tmp_path / 'probe.o', native
    )
    assert set(originals) == {str(native / 'app.a'), str(native / 'sdk.a')}, (
        'Every linked static input retains its original identity, including relative paths'
    )
    assert all(Path(path).parent == output for path in rewritten[1:]), (
        'Every affected archive is replaced by an observed private copy'
    )
    assert set(names) == {COPY, FILE, RENAME, LINK} and len(calls) == 2, (
        'Recursive copy, file copy, hard link and rename all reach typed observers'
    )


@pytest.mark.parametrize('escape', ['missing', 'overload', 'no-import'])
def test_unprovable_publication_imports_refuse_without_a_receipt(monkeypatch, tmp_path, escape):
    imports = {
        'app.a': ' U '
        + (FILE if escape == 'missing' else FILE + 'new' if escape == 'overload' else '')
    }
    native, output, _ = instrument(monkeypatch, tmp_path, imports)
    command = ['c++', 'absent.a' if escape == 'missing' else 'app.a']
    with pytest.raises(RuntimeError, match=r'(absent|overload|real linked)'):
        build.observe_publication_files(tmp_path, command, output, tmp_path / 'probe.o', native)
    assert (native / 'app.a').read_bytes() == b'independent static input\n', (
        'A refused instrumentation attempt never patches the real linked archive'
    )


def test_two_possible_delegate_imports_refuse_ambiguous_binding(monkeypatch, tmp_path):
    native, output, _ = instrument(
        monkeypatch, tmp_path, {'app.a': ' U ' + FILE}, trace=COPY + '\n' + COPY + 'new'
    )
    with pytest.raises(RuntimeError, match='compiler-typed delegate'):
        build.observe_publication_files(
            tmp_path, ['c++', 'app.a'], output, tmp_path / 'probe.o', native
        )
