"""Parse unchanged standard headers once for the native compiler witnesses."""

import shutil
import subprocess

import pytest

from tests.conftest import crysta_reference_prefix


def crysta_headers():
    """Before: sibling headers. After: the SDK actually linked by edi, fail closed."""
    include = crysta_reference_prefix() / 'include'
    assert (include / 'crysta/anchors.hpp').is_file(), (
        ' native witnesses require the linked SDK complete public headers'
    )
    return include


@pytest.fixture(scope='session')
def standard_headers(tmp_path_factory):
    compiler = shutil.which('clang++')
    assert compiler, ' native witnesses require the real Clang compiler'
    directory = tmp_path_factory.mktemp('c34-standard-headers')
    source, compiled = directory / 'standard.hpp', directory / 'standard.pch'
    # No edi or crysta declaration is cached: both complete public header graphs and
    # every attempted capability still compile in their own compiler invocation.
    source.write_text(
        ''.join(
            '#include <' + header + '>\n'
            for header in (
                'algorithm',
                'array',
                'bit',
                'set',
                'atomic',
                'concepts',
                'cstddef',
                'cstdint',
                'compare',
                'deque',
                'exception',
                'filesystem',
                'functional',
                'iterator',
                'map',
                'initializer_list',
                'memory',
                'mutex',
                'optional',
                'ostream',
                'span',
                'stdexcept',
                'string',
                'string_view',
                'tuple',
                'type_traits',
                'unordered_map',
                'utility',
                'vector',
            )
        )
    )
    result = subprocess.run(
        [compiler, '-std=c++20', '-c', '-x', 'c++-header', str(source), '-o', str(compiled)],
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )
    assert result.returncode == 0, (
        ' only standard headers may be precompiled for native witnesses: ' + result.stderr
    )
    return compiled
