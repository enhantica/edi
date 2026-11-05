# SPDX-License-Identifier: BSD-3-Clause
"""Exercise production compiler policy against real SDK/standard-header interactions."""

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope='module')
def build(tmp_path_factory):
    source = tmp_path_factory.mktemp('native-build-policy')
    (source / 'probe.cpp').write_text(
        '#include <algorithm>\n#include <chrono>\n#include <limits>\n'
        '#ifdef _WIN32\n#ifdef EDI_UNGUARDED_SDK\n#undef NOMINMAX\n#endif\n'
        '#include <windows.h>\n#endif\n'
        'int main() {\n'
        'if (std::min(2, 3) != 2 || std::max(2, 3) != 3) return 1;\n'
        'if (std::chrono::seconds::max().count() < std::numeric_limits<int>::max()) return 2;\n'
        'return 0; }\n',
        encoding='utf-8',
    )
    (source / 'CMakeLists.txt').write_text(
        'cmake_minimum_required(VERSION 3.26)\nproject(policy LANGUAGES CXX)\n'
        f'include("{(ROOT / "cmake/edi_build_options.cmake").as_posix()}")\n'
        'add_executable(guarded probe.cpp)\ntarget_compile_features(guarded PRIVATE cxx_std_20)\n'
        'add_executable(unguarded EXCLUDE_FROM_ALL probe.cpp)\n'
        'target_compile_features(unguarded PRIVATE cxx_std_20)\n'
        'target_compile_definitions(unguarded PRIVATE EDI_UNGUARDED_SDK)\n',
        encoding='utf-8',
    )
    output = source / 'build'
    subprocess.run(
        ['cmake', '-G', 'Ninja', '-S', str(source), '-B', str(output)], check=True, timeout=30
    )
    return output


def test_native_standard_calls_survive_dependency_sdk_headers(build):
    subprocess.run(
        ['cmake', '--build', str(build), '--target', 'guarded', '--parallel', '4'],
        check=True,
        timeout=30,
    )
    binary = build / ('guarded.exe' if os.name == 'nt' else 'guarded')
    subprocess.run([str(binary)], check=True, timeout=5)


@pytest.mark.skipif(os.name != 'nt', reason='The escape uses the real Windows SDK')
def test_unguarded_windows_sdk_is_rejected_by_the_same_probe(build):
    result = subprocess.run(
        ['cmake', '--build', str(build), '--target', 'unguarded', '--parallel', '4'],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode != 0, 'The probe did not exercise Windows SDK macro pollution'
