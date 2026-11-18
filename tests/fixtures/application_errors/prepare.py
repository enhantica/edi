# SPDX-License-Identifier: BSD-3-Clause
"""Prepare the complete production application exception boundary for a Qt probe."""

import argparse
import hashlib
import json
import os
from pathlib import Path


def prepare(source, destination):
    text = (source / 'app/main.cpp').read_text(encoding='utf-8')
    first = "namespace {\n// A failure in one event's handler"
    following = '// Thin QML host'
    assert text.count(first) == 1 and text.count(following) == 1, (
        'ADR-0062: caught-error coverage compiles the uniquely bounded application class'
    )
    provider = text[text.index(first) : text.index(following)].rstrip() + '\n'
    assert (
        'class GuardedApplication final : public QGuiApplication' in provider
        and provider.rstrip().endswith('namespace')
    ), 'ADR-0062: the complete production event boundary must be retained'
    destination.mkdir(parents=True, exist_ok=True)
    (destination / 'application_provider.inc').write_text(provider, encoding='utf-8')


def identity(source, destination):
    binary = destination / (
        'error_boundary_probe.exe' if os.name == 'nt' else 'error_boundary_probe'
    )
    paths = {
        'provider': destination / 'application_provider.inc',
        'fixture': source / 'tests/fixtures/application_errors/probe.cpp',
        'cmake': source / 'tests/fixtures/onboarding/native/CMakeLists.txt',
        'binary': binary,
    }
    return {key: hashlib.sha256(path.read_bytes()).hexdigest() for key, path in paths.items()}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stamp', action='store_true')
    parser.add_argument('source', type=Path)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    if args.stamp:
        (args.destination / 'error_boundary.identity.json').write_text(
            json.dumps(identity(args.source, args.destination)),
            encoding='utf-8',
        )
    else:
        prepare(args.source, args.destination)
