"""The Node interpreter of the test's own Pixi environment, on every platform."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def environment_node() -> Path:
    """Where conda puts Node: `bin/node` on Linux and macOS, `node.exe` at the root on Windows."""
    prefix = Path(sys.prefix)
    return prefix / 'node.exe' if os.name == 'nt' else prefix / 'bin/node'
