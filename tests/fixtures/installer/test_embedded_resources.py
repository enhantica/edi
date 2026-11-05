# SPDX-License-Identifier: BSD-3-Clause
"""Compile every production resource family with large UTF-8 input and compare bytes."""

import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
PALETTES = ['earth', 'classic', 'soft', 'natural', 'colour-blind-safe']
MAPS = ['viridis', 'batlow', 'inferno', 'lapaz', 'greys']
PAYLOAD = ('Å測定; quotes " and backslash \\; newline\n' * 1800).encode()


@pytest.fixture(scope='module')
def generated(tmp_path_factory):
    source = tmp_path_factory.mktemp('product-resources')
    shutil.copytree(ROOT / 'cmake', source / 'cmake')
    templates = source / 'core/src'
    templates.mkdir(parents=True)
    for path in (ROOT / 'core/src').glob('*_data.cpp.in'):
        shutil.copy2(path, templates / path.name)
    for path in (ROOT / 'core/src').glob('*.hpp'):
        shutil.copy2(path, templates / path.name)
    inputs = {
        'data/elements/element-styles.tsv': PAYLOAD + b'elements',
        'data/report/report.js': PAYLOAD + b'report',
        'data/assistant/openai-capabilities.json': PAYLOAD + b'capabilities',
        **{f'data/palettes/{name}.tsv': PAYLOAD + name.encode() for name in PALETTES},
        **{f'data/colormaps/{name}.tsv': PAYLOAD + name.encode() for name in MAPS},
    }
    skill = PAYLOAD + b'skill'
    digest = hashlib.sha256(skill).hexdigest()
    index = json.dumps(
        {
            'padding': PAYLOAD.decode(),
            'skills': [{'id': 'fixture', 'path': 'fixture/SKILL.md', 'sha256': digest}],
        },
        ensure_ascii=False,
    ).encode()
    inputs['data/assistant/skills/index.json'] = index
    inputs['data/assistant/skills/fixture/SKILL.md'] = skill
    for name, data in inputs.items():
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    expressions = [
        'edi::detail::kElementStylesTsv',
        'edi::detail::kReportJs',
        *[f'edi::detail::kPaletteTsv[{i}]' for i in range(len(PALETTES))],
        *[f'edi::detail::kColourMapTsvs[{i}]' for i in range(len(MAPS))],
        'edi::assistant::detail::openai_capabilities_data()',
        'edi::assistant::detail::skill_index_data()',
        'edi::assistant::detail::skill_resource_data()[0].id',
        'edi::assistant::detail::skill_resource_data()[0].sha256',
        'edi::assistant::detail::skill_resource_data()[0].content',
    ]
    expected = [
        inputs['data/elements/element-styles.tsv'],
        inputs['data/report/report.js'],
        *[inputs[f'data/palettes/{name}.tsv'] for name in PALETTES],
        *[inputs[f'data/colormaps/{name}.tsv'] for name in MAPS],
        inputs['data/assistant/openai-capabilities.json'],
        index,
        b'fixture',
        digest.encode(),
        skill,
    ]
    cases = '\n'.join(f'case {i}: value = {value}; break;' for i, value in enumerate(expressions))
    (source / 'main.cpp').write_text(
        '#include "assistant_skill_resources.hpp"\n#include <iostream>\n#include <cstdlib>\n'
        '#ifdef _WIN32\n#include <fcntl.h>\n#include <io.h>\n#endif\n'
        'namespace edi::detail {\nextern const char* const kElementStylesTsv;\n'
        'extern const char* const kReportJs;\nextern const char* const kPaletteTsv[];\n'
        'extern const char* const kColourMapTsvs[];\n}\n'
        'namespace edi::assistant::detail { std::string_view openai_capabilities_data(); }\n'
        'int main(int argc, char** argv) {\n'
        '#ifdef _WIN32\n_setmode(_fileno(stdout), _O_BINARY);\n#endif\n'
        'if(argc != 2) return 1;\n'
        'if(edi::assistant::detail::skill_resource_data().data() != '
        'edi::assistant::detail::skill_resource_data().data()) return 2;\n'
        'std::string_view value;\nswitch(std::atoi(argv[1])) {\n'
        + cases
        + '\ndefault: return 3; }\nstd::cout.write(value.data(), value.size()); return 0; }\n',
        encoding='utf-8',
    )
    (source / 'CMakeLists.txt').write_text(
        'cmake_minimum_required(VERSION 3.26)\nproject(resources LANGUAGES CXX)\n'
        'include(cmake/edi_core_sources.cmake)\nedi_core_sources("${CMAKE_SOURCE_DIR}" sources)\n'
        'file(GLOB EDI_EMBEDDED_FILES "${CMAKE_BINARY_DIR}/*_data.cpp")\n'
        'add_executable(runner main.cpp ${EDI_EMBEDDED_FILES})\n'
        'target_compile_features(runner PRIVATE cxx_std_20)\n'
        'target_include_directories(runner PRIVATE core/src)\n'
        'if(MSVC)\ntarget_compile_options(runner PRIVATE /utf-8 /EHsc /bigobj)\nendif()\n',
        encoding='utf-8',
    )
    build = source / 'build'
    subprocess.run(
        ['cmake', '-G', 'Ninja', '-S', str(source), '-B', str(build)], check=True, timeout=30
    )
    return build, expected


def test_all_generated_resources_avoid_oversized_string_literals(generated):
    build, _ = generated
    for path in build.glob('*_data.cpp'):
        text = path.read_text(encoding='utf-8')
        assert max(map(len, text.splitlines()), default=0) <= 8000, path.name
        matches = re.findall(r'R"([^ ()\\\t\r\n]{0,16})\((.*?)\)\1"', text, re.DOTALL)
        assert all(len(content.encode()) <= 8000 for _, content in matches), path.name


def test_all_resource_families_keep_exact_bytes_after_native_compilation(generated):
    build, expected = generated
    subprocess.run(['cmake', '--build', str(build), '--parallel', '4'], check=True, timeout=30)
    executable = build / ('runner.exe' if (build / 'runner.exe').is_file() else 'runner')
    for index, data in enumerate(expected):
        result = subprocess.run(
            [str(executable), str(index)], capture_output=True, check=True, timeout=5
        )
        assert result.stdout == data, index
