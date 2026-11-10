"""Record independent crysta lock ABI rows for SDK consumers without a checkout."""

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

import yaml

# Accepted ABI inventory; the reference values come only from the independent producer.
ABI_NAMES = {
    'gcc_impl_linux-64',
    'gxx_impl_linux-64',
    'libgcc',
    'libgcc-devel_linux-64',
    'libstdcxx',
    'libstdcxx-devel_linux-64',
    'libgomp',
    'sysroot_linux-64',
    'clang_impl_osx-arm64',
    'clangxx_impl_osx-arm64',
    'libcxx',
    'libcxx-devel',
    'llvm-openmp',
    'eigen',
    'sleef',
}

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('producer', type=Path)
source = parser.add_mutually_exclusive_group()
source.add_argument('--sdk-tag', help='Retained build-<sha> of the SDK pinned by edi')
source.add_argument('--ref', help='Main or the pinned SDK producer commit')
args = parser.parse_args()
if args.sdk_tag and not re.fullmatch(r'build-[0-9a-f]{40}', args.sdk_tag):
    parser.error('--sdk-tag must be a retained build-<full source sha>')
revision = args.sdk_tag.removeprefix('build-') if args.sdk_tag else args.ref or 'origin/main'
anchor = subprocess.check_output(
    ['git', '-C', str(args.producer), 'rev-parse', '--verify', revision + '^{commit}'], text=True
).strip()
raw = subprocess.check_output(['git', '-C', str(args.producer), 'show', anchor + ':pixi.lock'])
lock = yaml.safe_load(raw)
aliases = {p['name']: p.get('subdir', p['name']) for p in lock.get('platforms', [])}
platforms = {}
for key, packages in lock['environments']['cpp-ci']['packages'].items():
    values = {}
    for package in packages:
        if 'conda' in package:
            filename = (
                package['conda'].rsplit('/', 1)[-1].removesuffix('.conda').removesuffix('.tar.bz2')
            )
            name, version, build = filename.rsplit('-', 2)
            if name in ABI_NAMES:
                values[name] = [version, build]
    platforms[aliases.get(key, key)] = values
Path(__file__).with_name('producer-lock.json').write_text(
    json.dumps(
        {
            'repo': 'enhantica/crysta',
            'ref': args.sdk_tag or ('main' if revision == 'origin/main' else revision),
            'commit': anchor,
            'path': 'pixi.lock',
            'sha256': hashlib.sha256(raw).hexdigest(),
            'environment': 'cpp-ci',
            'platforms': platforms,
        },
        indent=2,
        sort_keys=True,
    )
    + '\n'
)
