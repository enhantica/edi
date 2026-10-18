"""Exercise the parsed index helper with the destination width of WebAssembly."""

import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope='module')
def index32_probe(tmp_path_factory):
    directory = tmp_path_factory.mktemp('report-index32')
    text = (ROOT / 'core/src/report_json.cpp').read_text()
    match = re.search(r'std::size_t index_of\([^\n]*\)\s*\{.*?^\}', text, re.MULTILINE | re.DOTALL)
    assert match is not None, 'The width witness reaches the actual parsed-index boundary function'
    # Substitute only the destination type, preserving every production guard and cast.
    function = match[0].replace('std::size_t', 'std::uint32_t')
    driver = directory / 'probe.cpp'
    driver.write_text(
        '#include <cmath>\n#include <limits>\n#include <cstdint>\n#include <cstdio>\n'
        '#include <cstdlib>\n#include <stdexcept>\n#include "json.hpp"\n'
        'using edi::json::Value;\n' + function + '\n'
        'int main(int argc,char** argv) { if(argc != 2) return 3;\n'
        'const Value value = std::string(argv[1]) == "null" ? Value{} '
        ': Value(std::strtod(argv[1],nullptr));\n'
        'try { const auto result=index_of(value,"index"); '
        'std::printf("accepted %u\\n",result); }\n'
        'catch(const std::invalid_argument&) { std::puts("refused"); } }\n'
    )
    executable = directory / 'probe'
    compiler = shutil.which('x86_64-conda-linux-gnu-c++') or shutil.which('c++')
    assert compiler, 'The pinned runner supplies the compiler for the destination-width witness'
    result = subprocess.run(
        [
            compiler,
            '-std=c++20',
            '-O1',
            '-fsanitize=float-cast-overflow',
            '-fno-sanitize-recover=float-cast-overflow',
            '-I',
            str(ROOT / 'core/src'),
            str(driver),
            str(ROOT / 'core/src/json.cpp'),
            '-o',
            str(executable),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert result.returncode == 0, (
        'The unchanged production helper compiles with a uint32_t destination: ' + result.stderr
    )
    return executable


@pytest.mark.parametrize(
    'value', ['null', '1.25', '-2', '4294967296', '9007199254740992', '1e300']
)
def test_report_index_refuses_before_a_32_bit_destination_cast(index32_probe, value):
    result = subprocess.run(
        [str(index32_probe), value], capture_output=True, text=True, check=False, timeout=5
    )
    assert result.returncode == 0 and result.stdout.strip() == 'refused', (
        'The actual parsed-index guard refuses invalid values before its 32-bit destination '
        f'cast, with sanitizer control; input={value}, actual={result.stdout + result.stderr}'
    )


@pytest.mark.parametrize('value', ['0', '7', '4294967295'])
def test_report_index_accepts_the_32_bit_endpoints_and_nonzero_control(index32_probe, value):
    result = subprocess.run(
        [str(index32_probe), value], capture_output=True, text=True, check=False, timeout=5
    )
    assert result.returncode == 0 and result.stdout.strip() == 'accepted ' + value, (
        'The destination-width observer retains every valid endpoint and nontrivial index'
    )
