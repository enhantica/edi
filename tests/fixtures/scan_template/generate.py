"""Copy the external-reference three-file scan into a portable fixture."""

import shutil
import sys
from pathlib import Path

source = Path(sys.argv[1]) / 'tests/fitting/cosio-d20-scan-3f/project'
target = Path(__file__).resolve().parent / 'project'
shutil.copytree(source, target)
