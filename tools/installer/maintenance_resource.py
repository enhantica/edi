# SPDX-License-Identifier: BSD-3-Clause
"""The maintenance tool's pages: the resource an update puts into MaintenanceTool.dat.

The Framework keeps the tool's configuration, control script, style sheet and our resources (the
English text and the images) in MaintenanceTool.dat, which the running tool writes at the end of
every update by copying what the old file holds. So a newer tool keeps showing the pages of the
release first installed, unless the update names a replacement for the default resource (the
Framework's DefaultResourceReplacement, read while that file is written). The replacement is the
only resource the update can bring, so it carries the -r resources as well: the old file may have
none (edi ADR-0106).
"""

import struct
import subprocess
import tempfile
import xml.etree.ElementTree as ET  # noqa: S405 - our own .qrc files only
import zlib
from pathlib import Path

# The name the app component unpacks it under, at the top of the installation.
RESOURCE_NAME = 'MaintenanceTool.rcc'

_MAGIC_COOKIE_DAT = 0xC2630A1C99D668F9
_DIRECTORY, _COMPRESSED, _COMPRESSED_ZSTD = 0x2, 0x1, 0x4


def read_rcc(data: bytes) -> dict[str, bytes]:
    """The files of a compiled Qt resource (rcc -binary), by path without a leading slash."""
    if data[:4] != b'qres':
        raise ValueError('not a compiled Qt resource')
    version, tree, payload, names = struct.unpack_from('>IIII', data, 4)
    node_size = 14 if version == 1 else 22

    def name_at(offset: int) -> str:
        (length,) = struct.unpack_from('>H', data, names + offset)
        start = names + offset + 6  # the length and the name's hash
        return data[start : start + 2 * length].decode('utf-16-be')

    files: dict[str, bytes] = {}

    def walk(index: int, prefix: str) -> None:
        node = tree + index * node_size
        name_offset, flags = struct.unpack_from('>IH', data, node)
        path = prefix + name_at(name_offset) if index else ''
        if flags & _DIRECTORY:
            count, first = struct.unpack_from('>II', data, node + 6)
            for child in range(first, first + count):
                walk(child, path + '/' if path else '')
            return
        (offset,) = struct.unpack_from('>I', data, node + 10)
        (size,) = struct.unpack_from('>I', data, payload + offset)
        content = data[payload + offset + 4 : payload + offset + 4 + size]
        if flags & _COMPRESSED_ZSTD:
            raise ValueError(f'{path} is zstd-compressed, which this reader does not take')
        if flags & _COMPRESSED:
            content = zlib.decompress(content[4:])  # qCompress puts the size first
        files[path] = content

    walk(0, '')
    return files


def dat_resources(path: Path) -> list[bytes]:
    """The meta resources a maintenance tool's .dat holds, the default resource first."""
    data = path.read_bytes()
    (cookie,) = struct.unpack_from('<Q', data, len(data) - 8)
    if cookie != _MAGIC_COOKIE_DAT:
        raise ValueError(f'{path.name} is not a maintenance tool data file')
    end = len(data)
    (count,) = struct.unpack_from('<q', data, end - 32)
    (content_size,) = struct.unpack_from('<q', data, end - 24)
    start_of_content = end - content_size
    ranges = end - (count * 16 + 64) + 16  # after the resource collections' range
    resources = []
    for index in range(count):
        offset, length = struct.unpack_from('<qq', data, ranges + 16 * index)
        resources.append(data[start_of_content + offset : start_of_content + offset + length])
    return resources


def dat_files(path: Path) -> dict[str, bytes]:
    """What the tool reads under :/metadata: the first resource holding a path wins, as in Qt."""
    files: dict[str, bytes] = {}
    for resource in dat_resources(path):
        for name, content in read_rcc(resource).items():
            files.setdefault(name, content)
    return files


def build(
    binarycreator: Path,
    rcc: Path,
    config: Path,
    resources: Path,
    output: Path,
    environment: dict | None = None,
) -> Path:
    """Compile the replacement: the online installer's default resource and its -r resources.

    binarycreator -rcc writes the default resource as the installer would (config.xml and the
    files it names, for an online installer), and Qt's rcc adds the .qrc's files beside it.
    """
    with tempfile.TemporaryDirectory() as scratch:
        work = Path(scratch)
        subprocess.run(
            [binarycreator, '--online-only', '-c', config, '-rcc'],
            cwd=work, env=environment, check=True, capture_output=True,
        )  # fmt: skip
        tree = work / 'default'
        for name, content in read_rcc((work / 'update.rcc').read_bytes()).items():
            if name.startswith('rccproject'):
                continue  # binarycreator's own project file, under a random name
            target = tree / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        # Written by the XML writer: the scratch path may hold any character, an ampersand too.
        default = ET.Element('RCC')
        listed = ET.SubElement(default, 'qresource', prefix='/')
        for path in sorted(p for p in tree.rglob('*') if p.is_file()):
            entry = ET.SubElement(listed, 'file', alias=path.relative_to(tree).as_posix())
            entry.text = path.as_posix()
        default_qrc = work / 'default.qrc'
        ET.ElementTree(default).write(default_qrc, encoding='utf-8')
        # Absolute paths for the -r files too, so both lists compile from one directory.
        added = ET.parse(resources)  # noqa: S314 - written by package.py
        for element in added.iter('file'):
            element.set('alias', element.get('alias', element.text))
            element.text = (resources.parent / element.text).resolve().as_posix()
        added_qrc = work / 'added.qrc'
        added.write(added_qrc, encoding='utf-8')
        output.parent.mkdir(parents=True, exist_ok=True)
        # Uncompressed, so the tool's Qt reads it whatever compression it was built with, and in
        # the first format, which holds no file times: the same pages give the same bytes.
        subprocess.run(
            [rcc, '--binary', '--no-compress', '--format-version', '1', '-o', output,
             default_qrc, added_qrc],
            check=True, capture_output=True,
        )  # fmt: skip
    files = read_rcc(output.read_bytes())
    for required in ('installer-config/config.xml', 'translations/ifw_en.qm', 'edi/CheckMark.png'):
        if required not in files:
            output.unlink(missing_ok=True)
            raise RuntimeError(f'The maintenance tool resource has no {required}')
    return output
