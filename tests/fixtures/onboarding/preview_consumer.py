"""Load the frozen independent consumer without changing its source bytes."""

import runpy
from pathlib import Path

validate_bundle = runpy.run_path(str(Path(__file__).with_name('preview_gui_capture.txt')))[
    'validate_bundle'
]
