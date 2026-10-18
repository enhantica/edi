"Run a real save in its own process with the caller's filesystem permissions."

import importlib
import sys
from pathlib import Path

sys.meta_path[:] = [
    finder
    for finder in sys.meta_path
    if type(finder).__module__ not in {'_crysta_editable', '_edi_editable'}
]
engine = importlib.import_module(sys.argv[1])
project = engine.Project.load(Path(sys.argv[3]))
print('entered', flush=True)
try:
    if sys.argv[2] == 'save':
        project.save()
    else:
        project.save_as(Path(sys.argv[4]))
except (OSError, ValueError, RuntimeError) as error:
    print('refused', str(error), flush=True)
else:
    print('published', flush=True)
