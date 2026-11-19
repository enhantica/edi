"""Data-only exchange contract for the GSAS-II CW neutron converter."""

import numpy as np

FORMAT = 'gsas-ii-pnc-v1'
INSTRUMENT = ('Lam', 'Zero', 'U', 'V', 'W', 'X', 'Y', 'SH/L')


def require(condition: object, message: str) -> None:
    """Refuse settings outside the supported conversion."""
    if not condition:
        raise ValueError(message)


def profile_metrics(reference: np.ndarray, candidate: np.ndarray, sigma: np.ndarray) -> dict:
    """Compare calculated/background columns on their already validated common grid."""
    require(
        reference.shape == candidate.shape == (len(sigma), 2)
        and np.isfinite(reference).all()
        and np.isfinite(candidate).all(),
        'Expected finite calculated and background profiles on the common grid',
    )
    difference = candidate[:, 0] - reference[:, 0]
    reference_net = reference[:, 0] - reference[:, 1]
    net_difference = (candidate[:, 0] - candidate[:, 1]) - reference_net
    require(np.linalg.norm(reference_net) > 0, 'Reference has no Bragg signal')
    return {
        'points': len(sigma),
        'total_relative_l2': float(np.linalg.norm(difference) / np.linalg.norm(reference[:, 0])),
        'net_relative_l2': float(np.linalg.norm(net_difference) / np.linalg.norm(reference_net)),
        'weighted_net_relative_l2': float(
            np.linalg.norm(net_difference / sigma) / np.linalg.norm(reference_net / sigma)
        ),
        'total_rms_counts': float(np.sqrt(np.mean(difference**2))),
        'total_max_abs_counts': float(np.max(np.abs(difference))),
        'background_max_abs_counts': float(np.max(np.abs(candidate[:, 1] - reference[:, 1]))),
        'reference_net_peak_counts': float(np.max(reference_net)),
    }
