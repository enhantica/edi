from __future__ import annotations

import ctypes
import os
import sys
from pathlib import Path

import edi
import numpy as np

from tests.model_calculation import calculate_on_grid


def main() -> None:
    project = edi.Project.load(Path(sys.argv[1]))
    tof_grid = np.asarray(
        [15000.0 + 70000.0 * float(index) / 256.0 for index in range(257)],
        dtype=np.float64,
    )
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
        pattern = calculate_on_grid(edi, project, tof_grid)
    finally:
        os.environ['EDI_C08_NATIVE_OBSERVER_ACTIVE'] = '0'

    assert pattern.shape == (257,)


if __name__ == '__main__':
    main()
