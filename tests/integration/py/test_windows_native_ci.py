"""All native hosts cross the same producer, test and artifact-consumer boundaries."""

import copy
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
PLATFORMS = {
    'Linux': ('ubuntu-24.04', 'linux-64'),
    'macOS': ('macos-15', 'osx-arm64'),
    'Windows': ('windows-2022', 'win-64'),
}


def boundary(jobs):
    for name in ('native', 'core', 'cli-python'):
        job = jobs[name]
        rows = job['strategy']['matrix']['include']
        assert len(rows) == 3
        assert {r['platform']: (r['runner'], r['sdk']) for r in rows} == PLATFORMS
        assert job['defaults']['run']['shell'] == 'bash'
        steps = job['steps']
        sdk = [s for s in steps if s.get('uses') == './.github/actions/crysta-sdk']
        assert len(sdk) == 1 and sdk[0]['with']['platform'] == '${{ matrix.sdk }}'
        if name != 'native':
            native = [s for s in steps if s.get('uses') == './.github/actions/edi-native']
            assert len(native) == 1 and native[0]['with']['platform'] == '${{ matrix.sdk }}'
        assert any(s.get('uses') == 'ilammy/msvc-dev-cmd@v1' for s in steps)
        assert any(s.get('run') == 'pixi run core-build' for s in steps)
        assert not any(s.get('continue-on-error') for s in steps)
    producer = jobs['native']
    assert any(s.get('run') == 'pixi run --skip-deps cpp-test' for s in producer['steps'])
    assert any(s.get('run') == 'pixi run --skip-deps cli-stream-parity' for s in producer['steps'])
    saves = [s for s in producer['steps'] if s.get('uses') == 'actions/cache/save@v4']
    assert len(saves) == 1 and '!cancelled()' in saves[0]['if']
    assert 'success()' not in saves[0]['if']


def jobs():
    return yaml.safe_load((ROOT / '.github/workflows/ci.yml').read_text())['jobs']


def test_all_three_hosts_share_the_native_qualification_path():
    boundary(jobs())


@pytest.mark.parametrize('name', ['native', 'core', 'cli-python'])
@pytest.mark.parametrize('damage', ['omitted', 'foreign-sdk', 'foreign-runner'])
def test_native_platform_omission_or_sibling_sdk_cannot_pass(name, damage):
    changed = copy.deepcopy(jobs())
    rows = changed[name]['strategy']['matrix']['include']
    win = next(r for r in rows if r['platform'] == 'Windows')
    if damage == 'omitted':
        rows.remove(win)
    elif damage == 'foreign-sdk':
        win['sdk'] = 'linux-64'
    else:
        win['runner'] = 'ubuntu-24.04'
    with pytest.raises(AssertionError):
        boundary(changed)


def test_windows_checkout_uses_the_existing_installer_reserved_path_policy():
    def windows_checkout(steps):
        return next(
            s for s in steps if s.get('name') == 'Check out Windows-compatible source paths'
        )

    installer = yaml.safe_load((ROOT / '.github/workflows/installers.yml').read_text())['jobs']
    original = windows_checkout(installer['installers']['steps'])
    for name in ('native', 'core', 'cli-python'):
        actual = windows_checkout(jobs()[name]['steps'])
        assert actual['with'] == original['with']
        assert actual['if'] == original['if']


def sdk_include_boundary(relative, source):
    import re  # noqa: PLC0415 - one mechanical include boundary, no C++ execution

    shared = r'(?m)^\s*#\s*include\s*"windows_sdk.hpp"\s*$'
    for match in re.finditer(
        r'(?m)^\s*#\s*include\s*[<"](windows|winhttp|winsock2)\.h[>"]', source, re.IGNORECASE
    ):
        if relative == 'core/src/windows_sdk.hpp':
            continue
        assert re.search(shared, source[: match.start()]), (
            'Native Windows headers enter through the existing macro-sanitizing wrapper: '
            + relative
        )


def test_all_product_windows_sdk_imports_use_the_existing_sanitized_boundary():
    for folder in ('cli', 'core/src', 'app/src'):
        for path in (ROOT / folder).rglob('*'):
            if path.is_file() and path.suffix in {'.cpp', '.hpp', '.h'}:
                sdk_include_boundary(
                    path.relative_to(ROOT).as_posix(), path.read_text(encoding='utf-8')
                )


@pytest.mark.parametrize(
    'source',
    [
        '#include <windows.h>\n',
        '#include <Windows.h>\n',
        '// #include "windows_sdk.hpp"\n#include <windows.h>\n',
        '#include <winhttp.h>\n',
        '#include <winsock2.h>\n',
        '#include <windows.h>\n#include "windows_sdk.hpp"\n',
    ],
)
def test_unsanitized_windows_sdk_import_cannot_bypass_the_boundary(source):
    sdk_include_boundary('cli/positive.cpp', '#include "windows_sdk.hpp"\n#include <windows.h>\n')
    with pytest.raises(AssertionError, match='existing macro-sanitizing wrapper'):
        sdk_include_boundary('cli/counterfactual.cpp', source)
