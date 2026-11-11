# SPDX-License-Identifier: BSD-3-Clause
"""Write the runner-source-objects.json an exported crysta source carries.

A source exported without its .git cannot name its own Git objects, so crysta's web observer
builders (tests/fixtures/web_parallel and web_simd) read them from this receipt, written from the
checkout the archive came from: each path the SIMD builder binds, by its object at the commit. The
paths are read from the builders themselves, so the receipt follows them.

    python tools/ci/crysta_source_receipt.py CRYSTA_CHECKOUT SHA OUTPUT
"""

from __future__ import annotations

import ast
import json
import pathlib
import subprocess
import sys


def declared(repo: str, sha: str, path: str, name: str) -> list[str]:
    """The tuple of paths `name` holds in the builder at `path`."""
    text = subprocess.run(
        ['git', '-C', repo, 'show', f'{sha}:{path}'], capture_output=True, text=True, check=True
    ).stdout
    for node in ast.parse(text).body:
        if isinstance(node, ast.Assign) and any(
            getattr(t, 'id', None) == name for t in node.targets
        ):
            return [str(ast.literal_eval(item)) for item in node.value.elts]
    raise SystemExit(f'{path} declares no {name}')


def main() -> int:
    repo, sha, output = sys.argv[1:4]
    paths = declared(repo, sha, 'tests/fixtures/web_simd/build.py', 'PATHS')
    parallel = declared(repo, sha, 'tests/fixtures/web_parallel/build.py', 'SOURCE_PATHS')
    if not set(parallel) <= set(paths):
        raise SystemExit(
            'the web_parallel builder binds paths the web_simd receipt does not carry'
        )
    objects = subprocess.run(
        ['git', '-C', repo, 'rev-parse', *[f'{sha}:{path}' for path in paths]],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    with pathlib.Path(output).open('w', encoding='utf-8') as stream:
        json.dump(dict(zip(paths, objects, strict=True)), stream, indent=2)
        stream.write('\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
