"""Bind native witnesses to the exact selected extension's CMake build."""

import hashlib
import io
import re
import shutil
import subprocess
import tarfile
from pathlib import Path


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).digest()


def selected_core(root, extension, *, archive=None, include=None):
    root, extension = Path(root), Path(extension).resolve()
    # A loaded build artifact identifies its own CMake owner, even outside this checkout.
    # Byte matching is the fallback for an installed COPY, whose original location is lost.
    owners = [p for p in extension.parents if (p / 'CMakeCache.txt').is_file()]
    if owners:
        build = owners[0]
    else:
        matches = {
            p.resolve()
            for p in (root / 'build').glob('*')
            if (p / 'CMakeCache.txt').is_file()
            and (p / extension.name).is_file()
            and digest(p / extension.name) == digest(extension)
        }
        assert len(matches) == 1, (
            'An installed observer must identify exactly one build with its extension bytes'
        )
        build = matches.pop()
    library = build / 'libcrysta_core.a'
    assert library.is_file(), 'The selected extension must retain its own native core archive'
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


def cache_item(cache, name):
    values = [
        line.split('=', 1)[1]
        for line in cache.splitlines()
        if re.match(re.escape(name) + r':[^=]+=', line)
    ]
    assert len(values) == 1, 'A selected native build must declare one unambiguous CMake input'
    return Path(values[0])


def selected_edi(root, extension):
    root, extension = Path(root), Path(extension).resolve()
    artifact = extension.parents[2]
    configurations = {
        (root / 'build/ci').resolve(): root / 'build/crysta-prefix',
        (root / 'build/ci-consumer').resolve(): root / 'build/crysta-consumer-prefix',
    }
    if artifact in configurations:
        # Declared exports relocate these paths; their cached absolute build paths do not.
        prefix, headers = configurations[artifact], root / 'core/include'
    else:
        cache = artifact / 'CMakeCache.txt'
        assert cache.is_file(), (
            'A local edi observer needs its selected artifact CMake configuration'
        )
        text = cache.read_text()
        package = cache_item(text, 'crysta_DIR')
        assert (package / 'crystaConfig.cmake').is_file(), (
            'The selected edi build must retain the actual crysta CMake package it linked'
        )
        prefix = package.parents[2]
        headers = cache_item(text, 'CMAKE_HOME_DIRECTORY') / 'core/include'
    assert (artifact / 'core/libedi_core.a').is_file(), (
        'The selected edi extension must retain its own native core archive'
    )
    assert (prefix / 'lib/libcrysta_core.a').is_file(), (
        'The selected edi CMake package must retain its crysta core'
    )
    assert (prefix / 'include').is_dir(), (
        'The selected edi CMake package must retain its crysta headers'
    )
    assert headers.is_dir(), 'The selected edi build must retain its own source headers'
    linked = (artifact / '.crysta-linked-sha').read_text().strip()
    assert re.fullmatch(r'[0-9a-f]{40}', linked), (
        'The selected edi native artifact must declare its full linked crysta identity'
    )
    assert (prefix / '.crysta-sha').read_text().strip() == linked, (
        'A local edi observer must use the crysta identity linked into its selected extension'
    )
    return artifact, prefix, headers, linked


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
