"""Real compiler probes must retain launcher policy inside nested CMake projects."""

import re
from pathlib import Path

import pytest

from tests.fixtures.compiler_launcher import run_compiler_probe

ROOT = Path(__file__).resolve().parents[3]
LANGUAGES = ('C', 'CXX')
SELECTIONS = ('default', 'empty', 'absolute', 'list')


@pytest.fixture(scope='module')
def compiler_probes(tmp_path_factory):
    """Each real build serves independent configuration and execution observations.

    The instrumented runtime bank records this shared compiler/bootstrap cost in
    the module row. No compiler check, ABI probe, link or launcher invocation is skipped.
    """
    source = (ROOT / 'CMakeLists.txt').read_text()
    return {
        selection: run_compiler_probe(
            tmp_path_factory.mktemp('compiler-' + selection), source, LANGUAGES, selection
        )
        for selection in SELECTIONS
    }


@pytest.mark.parametrize('selection', SELECTIONS)
@pytest.mark.parametrize('language', LANGUAGES)
def test_real_initial_and_nested_compiler_configuration_preserves_launcher_policy(
    compiler_probes, selection, language
):
    configured, tree, program, definitions = compiler_probes[selection]
    assert configured.returncode == 0, (
        'Actual compiler initialization and nested probes preserve the selected launcher'
    )
    expected = definitions.get(language, program.as_posix())
    assert (tree / (language + '.launcher')).read_text() == expected, (
        'The root compiler project retains its exact effective launcher selection'
    )
    assert (tree / (language + '.environment')).read_text() == 'ccache', (
        'Launcher propagation retains the unchanged caller environment'
    )
    assert (tree / 'nested-native').is_dir(), (
        'Every declared language reaches its explicit nested native compiler project'
    )
    children = list((tree / 'nested-native').rglob('CMakeCache.txt'))
    assert any(
        'USER_PROBE_WITNESS:UNINITIALIZED=retained-toolchain-value' in child.read_text()
        for child in children
    ), 'Nested compiler children retain unrelated caller platform variables'


@pytest.mark.parametrize('selection', SELECTIONS)
@pytest.mark.parametrize('language', LANGUAGES)
def test_actual_nested_compiler_execution_uses_the_selected_cache_policy(
    compiler_probes, selection, language
):
    configured, tree, _program, _definitions = compiler_probes[selection]
    assert configured.returncode == 0, 'Execution evidence requires successful real compilation'
    log = tree.parent / 'cache.log'
    if selection == 'empty':
        assert not log.exists(), (
            'Explicit empty launcher prevents cache execution in every compiler child'
        )
        return
    trace = log.read_text()
    assert 'TryCompile-' in trace, (
        'The actual cache forwards compiler checks during project initialization'
    )
    invocations = {}
    for line in trace.splitlines():
        record = re.match(r'\[[^]]+ (\d+)\] (.*)', line)
        if record:
            invocations.setdefault(record[1], []).append(record[2])
    suffix = 'c' if language == 'C' else 'cpp'
    assert any(
        any('Working directory:' in line and 'nested-native' in line for line in lines)
        and any(
            'Command line:' in line and re.search(r'probe\.' + suffix + r'(?:[.\s"]|$)', line)
            for line in lines
        )
        for lines in invocations.values()
    ), 'Each real cache process forwards its C or C++ source in the linked child project'
