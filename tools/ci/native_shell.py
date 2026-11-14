#!/usr/bin/env python3
"""Keep the workflow's selected Bash ahead of unrelated shell executables."""

import os
import sys
from pathlib import Path


def expose(shell: str, destination: Path) -> Path:
    """Append the actual running shell's directory to the Actions process path."""
    if any(character in shell for character in '\r\n'):
        raise ValueError('A shell path must occupy one environment-file line')
    selected = Path(shell).resolve(strict=True)
    if not selected.is_file() or selected.name not in {'bash', 'bash.exe'}:
        raise ValueError('The selected workflow shell must be an existing Bash executable')
    directory = str(selected.parent)
    if any(character in directory for character in '\r\n'):
        raise ValueError('A shell directory must occupy one environment-file line')
    with destination.open('a', encoding='utf-8', newline='\n') as output:
        output.write(directory + '\n')
    return selected


def main() -> None:
    """Use the Bash already selected by Actions, without another PATH search."""
    if len(sys.argv) != 2:
        raise ValueError('native_shell.py requires the running shell path')
    expose(sys.argv[1], Path(os.environ['GITHUB_PATH']))


if __name__ == '__main__':
    main()
