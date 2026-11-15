"""Bind native witnesses to the exact selected extension's CMake build."""

import hashlib
import io
import shutil
import subprocess
import tarfile
from pathlib import Path


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).digest()


def selected_core(root, extension, *, archive=None, include=None):
    root, extension = Path(root), Path(extension).resolve()
    candidates = [extension.parent, *sorted((root / 'build').glob('*'))]
    matches = {
        p.resolve()
        for p in candidates
        if (p / 'CMakeCache.txt').is_file()
        and (p / extension.name).is_file()
        and digest(p / extension.name) == digest(extension)
    }
    assert len(matches) == 1, (
        'The observer must identify exactly one build containing the selected extension bytes'
    )
    build = matches.pop()
    library = build / 'libcrysta_core.a'
    cache = (build / 'CMakeCache.txt').read_text()
    sources = [
        line.split('=', 1)[1]
        for line in cache.splitlines()
        if line.startswith('CMAKE_HOME_DIRECTORY:INTERNAL=')
    ]
    assert len(sources) == 1, 'The selected build must declare its actual source headers'
    headers = Path(sources[0]) / 'include'
    assert headers.is_dir(), 'The selected native build must retain its own headers'
    if archive is not None:
        assert digest(archive) == digest(library), (
            'A native core override must match the archive beside the selected extension'
        )
    if include is not None:
        other = Path(include)
        reference = {p.relative_to(headers): digest(p) for p in headers.rglob('*') if p.is_file()}
        actual = {p.relative_to(other): digest(p) for p in other.rglob('*') if p.is_file()}
        assert actual == reference, 'A header override must match the selected build headers'
    return library, headers


def identity(observed, selected):
    assert observed.strip() == selected, (
        'The linked native observer must embed the selected engine source identity'
    )


def committed_headers(root, headers, commit):
    archive = subprocess.run(
        [shutil.which('git'), '-C', str(root), 'archive', commit, 'include'],
        capture_output=True,
        check=True,
        timeout=5,
    )
    with tarfile.open(fileobj=io.BytesIO(archive.stdout)) as source:
        expected = {
            Path(member.name).relative_to('include'): hashlib.sha256(
                source.extractfile(member).read()
            ).digest()
            for member in source.getmembers()
            if member.isfile()
        }
    actual = {p.relative_to(headers): digest(p) for p in headers.rglob('*') if p.is_file()}
    assert actual == expected, 'Probe headers must match the selected engine source identity'
