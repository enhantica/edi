"""Default launcher lookup preserves explicit user choices and real native execution."""

from pathlib import Path

import pytest

from tests.fixtures.compiler_launcher import execute_lookup, run_lookup

ROOT = Path(__file__).resolve().parents[3]
LANGUAGES = ('C', 'CXX')


@pytest.mark.parametrize('language', LANGUAGES)
@pytest.mark.parametrize('selection', ['environment', 'explicit'])
def test_windows_default_cache_executes_by_absolute_path_without_child_path_lookup(
    tmp_path,
    language,
    selection,
):
    values = {language: 'custom-env-cache' if selection == 'explicit' else 'ccache'}
    definitions = {language: 'ccache'} if selection == 'explicit' else None
    result = run_lookup(
        tmp_path, (ROOT / 'CMakeLists.txt').read_text(), values, definitions=definitions
    )
    configured, observed, program, _tree, _ninja, _environment = result
    assert configured.returncode == 0, (
        'The pre-project default launcher resolves its locked executable'
    )
    executed = execute_lookup(result, language)
    assert executed.returncode == 0, (
        'Actual Ninja executes the selected native program without relying on the subprocess PATH'
    )
    assert 'launcher-lookup' in executed.stdout, (
        'The native executable probe reaches a selected path containing spaces'
    )
    assert observed[language] == program.as_posix(), (
        'The selected default launcher is the exact locked-prefix absolute executable path'
    )


@pytest.mark.parametrize('language', LANGUAGES)
def test_missing_default_cache_refuses_before_project_or_native_execution(tmp_path, language):
    configured, observed, *_unused = run_lookup(
        tmp_path,
        (ROOT / 'CMakeLists.txt').read_text(),
        {language: 'ccache'},
        present=False,
    )
    assert configured.returncode != 0, (
        'A selected missing default cache launcher refuses configuration'
    )
    assert not observed, 'A missing required launcher is rejected before the project starts'


@pytest.mark.parametrize('language', LANGUAGES)
@pytest.mark.parametrize(
    'choice',
    [
        '',
        'custom-cache',
        '/custom path/ccache',
        'ccache;--custom-argument',
        'ccache.exe',
        'CCACHE',
    ],
)
@pytest.mark.parametrize('selection', ['environment', 'explicit'])
def test_empty_custom_absolute_and_list_launchers_remain_exact_user_choices(
    tmp_path,
    language,
    choice,
    selection,
):
    values = {language: 'ccache'} if selection == 'explicit' else {language: choice}
    definitions = {language: choice} if selection == 'explicit' else None
    configured, observed, *_unused = run_lookup(
        tmp_path,
        (ROOT / 'CMakeLists.txt').read_text(),
        values,
        definitions=definitions,
        present=False,
    )
    assert configured.returncode == 0, (
        'Opt-out and custom launchers do not require an unrelated cache executable'
    )
    assert observed[language] == choice, (
        'User launcher precedence preserves empty absolute custom and argument-list values exactly'
    )


@pytest.mark.parametrize('language', LANGUAGES)
def test_unix_cache_defaults_are_preserved_without_windows_prefix_lookup(tmp_path, language):
    configured, observed, *_unused = run_lookup(
        tmp_path,
        (ROOT / 'CMakeLists.txt').read_text(),
        {language: 'ccache'},
        windows=False,
        present=False,
    )
    assert configured.returncode == 0, (
        'Unix default cache policy does not require a Windows executable'
    )
    assert observed[language] == 'ccache', (
        'The original Unix cache launcher selection remains unchanged'
    )


def test_unused_language_does_not_force_an_unrelated_cache_dependency(tmp_path):
    inactive = {'C'} - set(LANGUAGES)
    if inactive:
        configured, observed, *_unused = run_lookup(
            tmp_path,
            (ROOT / 'CMakeLists.txt').read_text(),
            {'C': 'ccache'},
            present=False,
        )
        assert configured.returncode == 0, (
            'A CXX-only project cannot require a missing cache for its unused C language'
        )
        assert not observed['CXX'], 'An explicit CXX cache opt-out survives an unused C default'
    else:
        configured, _observed, *_unused = run_lookup(
            tmp_path,
            (ROOT / 'CMakeLists.txt').read_text(),
            {'C': 'ccache'},
            present=False,
        )
        assert configured.returncode != 0, (
            'A project that enables C actually validates its selected C cache launcher'
        )
