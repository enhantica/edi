"""Real source archive operations preserve bytes and refuse unsafe extraction."""

import contextlib
import gzip
import io
import json
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest
import yaml

from tools.ci import crysta_source_archive

ROOT = Path(__file__).resolve().parents[3]
TOOL = ROOT / 'tools/ci/crysta_source_archive.py'


def original_archive(path):
    with tarfile.open(path, 'w') as output:
        data = b'independent source payload\x00\r\n'
        entry = tarfile.TarInfo('src/payload.txt')
        entry.size = len(data)
        output.addfile(entry, io.BytesIO(data))
    return data


def test_real_append_and_extract_keep_source_and_receipt_bytes_under_native_paths(tmp_path):
    folder = tmp_path / 'source archive Ω with spaces'
    folder.mkdir()
    archive = folder / 'source.tar'
    payload = original_archive(archive)
    receipt = folder / 'receipt.json'
    receipt.write_text(json.dumps({'src/payload.txt': 'a7' * 20}) + '\n', encoding='utf-8')
    run = subprocess.run(
        [sys.executable, str(TOOL), 'append', str(archive), str(receipt)],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert run.returncode == 0, run.stderr
    compressed = folder / 'source.tar.gz'
    with gzip.open(compressed, 'wb') as stream:
        stream.write(archive.read_bytes())
    destination = tmp_path / 'extracted Ω with spaces'
    run = subprocess.run(
        [sys.executable, str(TOOL), 'extract', str(compressed), str(destination)],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert run.returncode == 0, run.stderr
    assert (destination / 'src/payload.txt').read_bytes() == payload
    assert (destination / crysta_source_archive.RECEIPT).read_bytes() == receipt.read_bytes()
    with tarfile.open(archive) as source:
        assert source.getnames() == ['src/payload.txt', crysta_source_archive.RECEIPT]
    with pytest.raises(ValueError, match='already contains'):
        crysta_source_archive.append_receipt(archive, receipt)


@pytest.mark.parametrize('kind', ['parent', 'absolute', 'symlink'])
def test_source_extraction_cannot_write_outside_its_destination(tmp_path, kind):
    archive = tmp_path / 'unsafe.tar'
    outside = tmp_path / 'outside.txt'
    outside.write_bytes(b'unrelated existing bytes')
    with tarfile.open(archive, 'w') as output:
        member = tarfile.TarInfo('../outside.txt' if kind == 'parent' else str(outside))
        if kind == 'symlink':
            member = tarfile.TarInfo('link')
            member.type = tarfile.SYMTYPE
            member.linkname = str(outside)
            output.addfile(member)
        else:
            member.size = 7
            output.addfile(member, io.BytesIO(b'changed'))
    with contextlib.suppress(tarfile.FilterError):
        crysta_source_archive.extract(archive, tmp_path / 'destination')
    assert outside.read_bytes() == b'unrelated existing bytes'


def test_source_producer_and_both_consumers_share_python_archive_operations():
    producer = yaml.safe_load((ROOT / '.github/workflows/crysta-sdk.yml').read_text())
    installer = yaml.safe_load((ROOT / '.github/workflows/installers.yml').read_text())
    pack = next(
        step['run']
        for step in producer['jobs']['build']['steps']
        if 'cpp-ci sdk-pack' in step.get('run', '')
    )
    unpack = next(
        step['run']
        for step in installer['jobs']['installers']['steps']
        if step.get('name') == 'Unpack the pinned crysta source'
    )
    core = (ROOT / 'tools/ci/crysta-src.sh').read_text()
    assert 'python3 tools/ci/crysta_source_archive.py append' in pack
    assert 'python tools/ci/crysta_source_archive.py extract' in unpack
    assert 'python3 "$ROOT/tools/ci/crysta_source_archive.py" extract' in core
    assert 'tar -rf' not in pack and 'tar -xzf' not in unpack + core
    assert "'tools/ci/crysta_source_archive.py'" in producer['jobs']['resolve']['steps'][-1]['run']
