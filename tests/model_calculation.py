# SPDX-License-Identifier: BSD-3-Clause
"""Test helpers for declaring a calculation grid on the project model."""

from __future__ import annotations

from typing import Any

import numpy as np


def calculate_on_grid(module: Any, project: Any, grid: Any | None = None) -> np.ndarray:
    """Optionally declare a grid, then return the model-stored calculated intensity."""
    if grid is not None:
        axis = np.asarray(grid, dtype=np.float64)
        zeros = np.zeros_like(axis).tolist()
        ones = np.ones_like(axis).tolist()
        if isinstance(
            project.experiment.instrument,
            (module.CwlPdNeutronInstrument, module.CwlPdXrayInstrument),
        ):
            project.experiment.data = module.PdCwlData(
                two_theta=axis.tolist(),
                intensity_meas=zeros,
                intensity_meas_su=ones,
            )
        else:
            project.experiment.data = module.PdTofData(
                time_of_flight=axis.tolist(),
                intensity_meas=zeros,
                intensity_meas_su=ones,
            )
    project.analysis.calculate()
    return np.asarray(project.experiment.data.intensity_calc, dtype=np.float64)
