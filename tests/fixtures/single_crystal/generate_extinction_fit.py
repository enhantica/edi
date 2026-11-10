"""Freeze a Becker-Coppens fit using FullProf's unextincted structure factors."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path

import numpy as np
import scipy
from scipy.optimize import least_squares

HERE = Path(__file__).resolve().parent
CASE = 'sc-neut-cwl_tbti_isotropic-extinction'
PROJECT = 'sc-neut-cwl_tb2ti2o7-heidi_isotropic-extinction'


def correction(f2, cosine, wavelength, volume, radius, mosaicity):
    """Spherical Gaussian primary and secondary factors; see fitting/becker-coppens."""
    g = mosaicity * np.pi / 10800
    x = 1.5 * f2 * (wavelength * radius / volume) ** 2
    primary = (
        1 + 2 * x + (0.2 + 0.45 * cosine) * x**2 / (1 + (0.22 - 0.12 * (0.5 - cosine) ** 2) * x)
    ) ** -0.5
    xs = x * wavelength * g / np.sqrt((g * wavelength) ** 2 + 1.125 * radius**2 * (1 - cosine**2))
    secondary = (
        1
        + 2.12 * xs
        + (0.58 + 0.48 * cosine + 0.24 * cosine**2) * xs**2 / (1 + (0.02 - 0.025 * cosine) * xs)
    ) ** -0.5
    return primary * secondary


def main():  # noqa: PLR0914 - independent fit inputs and uncertainty quantities
    references = json.loads((HERE / 'fullprof.json').read_text())['cases']
    basic = HERE / 'projects/sc-neut-cwl_tbti_basic'
    source = HERE / 'fitting/fullprof' / PROJECT
    structure = source / 'project/structures/structure.edi'
    if structure.read_bytes() != (basic / 'structures/structure.edi').read_bytes():
        message = 'The extincted and unextincted structures must be identical'
        raise ValueError(message)
    basis_rows = references['sc-neut-cwl_tbti_basic']['calculated_rows']
    measured_rows = references[CASE]['input_rows']
    if [r['hkl'] for r in basis_rows] != [r[:3] for r in measured_rows]:
        message = 'The independent basis must preserve the measured reflection order'
        raise ValueError(message)
    basis_scale = float(
        re.search(
            r'^structure (\S+)$', (basic / 'experiments/experiment.edi').read_text(), re.MULTILINE
        )[1]
    )
    f2 = np.array([r['f2_calc'] for r in basis_rows]) / basis_scale
    rows = np.array(measured_rows)
    measured, sigma = rows[:, 3], rows[:, 4]
    a = float(re.search(r'_cell.length_a (\S+)', structure.read_text())[1])
    wavelength, mosaicity = 0.793, 35000.0
    cosine = 1 - wavelength**2 * np.sum(rows[:, :3] ** 2, axis=1) / (2 * a**2)

    def predicted(parameters):
        scale, radius = parameters
        return scale * f2 * correction(f2, cosine, wavelength, a**3, radius, mosaicity)

    def residual(parameters):
        return (predicted(parameters) - measured) / sigma

    fit = least_squares(
        residual,
        [4.1744, 10.0],
        bounds=(0, np.inf),
        jac='3-point',
        x_scale='jac',
        ftol=1e-13,
        xtol=1e-13,
        gtol=1e-11,
        max_nfev=1000,
    )
    if not fit.success or not np.isfinite(fit.x).all():
        message = f'Independent fit did not converge: {fit.message}'
        raise ValueError(message)
    reduced = float(np.dot(fit.fun, fit.fun) / (len(rows) - 2))
    normal = fit.jac.T @ fit.jac
    covariance = np.linalg.inv(normal) * reduced
    su = np.sqrt(np.diag(covariance))
    correlation = covariance / np.outer(su, su)
    # The predeclared objective budget is retained from the FullProf fit gates.
    quantities = {
        'n_free': {'value': 2, 'kind': 'reference', 'tol_abs': 0},
        'n_points_fitted': {'value': len(rows), 'kind': 'reference', 'tol_abs': 0},
        'param.scale.value': {
            'value': float(fit.x[0]),
            'kind': 'reference',
            'tol_abs': float(su[0]),
        },
        'param.domain_radius.value': {
            'value': float(fit.x[1]),
            'kind': 'reference',
            'tol_abs': float(su[1]),
        },
        'reduced_chi_square': {
            'value': reduced,
            'kind': 'reference',
            'tol_abs': 0.06,
            'tol_rel': 0.002,
        },
    }
    destination = HERE / 'fitting/becker-coppens' / PROJECT
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source / 'project', destination / 'project', dirs_exist_ok=True)
    inputs = [
        Path(__file__).resolve(),
        HERE / 'fullprof.json',
        structure,
        basic / 'experiments/experiment.edi',
        HERE / 'fullprof/sc-neut-cwl_tbti_basic/tbti.pcr',
        HERE / 'fullprof/sc-neut-cwl_tbti_basic/tbti.out',
        HERE / 'fullprof' / CASE / 'tbti.int',
    ]
    record = {
        'method': 'FullProf unextincted F2 plus Becker-Coppens spherical Gaussian closed form',
        'upstream_revision': 'cb2cda7be6117199be8f8cac0a666a7bccd32d90',
        'equations': 'https://doi.org/10.1107/S0567739474000337',
        'conventions': '../extinction.json and generate_projects.py; mosaicity uses pi/10800',
        'scipy_version': scipy.__version__,
        'numpy_version': np.__version__,
        'inputs_sha256': {
            str(p.relative_to(HERE)): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs
        },
        'basis_scale': basis_scale,
        'basis_rounding_absolute': 0.00005 / basis_scale,
        'wavelength': wavelength,
        'cell_a': a,
        'model': 'gauss',
        'mosaicity': mosaicity,
        'start': {'scale': 4.1744, 'radius': 10.0},
        'n_selected': len(rows),
        'n_free': 2,
        'parameters': [
            {'name': name, 'value': float(value), 'su': float(error)}
            for name, value, error in zip(('scale', 'radius'), fit.x, su, strict=True)
        ],
        'su_convention': 'sqrt(diag(inv(J.T @ J) * sum(r*r)/(N-p)))',
        'correlation': correlation.tolist(),
        'scaled_jacobian_condition': float(
            np.linalg.cond(fit.jac * np.linalg.norm(fit.jac, axis=0) ** -1)
        ),
        'converged': bool(fit.success),
        'termination': fit.message,
        'optimality': float(fit.optimality),
        'nfev': fit.nfev,
        'residual_sum': float(np.dot(fit.fun, fit.fun)),
        'reduced_chi_square': reduced,
        'rows': [
            {'hkl': r[:3], 'f2_bare': float(bare), 'f2_calc': float(calc)}
            for r, bare, calc in zip(measured_rows, f2, predicted(fit.x), strict=True)
        ],
    }
    (destination / 'reference.json').write_text(json.dumps(record, indent=2) + '\n')
    (destination / 'expected.json').write_text(
        json.dumps(
            {
                'schema': 1,
                'source': {
                    'engine': 'Becker-Coppens closed form on FullProf F2',
                    'artifact': 'reference.json',
                    'provenance': '../README.md',
                },
                'quantities': quantities,
            },
            indent=2,
        )
        + '\n'
    )
    print(
        json.dumps({
            k: record[k]
            for k in (
                'parameters',
                'reduced_chi_square',
                'correlation',
                'scaled_jacobian_condition',
            )
        })
    )


if __name__ == '__main__':
    main()
