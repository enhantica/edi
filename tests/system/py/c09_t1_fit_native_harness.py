from __future__ import annotations

import ctypes
import os
import sys
from pathlib import Path

import edi
import numpy as np


def measured(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    rows = np.loadtxt(path, dtype=np.float64)
    observed = rows[:, 1]
    return rows[:, 0], observed, np.sqrt(np.maximum(observed, 1.0))


def main() -> None:
    project = edi.Project.load(Path(sys.argv[1]))
    grid, observed, sigma = measured(Path(sys.argv[2]))
    os.environ['EDI_C08_NATIVE_OBSERVER_ACTIVE'] = '1'
    try:
        if sys.argv[3] == 'counterfactual':
            libc = ctypes.CDLL(None, use_errno=True)
            native_open = libc.open
            native_open.argtypes = [ctypes.c_char_p, ctypes.c_int]
            native_open.restype = ctypes.c_int
            descriptor = native_open(os.fsencode(sys.argv[4]), os.O_RDONLY)
            if descriptor < 0:
                raise OSError(ctypes.get_errno(), 'counterfactual native open failed')
            libc.close(descriptor)
            return
        result = project.fit(grid, observed, sigma)
    finally:
        os.environ['EDI_C08_NATIVE_OBSERVER_ACTIVE'] = '0'

    assert np.isfinite(result.rwp)
    assert np.isfinite(result.reduced_chi_square)


if __name__ == '__main__':
    main()
