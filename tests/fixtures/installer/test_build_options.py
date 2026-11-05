# SPDX-License-Identifier: BSD-3-Clause
"""Exercise production compiler policy against real SDK/standard-header interactions."""

import os
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope='module')
def build(tmp_path_factory):
    source = tmp_path_factory.mktemp('native-build-policy')
    (source / 'probe.cpp').write_text(
        '#include <algorithm>\n#include <chrono>\n#include <limits>\n'
        '#ifdef EDI_MODEL_FIRST\n#include <edi/fit_status.hpp>\n#endif\n'
        '#ifdef _WIN32\n#ifdef EDI_UNGUARDED_SDK\n#undef NOMINMAX\n#endif\n'
        '#if defined(EDI_UNGUARDED_SDK) || defined(EDI_RAW_SDK)\n'
        '#include <windows.h>\n#else\n#include "windows_sdk.hpp"\n#endif\n#endif\n'
        '#ifndef EDI_MODEL_FIRST\n#include <edi/fit_status.hpp>\n#endif\n'
        'int main() {\n'
        'if (std::min(2, 3) != 2 || std::max(2, 3) != 3) return 1;\n'
        'if (std::chrono::seconds::max().count() < std::numeric_limits<int>::max()) return 2;\n'
        'return edi::FitStatus::ERROR == edi::FitStatus::DONE ? 3 : 0; }\n',
        encoding='utf-8',
    )
    (source / 'CMakeLists.txt').write_text(
        'cmake_minimum_required(VERSION 3.26)\nproject(policy LANGUAGES CXX)\n'
        f'include("{(ROOT / "cmake/edi_build_options.cmake").as_posix()}")\n'
        f'include_directories("{(ROOT / "core/include").as_posix()}" '
        f'"{(ROOT / "core/src").as_posix()}")\n'
        'add_executable(guarded probe.cpp)\ntarget_compile_features(guarded PRIVATE cxx_std_20)\n'
        'add_executable(model_first probe.cpp)\n'
        'target_compile_features(model_first PRIVATE cxx_std_20)\n'
        'target_compile_definitions(model_first PRIVATE EDI_MODEL_FIRST)\n'
        'add_executable(unguarded EXCLUDE_FROM_ALL probe.cpp)\n'
        'target_compile_features(unguarded PRIVATE cxx_std_20)\n'
        'target_compile_definitions(unguarded PRIVATE EDI_UNGUARDED_SDK)\n'
        'add_executable(raw_after_model EXCLUDE_FROM_ALL probe.cpp)\n'
        'target_compile_features(raw_after_model PRIVATE cxx_std_20)\n'
        'target_compile_definitions(raw_after_model PRIVATE EDI_MODEL_FIRST EDI_RAW_SDK)\n',
        encoding='utf-8',
    )
    output = source / 'build'
    subprocess.run(
        ['cmake', '-G', 'Ninja', '-S', str(source), '-B', str(output)], check=True, timeout=30
    )
    return output


@pytest.mark.parametrize('target', ['guarded', 'model_first'])
def test_native_standard_calls_survive_dependency_sdk_headers(build, target):
    subprocess.run(
        ['cmake', '--build', str(build), '--target', target, '--parallel', '4'],
        check=True,
        timeout=30,
    )
    binary = build / (target + ('.exe' if os.name == 'nt' else ''))
    subprocess.run([str(binary)], check=True, timeout=5)


@pytest.mark.skipif(os.name != 'nt', reason='The escape uses the real Windows SDK')
@pytest.mark.parametrize('target', ['unguarded', 'raw_after_model'])
def test_unguarded_windows_sdk_is_rejected_by_the_same_probe(build, target):
    result = subprocess.run(
        ['cmake', '--build', str(build), '--target', target, '--parallel', '4'],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode != 0, 'The probe did not exercise Windows SDK macro pollution'


def test_product_windows_headers_use_the_shared_sdk_boundary():
    direct = re.compile(r'^\s*#\s*include\s*[<"]windows\.h[>"]', re.IGNORECASE | re.MULTILINE)
    actual = []
    for folder in ('app', 'core', 'assistant'):
        actual.extend(
            path.relative_to(ROOT).as_posix()
            for path in (ROOT / folder).rglob('*')
            if path.suffix in {'.cpp', '.hpp', '.h'}
            and direct.search(path.read_text(encoding='utf-8'))
        )
    assert actual == ['core/src/windows_sdk.hpp']


def test_linked_executable_keeps_the_generated_build_marker(tmp_path):
    marker = tmp_path / 'marker.cpp'
    commit = subprocess.check_output(
        ['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True
    ).strip()
    subprocess.run(
        [
            'cmake',
            f'-DSOURCE_DIR={ROOT}',
            f'-DOUT={marker}',
            '-DMARKER=ON',
            '-P',
            str(ROOT / 'cmake/build_commit.cmake'),
        ],
        check=True,
        timeout=15,
    )
    (tmp_path / 'main.cpp').write_text('int main() { return 0; }\n', encoding='utf-8')
    (tmp_path / 'CMakeLists.txt').write_text(
        'cmake_minimum_required(VERSION 3.26)\nproject(marker LANGUAGES CXX)\n'
        'add_executable(probe main.cpp marker.cpp)\n'
        'if(MSVC)\n  target_link_options(probe PRIVATE /OPT:REF)\n'
        'elseif(APPLE)\n  target_link_options(probe PRIVATE -Wl,-dead_strip)\n'
        'else()\n  target_link_options(probe PRIVATE -Wl,--gc-sections)\nendif()\n',
        encoding='utf-8',
    )
    output = tmp_path / 'build'
    subprocess.run(
        [
            'cmake',
            '-G',
            'Ninja',
            '-DCMAKE_BUILD_TYPE=Release',
            '-S',
            str(tmp_path),
            '-B',
            str(output),
        ],
        check=True,
        timeout=30,
    )
    subprocess.run(['cmake', '--build', str(output), '--parallel', '4'], check=True, timeout=30)
    binary = output / ('probe.exe' if os.name == 'nt' else 'probe')
    assert f'edi-build-commit:{commit}\n'.encode() in binary.read_bytes()
