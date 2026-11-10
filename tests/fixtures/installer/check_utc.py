# SPDX-License-Identifier: BSD-3-Clause
"""Compile the shared production UTC conversion used by projects and reports."""

import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_project_and_report_utc_conversion_is_portable(tmp_path):
    (tmp_path / 'CMakeLists.txt').write_text(
        'cmake_minimum_required(VERSION 3.26)\nproject(utc_fixture LANGUAGES CXX)\n'
        'add_executable(utc main.cpp)\ntarget_compile_features(utc PRIVATE cxx_std_17)\n'
        f'target_include_directories(utc PRIVATE "{(ROOT / "core/src").as_posix()}")\n'
        'if(MSVC)\ntarget_compile_options(utc PRIVATE /EHsc)\nendif()\n'
    )
    (tmp_path / 'main.cpp').write_text(
        r"""
#include "utc_time.hpp"
#include <array>
#include <limits>
#include <string>
int main() {
    using namespace edi::detail;
    const std::array<std::pair<std::time_t, const char*>, 4> cases{{
        {0, "01 Jan 1970 00:00:00"},
        {951782399, "28 Feb 2000 23:59:59"},
        {951782400, "29 Feb 2000 00:00:00"},
        {2147483648LL, "19 Jan 2038 03:14:08"}
    }};
    for (const auto& [seconds, stamp] : cases) {
        const auto calendar = utc_calendar(seconds);
        const auto back = utc_seconds(calendar);
        if (!back || *back != seconds) return 1;
        char text[32];
        std::strftime(text, sizeof(text), "%d %b %Y %H:%M:%S", &calendar);
        if (std::string(text) != stamp) return 2;
    }
    const auto epoch = utc_calendar(0);
    char iso[32];
    std::strftime(iso, sizeof(iso), "%Y-%m-%dT%H:%M:%SZ", &epoch);
    if (std::string(iso) != "1970-01-01T00:00:00Z") return 3;
    try { utc_calendar(std::numeric_limits<std::time_t>::max()); }
    catch (const std::runtime_error&) { return 0; }
    return 4;
}
""",
        encoding='utf-8',
    )
    cmake = shutil.which('cmake')
    assert cmake, 'The declared CMake build tool is missing'
    build = tmp_path / 'build'
    subprocess.run(
        [cmake, '-G', 'Ninja', '-S', str(tmp_path), '-B', str(build)],
        check=True,
        timeout=30,
    )
    subprocess.run(
        [cmake, '--build', str(build), '--parallel', '4'],
        check=True,
        timeout=30,
    )
    executable = build / ('utc.exe' if os.name == 'nt' else 'utc')
    for timezone in ['UTC0', 'PST8PDT', 'JST-9']:
        subprocess.run(
            [str(executable)],
            env={**os.environ, 'TZ': timezone},
            check=True,
            capture_output=True,
            timeout=10,
        )
