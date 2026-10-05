"""Freeze CrySPY's width-convention displacement; no product or data fitting."""

import argparse
import hashlib
import importlib.util
import itertools
import json
import sys
import types
from importlib import metadata
from pathlib import Path

import numpy as np
from scipy.optimize import minimize_scalar


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_functions(source):
    package = types.ModuleType('beer_cryspy')
    package.__path__ = [str(source)]
    sys.modules[package.__name__] = package
    modules = {}
    for name in ('powder_diffraction_cutoff', 'powder_diffraction_tof'):
        spec = importlib.util.spec_from_file_location(f'beer_cryspy.{name}', source / f'{name}.py')
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        modules[name] = module
    return modules['powder_diffraction_tof']


def displacement(tof, home, stage, index, bank):  # noqa: PLR0914 -- one physical profile calculation
    path = home / f'reference-run/stage-{index}/experiments/{bank}.edi'
    data, reflections = [], []
    for line in path.read_text().splitlines():
        fields = line.split()
        if len(fields) == 8 and fields[-1] == 'incl':
            data.append([float(fields[0]), float(fields[4])])
        elif len(fields) == 10 and fields[1] in {'ferrite', 'austenite'}:
            reflections.append(fields)
    if not data or not reflections or {row[1] for row in reflections} != {'ferrite', 'austenite'}:
        raise ValueError('Both independent phases and included external rows are required')
    time, error = np.array(data).T
    if not np.all(np.isfinite(time)) or not np.all(np.isfinite(error) & (error > 0)):
        raise ValueError('The saved external grid and weighting errors must be finite and valid')
    parameters = stage['all_parameters']

    def value(key):
        return parameters[key]['value']

    zero, linear, quadratic = [
        value(f'{bank}.instrument.d_to_tof_{field}') for field in ('offset', 'linear', 'quadratic')
    ]
    sigmas = [value(f'{bank}.peak.broad_gauss_sigma_{i}') for i in range(3)]
    gammas = [value(f'{bank}.peak.broad_lorentz_gamma_{i}') for i in range(3)]
    d_time = tof.calc_d_by_time_for_thermal_neutrons(time, zero, linear, quadratic)
    point_sigma, point_gamma = tof.calc_sigma_gamma(d_time, *sigmas, *gammas)
    point_profile = np.zeros_like(time)
    components = []
    for fields in reflections:
        phase = fields[1]
        hkl = tuple(int(v) for v in fields[4:7])
        # Cubic m-3m orbit, including Friedel partners, for both saved Fe phases.
        multiplicity = len({
            tuple(sign * v for sign, v in zip(signs, permutation, strict=True))
            for permutation in itertools.permutations(hkl)
            for signs in itertools.product((-1, 1), repeat=3)
        })
        d = value(f'{phase}.cell.length_a') / np.sqrt(sum(v * v for v in hkl))
        centre = float(
            tof.calc_time_for_thermal_neutrons_by_d(np.array([d]), zero, linear, quadratic)[0]
        )
        # Saved external F² includes the phase's thermal factor. A common
        # Lorentz/polarization factor cancels from this profile-displacement fit.
        amplitude = (
            value(f'{bank}.linked_structure.{phase}.scale')
            * multiplicity
            * float(fields[8])
            * d**4
        )
        point_profile += (
            amplitude
            * tof.tof_non_convoluted_pseudo_voigt(
                point_sigma, point_gamma, time, np.array([centre])
            )[:, 0]
        )
        sigma, gamma = tof.calc_sigma_gamma(np.array([d]), *sigmas, *gammas)
        components.append((centre, sigma, gamma, amplitude))

    def reflection_profile(delta):
        return sum(
            amplitude
            * tof.tof_non_convoluted_pseudo_voigt(sigma, gamma, time, np.array([centre + delta]))[
                :, 0
            ]
            for centre, sigma, gamma, amplitude in components
        )

    def match(target):
        def cost(delta):
            return float(np.sum(((reflection_profile(delta) - target) / error) ** 2))

        result = minimize_scalar(
            cost, bounds=(-2.0, 2.0), method='bounded', options={'xatol': 1e-9}
        )
        if not result.success or abs(result.x) >= 1.9:
            raise ValueError('The independent convention displacement is not bracketed')
        return float(result.x), cost(0), cost(result.x)

    later, before, after = match(point_profile)
    identity, _, _ = match(reflection_profile(0))
    if later <= 0 or abs(identity) > 1e-6 or after >= before:
        raise ValueError('The width convention must shift later; fixed widths must not shift')
    return {
        'signed_shift_us': -later,
        'reflection_width_control_us': identity,
        'cost_at_zero': before,
        'cost_at_displacement': after,
        'included_points': len(time),
        'reflections': len(components),
        'external_input_sha256': digest(path),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cryspy-functions', type=Path, required=True)
    parser.add_argument('--home', type=Path, default=Path(__file__).with_name('beer'))
    args = parser.parse_args()
    ref = json.loads((args.home / 'reference.json').read_text())
    distribution = metadata.distribution('cryspy')
    if distribution.version != ref['versions']['cryspy'] or not (
        args.cryspy_functions.resolve()
        == distribution.locate_file('cryspy/A_functions_base').resolve()
    ):
        raise ValueError('Authoring must use the captured CrySPY version and its own sources')
    tof = load_functions(args.cryspy_functions)
    record = {
        'reference_sha256': digest(args.home / 'reference.json'),
        'cryspy_version': ref['versions']['cryspy'],
        'author_sha256': digest(Path(__file__)),
        'numerical_versions': {name: metadata.version(name) for name in ('numpy', 'scipy')},
        'function_sha256': {
            p.name: digest(p)
            for p in (
                args.cryspy_functions / 'powder_diffraction_cutoff.py',
                args.cryspy_functions / 'powder_diffraction_tof.py',
            )
        },
        'command': (
            '../diffraction-lib/.pixi/envs/default/bin/python '
            'tests/fixtures/multiphase/author_beer_offsets.py --cryspy-functions '
            '../diffraction-lib/.pixi/envs/default/lib/python3.14/site-packages/'
            'cryspy/A_functions_base'
        ),
        'definition': (
            'signed shift = minus the displacement of a reflection-width CrySPY '
            'profile minimizing inverse-variance weighted squared differences '
            'from the point-width CrySPY profile, on all included external rows. '
            'Only this displacement varies; no measured intensities, product '
            'outputs or product imports enter the objective. Expected offset '
            '= raw reference offset minus signed shift. External SUs are unchanged.'
        ),
        'stages': [
            {
                bank: displacement(tof, args.home, stage, index, bank)
                for bank in ('expt_n2', 'expt_s2')
            }
            for index, stage in enumerate(ref['stages'], 1)
        ],
    }
    (args.home / 'offset-convention.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record, indent=2), flush=True)


if __name__ == '__main__':
    main()
