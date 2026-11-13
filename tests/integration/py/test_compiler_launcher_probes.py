"""Real compiler probes must retain launcher policy inside nested CMake projects."""

from pathlib import Path

import pytest

from tests.fixtures.compiler_launcher import run_compiler_probe

ROOT = Path(__file__).resolve().parents[3]
LANGUAGES = ('C', 'CXX')


@pytest.mark.parametrize('selection', ['default', 'empty', 'absolute', 'list'])
def test_real_initial_and_explicit_nested_compiler_probes_preserve_launcher_policy(
    tmp_path, selection
):
    configured, tree, program, definitions = run_compiler_probe(
        tmp_path,
        (ROOT / 'CMakeLists.txt').read_text(),
        LANGUAGES,
        selection,
    )
    assert configured.returncode == 0, (
        'Actual compiler initialization and nested probes preserve the selected launcher'
    )
    for language in LANGUAGES:
        expected = definitions.get(language, program.as_posix())
        assert (tree / (language + '.launcher')).read_text() == expected, (
            'The root compiler project retains its exact effective launcher selection'
        )
        assert (tree / (language + '.environment')).read_text() == 'ccache', (
            'Launcher propagation retains the unchanged caller environment'
        )
        assert (tree / ('nested-' + language)).is_dir(), (
            'Every declared language reaches its explicit nested native compiler project'
        )
        children = list((tree / ('nested-' + language)).rglob('CMakeCache.txt'))
        assert any(
            'USER_PROBE_WITNESS:UNINITIALIZED=retained-toolchain-value' in child.read_text()
            for child in children
        ), 'Nested compiler children retain unrelated caller platform variables'
    log = tmp_path / 'cache.log'
    if selection == 'empty':
        assert not log.exists(), (
            'Explicit empty launcher prevents cache execution in every compiler child'
        )
    else:
        trace = log.read_text()
        assert 'TryCompile-' in trace, (
            'The actual cache forwards compiler checks during project initialization'
        )
        for language in LANGUAGES:
            assert 'nested-' + language in trace, (
                'The actual cache forwards every explicit nested compiler invocation'
            )
