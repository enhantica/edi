"""Reproduce the no-loop loader boundary without ever populating its declarations."""

import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
materialize = runpy.run_path(str(ROOT / 'tests/fixtures/constraint_expressions/project.py'))[
    'materialize'
]
materialize(Path(__file__).parent / 'project')
