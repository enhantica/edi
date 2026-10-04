from __future__ import annotations

import ctypes
import os
import sys
from pathlib import Path

import edi
import numpy as np


def measured(path: Path) -> edi.PdTofData:
    lines = path.read_text(encoding='utf-8').splitlines()
    start = lines.index('_data.time_of_flight')
    tags = []
    index = start
    while index < len(lines) and lines[index].startswith('_'):
        tags.append(lines[index])
        index += 1
    rows = np.loadtxt(lines[index:], dtype=np.float64)
    return edi.PdTofData(
        time_of_flight=rows[:, tags.index('_data.time_of_flight')],
        intensity_meas=rows[:, tags.index('_data.intensity_meas')],
        intensity_meas_su=rows[:, tags.index('_data.intensity_meas_su')],
    )


def main() -> None:
    project_directory = Path(sys.argv[1])
    project = edi.Project.load(project_directory)
    patterns = [
        measured(path) for path in sorted((project_directory / 'experiments').glob('*.edi'))
    ]
    os.environ['EDI_C08_NATIVE_OBSERVER_ACTIVE'] = '1'
    try:
        if sys.argv[2] == 'counterfactual':
            libc = ctypes.CDLL(None, use_errno=True)
            native_open = libc.open
            native_open.argtypes = [ctypes.c_char_p, ctypes.c_int]
            native_open.restype = ctypes.c_int
            descriptor = native_open(os.fsencode(sys.argv[3]), os.O_RDONLY)
            if descriptor < 0:
                raise OSError(ctypes.get_errno(), 'counterfactual native open failed')
            libc.close(descriptor)
            return
        result = project.fit_joint(patterns)
    finally:
        os.environ['EDI_C08_NATIVE_OBSERVER_ACTIVE'] = '0'

    assert np.isfinite(result.rwp)
    assert np.isfinite(result.reduced_chi_square)


if __name__ == '__main__':
    main()
