"""Test-only access macros must not rewrite installed SDK declarations."""

import re
import subprocess
from pathlib import Path

import pytest

from tests.fixtures.removed_absorption.surfaces import CPP_DATA

ROOT = Path(__file__).resolve().parents[3]


def require_sdk_access_identity(source):
    source = re.sub(r'\\\r?\n', '', source)
    if not re.search(r'#\s*define\s+(?:private|protected|public)\b', source):
        return

    def keep_include_operand(match):
        start = source.rfind('\n', 0, match.start()) + 1
        prefix = source[start : match.start()]
        if match[0].startswith('"') and re.fullmatch(r'\s*#\s*include\s+', prefix):
            return match[0]
        return ''.join('\n' if char == '\n' else ' ' for char in match[0])

    code = CPP_DATA.sub(keep_include_operand, source)
    preloaded, depth = False, 0
    for line in code.splitlines():
        if re.match(r'\s*#\s*(?:if|ifdef|ifndef)\b', line):
            depth += 1
        elif re.match(r'\s*#\s*endif\b', line):
            depth -= 1
        elif re.match(r'\s*#\s*include\s*[<"]crysta/model\.hpp[>"]', line):
            preloaded |= depth == 0
        elif re.match(r'\s*#\s*define\s+(?:private|protected|public)\b', line):
            assert preloaded, (
                'Access macros cannot rewrite SDK declarations or MSVC member identities'
            )


def test_authored_native_test_sources_preserve_sdk_access_identity():
    for directory in ('tests', 'core/include', 'core/src', 'cli', 'app/src'):
        for path in (ROOT / directory).rglob('*'):
            if path.is_file() and path.suffix in {'.cpp', '.hpp', '.h', '.cxx', '.inc'}:
                require_sdk_access_identity(path.read_text(encoding='utf-8'))


@pytest.mark.parametrize(
    'prefix',
    [
        '',
        '// #include "crysta/model.hpp"\n',
        '/*\n#include "crysta/model.hpp"\n*/\n',
        'auto text = R"(\n#include "crysta/model.hpp"\n)";\n',
        '#if 0\n#include "crysta/model.hpp"\n#endif\n',
    ],
)
@pytest.mark.parametrize('keyword', ['private', 'protected', 'public'])
def test_unloaded_sdk_macro_cannot_hide_behind_comments_strings_or_conditionals(prefix, keyword):
    source = prefix + '#define ' + keyword + ' public\n#include "edi/model.hpp"\n'
    with pytest.raises(AssertionError, match='Access macros cannot rewrite SDK'):
        require_sdk_access_identity(source)


def test_existing_transaction_probe_preloads_the_sdk_before_its_access_macro():
    require_sdk_access_identity(
        (ROOT / 'tests/fixtures/project_transactions/probe.cpp').read_text()
    )
    require_sdk_access_identity('#include <crysta/model.hpp>\n#define private public\n')
    with pytest.raises(AssertionError, match='Access macros cannot rewrite SDK'):
        require_sdk_access_identity('#def\\\nine private public\n#include "crysta/model.hpp"\n')


def test_committed_probe_preimage_reaches_the_access_macro_gate():
    previous = subprocess.check_output(
        [
            'git',
            'show',
            '7d9b79240e2b3b51ae1c2b2a8258bc7954486c4e:tests/unit/cpp/c09_t7_internal_probe.cpp',
        ],
        cwd=ROOT,
        text=True,
    )
    with pytest.raises(AssertionError, match='Access macros cannot rewrite SDK'):
        require_sdk_access_identity(previous)
