"""Closed-form axial neutron Gaussian profiles for the authored two-phase fixture."""

import math

import numpy as np


def axial_profiles(grid):
    """Two P1 Friedel orbits per phase, with the declared five-FWHM C1 window."""
    profiles = []
    for lengths, scale in (((4.1, 3.95), 0.8), ((3.6, 3.3), 1.2)):
        phase = []
        for length in lengths:
            theta = math.asin(1.54 / (2 * length))
            delta = grid - 2 * math.degrees(theta)
            width = 0.05
            extent = 5 * width
            offset = np.abs(delta)
            taper = np.where(
                offset <= 0.8 * extent,
                1,
                np.where(
                    offset >= extent,
                    0,
                    0.5 * (1 + np.cos(np.pi * (offset - 0.8 * extent) / (0.2 * extent))),
                ),
            )
            # Coincident La occupancies sum to one; b=8.24 fm (NIST), m=2, fm²/barn=0.01.
            intensity = scale * 2 * (8.24**2 / 100) / (math.sin(theta) * math.sin(2 * theta))
            gaussian = (
                (2 / width)
                * math.sqrt(math.log(2) / math.pi)
                * np.exp(-4 * math.log(2) * (delta / width) ** 2)
            )
            phase.append(intensity * gaussian * taper)
        profiles.append(phase)
    return profiles
