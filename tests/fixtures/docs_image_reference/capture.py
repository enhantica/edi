# SPDX-License-Identifier: BSD-3-Clause
"""Execute the declared producer after removing stale app images in an isolated source copy."""

import io
import json
import os
import shutil
import struct
import subprocess
import sys
import tarfile
import zlib
from pathlib import Path


def png_chunks(content):
    position = 8
    while position < len(content):
        size = struct.unpack_from('!I', content, position)[0]
        kind = content[position + 4 : position + 8]
        payload = content[position + 8 : position + 8 + size]
        checksum = struct.unpack_from('!I', content, position + 8 + size)[0]
        if checksum != zlib.crc32(kind + payload):
            raise ValueError('Invalid captured PNG checksum')
        position += size + 12
        yield kind, payload


def valid_png(path):
    content = path.read_bytes()
    if content[:8] != b'\x89PNG\r\n\x1a\n':
        return False
    try:
        chunks = list(png_chunks(content))
        dimensions = struct.unpack_from('!II', chunks[0][1])
        compressed = b''.join(payload for kind, payload in chunks if kind == b'IDAT')
        return bool(
            chunks[0][0] == b'IHDR'
            and chunks[-1][0] == b'IEND'
            and all(dimensions)
            and zlib.decompress(compressed)
        )
    except (IndexError, ValueError, struct.error, zlib.error):
        return False


def decode_outputs(paths, temporary):
    project = Path(__file__).resolve().parents[3]
    provisioned = project / 'tools/installer/.pixi/envs/default/bin/python'
    interpreter = os.environ.get(
        'EDI_DOCS_BROWSER_PYTHON', str(provisioned) if provisioned.is_file() else sys.executable
    )
    inputs, output = temporary / 'fresh-images.json', temporary / 'fresh-decoded.json'
    inputs.write_text(json.dumps(list(map(str, paths))), encoding='utf-8')
    result = subprocess.run(
        [interpreter, str(Path(__file__).with_name('decode.py')), str(inputs), str(output)],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0 and output.is_file(), (
        'Fresh capture outputs must reach the actual local-only image decoder: ' + result.stderr
    )
    rows = json.loads(output.read_text(encoding='utf-8'))
    assert len(rows) == len(paths) and all(row['loaded'] for row in rows), (
        'Every fresh capture output must fully decode as an image'
    )


def execute(project, manifest, required, temporary):
    command = manifest.get('command')
    assert (
        isinstance(command, list)
        and command
        and all(isinstance(part, str) and part for part in command)
        and command.count('OUTPUT') == 1
    ), 'The capture route must declare executable arguments and one disposable OUTPUT'
    declared = {
        (item['theme'], item['path'])
        for item in manifest['images']
        if item['path'].startswith('assets/gui/') or item.get('kind') == 'app'
    }
    assert required and required <= declared, (
        'The capture declaration must cover every required app image under both schemes'
    )
    workspace = temporary / 'source'
    if (project / '.git').exists():
        payload = subprocess.check_output(['git', 'archive', 'HEAD'], cwd=project)
        workspace.mkdir()
        with tarfile.open(fileobj=io.BytesIO(payload)) as archive:
            archive.extractall(workspace, filter='data')
    else:
        shutil.copytree(project, workspace)
    publication = workspace / 'website/surfaces/docs'
    for _, relative in declared:
        target = publication / relative
        assert target.resolve().is_relative_to(publication.resolve()), (
            'A capture output must remain inside the disposable publication tree'
        )
        target.unlink(missing_ok=True)
    for target in (publication / 'assets/gui').rglob('*'):
        if target.suffix.lower() in {'.png', '.jpg', '.jpeg', '.svg', '.webp'}:
            target.unlink()
    output = temporary / 'captured'
    argv = [str(output) if part == 'OUTPUT' else part for part in command]
    env = {**os.environ}
    app = project / 'build/app/app/edi_app'
    if 'EDI_DOCS_APP' not in env and app.is_file():
        env['EDI_DOCS_APP'] = str(app.resolve())
    try:
        result = subprocess.run(
            argv,
            cwd=workspace,
            env=env,
            capture_output=True,
            text=True,
            timeout=1800,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise AssertionError('The declared capture command must execute successfully') from error
    (temporary / 'capture.stdout').write_text(result.stdout, encoding='utf-8')
    (temporary / 'capture.stderr').write_text(result.stderr, encoding='utf-8')
    assert result.returncode == 0, (
        'The declared capture command must complete successfully: ' + result.stderr[-4000:]
    )
    from tests.fixtures.tutorial_cases.screenshots import (  # noqa: PLC0415
        tutorial_folders,
        webp_info,
    )

    tutorial_roots = tutorial_folders(publication)
    produced = set()
    for theme, relative in declared:
        target = publication / relative
        if not target.is_file():
            continue
        assert target.resolve().is_relative_to(publication.resolve()), (
            'A newly captured image must not be a link to stale outside output'
        )
        tutorial = any(
            target.resolve().is_relative_to(folder.resolve()) for folder in tutorial_roots
        )
        if tutorial:
            assert target.suffix == '.webp' and webp_info(target)['loaded'], (
                'Each freshly captured tutorial output must be a complete WebP image'
            )
        else:
            assert valid_png(target), (
                'Each freshly captured feature output must be a complete nonempty PNG image'
            )
        produced.add((theme, relative))
    assert declared <= produced and required <= produced, (
        'The executed capture must freshly produce every declared and required app image'
    )
    decode_outputs([publication / relative for _, relative in sorted(produced)], temporary)
    return produced
