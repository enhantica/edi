"""file-plane assignment cannot bypass constructor admission.

The private Loop lives in io.cpp. Compile that real translation unit without
linking or copying its declaration; C++ type traits prove the deleted operations.
This is a system gate: the compiler consumes the entire production I/O translation
unit and proves the native caller contract end to end.
The oracle is the immutable-value contract in ADR-0016, not product output.
"""

import os
import shlex
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_private_loop_whole_object_assignment_is_unspellable():
    source = r"""#include "core/src/io.cpp"
#include <type_traits>
static_assert(!std::is_copy_assignable_v<edi::Loop>,
              " immutable file loops prohibit whole-object copy assignment");
static_assert(!std::is_move_assignable_v<edi::Loop>,
              " immutable file loops prohibit whole-object move assignment");
"""
    # I26 makes crysta's public headers a dependency of edi/model.hpp. Use
    # the same prepared SDK include root as the native consumer build.
    sdk = Path(os.environ.get('CRYSTA_SDK_DIR', ROOT / 'build/crysta-prefix'))
    assert (sdk / 'include/crysta/anchors.hpp').is_file(), (
        ' the prepared crysta SDK is needed to reach the immutable-loop assertions'
    )
    result = subprocess.run(
        [
            *shlex.split(os.environ.get('CXX', 'c++')),
            '-std=c++20',
            '-fsyntax-only',
            '-x',
            'c++',
            '-I.',
            '-Icore/include',
            '-I' + str(sdk / 'include'),
            '-',
        ],
        input=source,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=25,
    )
    assert result.returncode == 0, (
        ' admitted edi file loops must make both whole-object assignments unspellable: '
        + result.stderr
    )
