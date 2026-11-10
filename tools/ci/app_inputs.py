# SPDX-License-Identifier: BSD-3-Clause
"""Decide whether a pull request has to build and test the app.

The app job runs on a pull request unless every path it changes is one the app cannot read: the
website, knowledge pages, the Python tutorials, top-level markdown and the other workflows. Any
other path, one this list does not know included, builds and tests the app. Main pushes, the
nightly and manual runs always build it.

    python tools/ci/app_inputs.py <base> <head>
        prints `run=true` or `run=false`; the reason goes to stderr
"""

import fnmatch
import subprocess
import sys

# Paths the app build, its tests and the surfaces it stages never read.
INERT = (
    'website/*',
    'knowledge/*',
    'docs/user/tutorials/*',
    'CITATION.cff',
    '.github/workflows/*',
)
# The app job's own workflow is an input, even though other workflow files are not.
NOT_INERT = ('.github/workflows/ci.yml',)


def inert(path: str) -> bool:
    if path in NOT_INERT:
        return False
    # Markdown at the top level only (README.md and the like).
    if path.endswith('.md') and '/' not in path:
        return True
    return any(fnmatch.fnmatch(path, pattern) for pattern in INERT)


def changed(base: str, head: str) -> list[str]:
    result = subprocess.run(
        ['git', 'diff', '--name-only', f'{base}...{head}'],
        check=True,
        capture_output=True,
        text=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def main() -> int:
    base, head = sys.argv[1:3]
    paths = changed(base, head)
    inputs = [path for path in paths if not inert(path)]
    if inputs:
        print('run=true')
        print(f'{len(inputs)} app input(s) changed, the first {inputs[0]}', file=sys.stderr)
    else:
        print('run=false')
        print(f'None of the {len(paths)} changed path(s) is an app input', file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
