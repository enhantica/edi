"""The F-live producer's observed subprocess ( §P1.2b).

Runs the ONE live edi joint fit of the session — ``Project.load`` +
``fit_joint`` with a callback recording per-iteration history — inside the process the
native I/O observer was preloaded into, and emits the complete result as JSON on stdout:
the outcome fields, the full value/ESD/start maps, per-bank metrics, the callback history,
and the post-fit model parameter table (the write-back evidence). The session fixture parses
this transcript; no consumer re-runs the fit.
"""

from __future__ import annotations

import json
import sys

import edi


def _model_parameters(project: object) -> dict[str, list[float]]:
    """The post-fit model parameter table, keyed by the outcome's own path grammar."""
    mapped: dict[str, list[float]] = {}

    def record(path: str, parameter: object) -> None:
        mapped[path] = [float(parameter.value), float(parameter.uncertainty)]

    for field in ('length_a', 'length_b', 'length_c', 'angle_alpha', 'angle_beta', 'angle_gamma'):
        record(f'structure.cell.{field}', getattr(project.structure.cell, field))
    for site in project.structure.atom_sites:
        for field in ('fract_x', 'fract_y', 'fract_z', 'occupancy', 'adp_iso'):
            record(f'structure.atom_sites[{site.id}].{field}', getattr(site, field))
    for experiment in project.experiments:
        prefix = f'experiments[{experiment.name}]'
        for field in (
            'rise_alpha_0',
            'rise_alpha_1',
            'decay_beta_0',
            'decay_beta_1',
            'broad_gauss_sigma_0',
            'broad_gauss_sigma_1',
            'broad_gauss_sigma_2',
            'broad_gauss_size',
            'broad_gauss_strain',
            'broad_lorentz_gamma_0',
            'broad_lorentz_gamma_1',
            'broad_lorentz_gamma_2',
            'broad_lorentz_size',
            'broad_lorentz_strain',
        ):
            record(f'{prefix}.peak.{field}', getattr(experiment.peak, field))
        for field in (
            'calib_d_to_tof_offset',
            'calib_d_to_tof_linear',
            'calib_d_to_tof_quadratic',
        ):
            record(f'{prefix}.instrument.{field}', getattr(experiment.instrument, field))
        record(f'{prefix}.linked_structure.scale', experiment.linked_structure.scale)
        for index, point in enumerate(experiment.background):
            record(f'{prefix}.background[{index}].intensity', point.intensity)
        for field in ('abscor1', 'abscor2'):
            parameter = getattr(experiment.absorption, field)
            if parameter is not None:
                record(f'{prefix}.absorption.{field}', parameter)
    return mapped


def main() -> int:
    """Load the project, run the one observed fit, emit the JSON transcript."""
    project = edi.Project.load(sys.argv[1])
    history: list[dict[str, float]] = []

    def on_iteration(progress: object) -> None:
        history.append({
            'iteration': int(progress.iteration),
            'reduced_chi_square': float(progress.reduced_chi_square),
            'rwp': float(progress.rwp),
        })

    outcome = project.fit_joint(on_iteration=on_iteration)
    payload = {
        'status': str(outcome.status).rsplit('.', maxsplit=1)[-1].lower(),
        'converged': bool(outcome.converged),
        'iterations': int(outcome.iterations),
        'reduced_chi_square': float(outcome.reduced_chi_square),
        'rwp': float(outcome.rwp),
        'values': {path: float(value) for path, value in outcome.values.items()},
        'uncertainty': {path: float(value) for path, value in outcome.uncertainty.items()},
        'banks': [
            {
                'name': bank.name,
                'n_points': int(bank.n_points),
                'rwp': float(bank.rwp),
                'chi_square': float(bank.chi_square),
            }
            for bank in outcome.banks
        ],
        'callback_history': history,
        'model_parameters': _model_parameters(project),
    }
    json.dump(payload, sys.stdout)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
