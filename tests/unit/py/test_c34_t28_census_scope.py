"""Independent Clang controls for namespace model versus function-local scopes."""

import shutil
import subprocess

import pytest

from tests.fixtures.c34_t28_baseline import census_reference as reference

REPO = 'edi'
LOCALS = {
    'function': 'inline void helper() { LOCAL_TYPES }',
    'method': 'struct Runner { static void work() { LOCAL_TYPES } };',
    'lambda': 'inline void helper() { auto callback = [] { LOCAL_TYPES }; }',
    'nested-block': 'inline void helper() { if (true) { LOCAL_TYPES } }',
}


@pytest.mark.parametrize('channel', LOCALS)
def test_independent_census_distinguishes_local_and_model_scopes(tmp_path, channel):
    compiler = shutil.which('clang++')
    assert compiler, 'The independent scope control requires an installed Clang'
    local = 'struct Shadow { int phantom; }; struct Local { int scratch; };'
    text = (
        f'namespace {REPO} {{ '
        'struct Shadow { int kept; }; '
        'struct Owner { int stored; private: struct Cell { int nested; }; }; '
        'namespace detail { struct DetailStored { int qualified; }; } '
        + LOCALS[channel].replace('LOCAL_TYPES', local)
        + ' }'
    )
    source = tmp_path / 'scope.cpp'
    source.write_text(text)
    result = subprocess.run(
        [
            compiler,
            '-std=c++20',
            '-fsyntax-only',
            '-Xclang',
            '-ast-dump',
            '-Xclang',
            '-ast-dump-filter=' + REPO,
            str(source),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert result.returncode == 0, 'Every local scope escape must compile as ordinary C++'
    rows = reference.members(result.stdout, REPO, reference.declarations(text))
    actual = {(row['owner'], row['member'], row['type']) for row in rows}
    assert actual == {
        (REPO + '::Shadow', 'kept', 'int'),
        (REPO + '::Owner', 'stored', 'int'),
        (REPO + '::Owner::Cell', 'nested', 'int'),
        (REPO + '::detail::DetailStored', 'qualified', 'int'),
    }, (
        'Function, method, lambda and nested-block locals cannot impersonate a model '
        'even when they shadow its name; named nested records '
        'and private fields remain inventoried'
    )
