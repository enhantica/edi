# SPDX-License-Identifier: BSD-3-Clause
"""The standalone CLI's dependency check admits every operating system library the CLI links.

The libraries the CLI links come from cli/CMakeLists.txt, read here; the check's verdicts come from
simulated readelf, otool and dumpbin listings, so no platform toolchain is needed.
"""

import re
import sys
from pathlib import Path
from unittest import mock

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/installer'))
import standalone_cli  # noqa: E402

CMAKE = (ROOT / 'cli/CMakeLists.txt').read_text(encoding='utf-8')


def linked(branch: str) -> list[str]:
    """The libraries linked in the `if(WIN32)` branch ('windows') or its `else()` ('other')."""
    match = re.search(r'if\(WIN32\)(.*?)else\(\)(.*?)endif\(\)', CMAKE, re.DOTALL)
    assert match, 'cli/CMakeLists.txt links its operating system libraries per platform'
    body = match[1] if branch == 'windows' else match[2]
    return re.findall(r'target_link_libraries\(easydiffraction PRIVATE ([^)]+)\)', body)


def verdict(system: str, listing: str) -> None:
    with (
        mock.patch.object(standalone_cli, 'SYSTEM', system),
        mock.patch.object(standalone_cli.subprocess, 'check_output', return_value=listing),
    ):
        standalone_cli.verify_dependencies(Path('edi'))


def dumpbin(*dlls: str, delay: tuple[str, ...] = ()) -> str:
    listing = 'Dump of file edi.exe\n\nFile Type: EXECUTABLE IMAGE\n\n'
    listing += '  Image has the following dependencies:\n\n' + ''.join(f'    {d}\n' for d in dlls)
    if delay:
        listing += '\n  Image has the following delay load dependencies:\n\n'
        listing += ''.join(f'    {d}\n' for d in delay)
    return listing + '\n  Summary\n\n        1000 .data\n'


def otool(*paths: str) -> str:
    return 'edi:\n' + ''.join(
        f'\t{p} (compatibility version 1.0.0, current version 1.0.0)\n' for p in paths
    )


def readelf(*names: str) -> str:
    return ''.join(
        f' 0x0000000000000001 (NEEDED)             Shared library: [{n}]\n' for n in names
    )


def test_every_windows_library_the_cli_links_is_admitted():
    names = [name.lower() + '.dll' for line in linked('windows') for name in line.split()]
    assert names == ['winhttp.dll'], 'The Windows CLI links WinHTTP for downloads.'
    verdict('windows', dumpbin('KERNEL32.dll', *[n.upper() for n in names]))


@pytest.mark.parametrize(
    'unknown',
    ['vendor+math.dll', 'vendor math.dll', 'other.dll', 'api-ms-win-vendor-helper-l1-1-0.dll'],
)
def test_a_windows_library_outside_the_exact_list_is_refused_whatever_its_name(unknown):
    with pytest.raises(RuntimeError, match=re.escape(unknown)):
        verdict('windows', dumpbin('KERNEL32.dll', 'WINHTTP.dll', unknown))
    with pytest.raises(RuntimeError, match=re.escape(unknown)):
        verdict('windows', dumpbin('KERNEL32.dll', delay=(unknown,)))


def test_a_windows_listing_without_a_dependency_section_refuses():
    with pytest.raises(RuntimeError, match='dependency section'):
        verdict('windows', 'Dump of file edi.exe\n\nFile Type: EXECUTABLE IMAGE\n')


def test_linux_links_only_libdl_beside_the_c_runtime():
    assert linked('other') == ['${CMAKE_DL_LIBS}'], (
        'Elsewhere the CLI links only the loader library; libcurl is loaded on demand.'
    )
    system = ('libdl.so.2', 'libm.so.6', 'libc.so.6', 'ld-linux-x86-64.so.2')
    verdict('linux', readelf(*system))
    for unknown in ('libcurl.so.4', 'libvendor+x.so.1'):
        with pytest.raises(RuntimeError, match=re.escape(unknown)):
            verdict('linux', readelf(*system, unknown))
    with pytest.raises(RuntimeError, match='Cannot read the dependency row'):
        verdict('linux', readelf(*system) + ' 0x1 (NEEDED)  something else\n')


@pytest.mark.parametrize(
    'unknown',
    [
        '/opt/homebrew/lib/libcurl.4.dylib',
        '/usr/lib/../local/libvendor.dylib',
        '/System/Library/../../opt/vendor/libvendor.dylib',
        '/usr/lib/libcurl.4.dylib',
        '/System/Library/Frameworks/CoreFoundation.framework/Versions/A/CoreFoundation',
    ],
)
def test_macos_admits_only_the_exact_system_install_names(unknown):
    verdict('macos', otool('/usr/lib/libSystem.B.dylib', '/usr/lib/libc++.1.dylib'))
    with pytest.raises(RuntimeError, match=re.escape(unknown)):
        verdict('macos', otool('/usr/lib/libSystem.B.dylib', unknown))


def test_a_macos_row_in_another_shape_refuses():
    with pytest.raises(RuntimeError, match='Cannot read the dependency row'):
        verdict('macos', otool('/usr/lib/libSystem.B.dylib') + '\t/usr/lib/libz.1.dylib\n')


def test_the_check_reads_the_shipped_executable_through_the_platform_tool():
    with (
        mock.patch.object(standalone_cli, 'SYSTEM', 'windows'),
        mock.patch.object(
            standalone_cli.subprocess, 'check_output', return_value=dumpbin('WINHTTP.dll')
        ) as tool,
    ):
        standalone_cli.verify_dependencies(Path('edi.exe'))
    assert tool.call_args[0][0][:2] == ['dumpbin', '/dependents'], (
        'Windows reads dumpbin /dependents.'
    )
