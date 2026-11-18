# SPDX-License-Identifier: BSD-3-Clause
"""Compile the complete production settings functions independently of the QML host."""

import argparse
import hashlib
import json
import os
from pathlib import Path


def prepare(source, destination):
    text = (source / 'app/src/engine_setup.cpp').read_text(encoding='utf-8')
    spans = []
    for first, following in [
        ('QString& fresh_config_dir() {', '// Set by select_freetype_engine()'),
        ('QString settings_organisation() {', 'void store_settings_now()'),
        ('void use_fresh_settings() {', 'void select_freetype_engine('),
    ]:
        assert text.count(first) == 1 and text.count(following) == 1, (
            'ADR-0091: native settings coverage compiles uniquely bounded production functions'
        )
        section = text[text.index(first) : text.index(following)].rstrip()
        assert section.endswith('}'), (
            'ADR-0091: a settings probe must retain each complete production function body'
        )
        spans.append(section)
    provider = '\n'.join(spans) + '\n'
    destination.mkdir(parents=True, exist_ok=True)
    (destination / 'settings_provider.inc').write_text(provider, encoding='utf-8')
    (destination / 'settings_provider.sha256').write_text(
        hashlib.sha256(provider.encode()).hexdigest() + '\n',
        encoding='utf-8',
    )


def identity(source, destination):
    fixture = source / 'tests/fixtures/settings_identity'
    binary = destination / (
        'settings_identity_probe.exe' if os.name == 'nt' else 'settings_identity_probe'
    )
    paths = {
        'provider': destination / 'settings_provider.inc',
        'probe': fixture / 'probe.cpp',
        'cmake': fixture / 'CMakeLists.txt',
        'binary': binary,
    }
    return {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in paths.items()}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stamp', action='store_true')
    parser.add_argument('source', type=Path)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    if args.stamp:
        (args.destination / 'identity.json').write_text(
            json.dumps(identity(args.source, args.destination)),
            encoding='utf-8',
        )
    else:
        prepare(args.source, args.destination)
