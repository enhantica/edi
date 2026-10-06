#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Refine LBCO/HRPT constant-wavelength neutron data in two stages, to engine parity.

    pixi run core-build                                       # build the `edi._edi` extension once
    pixi run -e default python examples/fit_lbco_hrpt.py   # the vendored LBCO measurement

What it shows: edi driving and reporting a **constant-wavelength Rietveld refinement** — the
La0.5Ba0.5CoO3 pattern measured on HRPT@PSI — through the ordinary public ``import edi``
surface, and reaching **engine parity** with diffraction-lib's own recorded refinement of the
same data (``tests/fixtures/lbco_hrpt_baseline/baseline.json``, vendored byte-identical from
upstream —
see its ``PROVENANCE.md`` — key ``refine-lbco-hrpt-from-data``, that engine's own ``rtol``
0.02). Engine parity is the whole claim, and it is an agreement **of outputs, not of
protocols**: two independent engines, refining the same measurement along different routes
(spelled out below), land on the same three compared outputs within the tolerance the other
engine declared for itself. It asserts nothing about experimental correctness, and it does not
make either engine a reference standard.

The lesson is the **two-stage protocol** — and this docstring is the example's single
authoritative statement of why it is needed; other surfaces (the repository README's examples
row) link here rather than restating it. From the tutorial's plain starting values (``a`` 3.88 Å,
scale 10.0, zero-shift 0.6°, Caglioti ``u``/``v``/``w`` 0.1/-0.1/0.1, Lorentz ``y`` 0.1, all ADPs
0.5 Å²) the full free set does **not** refine in one shot — and the failure is **silent, not
loud**. Since crysta ``324a4ef3`` an unevaluable trial step is rejected per-probe instead of
aborting the fit, so the one-shot run no longer raises: measured on this example's own
``build_project()`` at that pin, it finishes ``DONE`` with no exception and no warning, in a
**wrong basin** — reduced χ² 23.136925, Rwp 0.305298, against the staged route's 1.297269 and
0.072291 from the same starts. That is cold-start basin selection with the CW profile free (open,
dataset-dependent), and this example neither fixes nor gates it. What a caller can do is read the
engine's boundary-contact counters, ``FitResultBase.unevaluable_trials`` /
``terminal_unevaluable_trials``: the wrong-basin run measured above rejects trial probes
throughout its descent and still does so in its final
iteration (both counters nonzero), while both stages of the staged route run boundary-free
(both 0). The escape is not better guesses — it is staging:

  stage A  free scale + the 5 background intensities + cell ``a`` + zero-shift, with the
           profile and ADPs held at their plain starts;
  stage B  release the full set (cell ``a``, 4 ADPs, zero-shift, ``u``/``v``/``w``/``y``,
           background, scale) from stage A's warm state — everything stage A refined
           carries forward (cell ``a``, scale, zero-shift **and** the five background
           intensities, written back onto the model), while the profile still starts at
           0.1/-0.1/0.1/0.1 and the ADPs at 0.5, and the identical free set that lands in
           the wrong basin above now converges in a handful of iterations.

Nothing here is pre-converged: the cell, ADP, scale, zero-shift and profile starts below are the
upstream tutorial's own in-code values; the five background node positions/starts are authored
from the fitless FullProf ``.pcr`` (the tutorial instead calls ``background.auto_estimate()``,
which edi does not have); and stage B's profile seed is untouched. The staging is the finding,
shown, not hidden.

The two routes to the compared numbers **differ**, deliberately. The upstream baseline records
the tutorial's *final saved state* at pin ``39ada82c``: an auto-estimated background, an
unconstrained fit, a **La/Ba ADP equality constraint**, a second fit, a **calculator switch to
``crysfml``**, and a third fit. This example refines unconstrained (La and Ba ADPs vary
independently), with the authored background, in the two stages above — so the engines' free
sets and starting states are **not** identical, and no sentence here claims they are. Shared:
the measurement bytes and the three compared outputs. That two differently-produced refinements
of the same data agree inside upstream's own ``rtol`` is precisely the point.

Inputs, all committed in this repository — the example runs with **no network access**:

- Measurement: ``knowledge/verification/fullprof/pd-neut-cwl_lbco-hrpt_basic/lbco.dat`` — 3098 rows
  of ``2theta  intensity  sigma``, vendored byte-identical from diffraction-lib (see
  ``fullprof/PROVENANCE.md``). The FullProf project it sits in is *fitless by contract* (zero
  refined parameters); this example takes only the **measurement** and the five background
  node **positions/starts** from it, never a refined-value oracle.
- Parity reference: ``tests/fixtures/lbco_hrpt_baseline/baseline.json`` — diffraction-lib's
  record of its own tutorial refinement, with its own tolerance, vendored **byte-identical** from
  upstream pin ``39ada82c`` (see ``tests/fixtures/lbco_hrpt_baseline/PROVENANCE.md``; the
  upstream path,
  ``tests/tutorials/baseline.json``, lives in a git-ignored study clone and is therefore not
  present in a clean checkout).

Compared under that ``rtol`` 0.02: refined cell ``a``, scale, and Rwp (against the baseline's
``wr_factor_all``). The baseline's ``r_factor_all`` (unweighted R) has no counterpart on edi's
``FitResultBase`` and is not compared. Reduced χ² is **reported but excluded** from the parity
check: the two engines weight and count differently enough that edi's converged 1.2973 sits
2.97 % from the baseline's 1.2599 — outside the 2 % bound the refined *parameters* meet — and
widening a tolerance to admit it would assert nothing. The exclusion is stated, not hidden.

Scattering-length table: the engine's **default** table, matching the comparison — the upstream
tutorial also refines on its engine's defaults. Measured at authoring time, supplying FullProf's
explicit lengths instead moves scale by 0.016 % and cell ``a`` by 3e-7 Å: far inside the parity
bound either way, so the default is pinned for symmetry with what the baseline itself did.
"""

from __future__ import annotations

import json
from pathlib import Path

import edi
from edi import ExperimentFactory, StructureFactory

REPO = Path(__file__).resolve().parents[1]
MEASUREMENT = (
    REPO / 'knowledge' / 'verification' / 'fullprof' / 'pd-neut-cwl_lbco_basic' / 'lbco.dat'
)
BASELINE = (
    Path(__file__).resolve().parents[1]
    / 'tests'
    / 'fixtures'
    / 'lbco_hrpt_baseline'
    / 'baseline.json'
)
BASELINE_KEY = 'refine-lbco-hrpt-from-data'


def load_measurement(path: Path) -> tuple[list[float], list[float], list[float]]:
    """The vendored ``2theta  intensity  sigma`` columns, parsed with no dependencies."""
    grid: list[float] = []
    observed: list[float] = []
    sigma: list[float] = []
    for line in path.read_text(encoding='utf-8').splitlines():
        columns = line.split()
        if len(columns) != 3:
            continue
        grid.append(float(columns[0]))
        observed.append(float(columns[1]))
        sigma.append(float(columns[2]))
    return grid, observed, sigma


def build_project() -> edi.Project:
    """LBCO + HRPT, nothing pre-converged.

    Cell/ADP/scale/zero-shift/profile starts are the upstream tutorial's in-code values; the five
    background nodes are ``.pcr``-authored (module docstring — edi has no ``auto_estimate()``).
    """
    structure = StructureFactory.from_dict({
        'space_group': {'name_h_m': 'P m -3 m'},
        'cell': {'length_a': {'value': 3.88, 'free': False}},
        'atom_sites': [
            {
                'id': 'La',
                'type_symbol': 'La',
                'wyckoff_letter': 'a',
                'fract': (0.0, 0.0, 0.0),
                'occupancy': 0.5,
                'adp_iso': {'value': 0.5, 'free': False},
            },
            {
                'id': 'Ba',
                'type_symbol': 'Ba',
                'wyckoff_letter': 'a',
                'fract': (0.0, 0.0, 0.0),
                'occupancy': 0.5,
                'adp_iso': {'value': 0.5, 'free': False},
            },
            {
                'id': 'Co',
                'type_symbol': 'Co',
                'wyckoff_letter': 'b',
                'fract': (0.5, 0.5, 0.5),
                'occupancy': 1.0,
                'adp_iso': {'value': 0.5, 'free': False},
            },
            {
                'id': 'O',
                'type_symbol': 'O',
                'wyckoff_letter': 'c',
                'fract': (0.0, 0.5, 0.5),
                'occupancy': 1.0,
                'adp_iso': {'value': 0.5, 'free': False},
            },
        ],
        # No 'scattering_lengths_fm': the engine's default table, pinned by the argument above.
    })
    structure.name = 'lbco'

    # The five background nodes are the vendored .pcr's linear-interpolation set — positions and
    # starting intensities only, from a FullProf project that refined nothing (fitless by
    # contract). edi has no auto-estimator; a CW background is authored explicitly.
    experiment = ExperimentFactory.from_dict({
        'experiment_type': {'beam_mode': 'constant wavelength'},
        'peak': {
            'type': 'cwl-tch-pseudo-voigt',
            'cutoff_fwhm': 30.0,
            'broad_gauss_u': {'value': 0.1, 'free': False},
            'broad_gauss_v': {'value': -0.1, 'free': False},
            'broad_gauss_w': {'value': 0.1, 'free': False},
            'broad_lorentz_x': {'value': 0.0, 'free': False},
            'broad_lorentz_y': {'value': 0.1, 'free': False},
        },
        'instrument': {
            'setup_wavelength': 1.494,
            'calib_twotheta_offset': {'value': 0.6, 'free': False},
        },
        'linked_structure': {'scale': {'value': 10.0, 'free': False}},
        'background': [
            (10.0, {'value': 169.0, 'free': False}),
            (30.0, {'value': 164.1, 'free': False}),
            (50.0, {'value': 166.91, 'free': False}),
            (110.0, {'value': 175.27, 'free': False}),
            (165.0, {'value': 174.56, 'free': False}),
        ],
    })
    experiment.name = 'hrpt'
    experiment.excluded_regions = [(0.0, 5.0), (165.0, 180.0)]

    project = edi.Project()
    project.structure = structure
    project.experiment = experiment
    return project


def release(project: edi.Project, *, full: bool) -> None:
    """Flag the stage's free set. ``full=False`` is stage A; ``full=True`` releases everything.

    Stage A: scale, the five background intensities, cell ``a``, zero-shift.
    Stage B: the same, plus the four ADPs and the Gaussian U/V/W + Lorentz Y profile — the exact
    free set that raises when attempted cold in one shot.
    """
    structure, experiment = project.structure, project.experiment

    def free(owner: object, name: str, *, released: bool) -> None:
        parameter = getattr(owner, name)
        parameter.free = released
        setattr(owner, name, parameter)

    free(structure.cell, 'length_a', released=True)
    free(experiment.instrument, 'calib_twotheta_offset', released=True)
    free(experiment.linked_structure, 'scale', released=True)
    # The collections are live views — a mutation through them reaches the model
    # directly, so the old copy-out/write-back idiom is retired.
    for point in experiment.background:
        point.intensity.free = True

    for site in structure.atom_sites:
        site.adp_iso.free = full
    for name in ('broad_gauss_u', 'broad_gauss_v', 'broad_gauss_w', 'broad_lorentz_y'):
        free(experiment.peak, name, released=full)


def fit_stage(
    label: str, project: edi.Project, data: tuple[list[float], list[float], list[float]]
) -> edi.FitResultBase:
    grid, observed, sigma = data
    print(f'{label}:')
    outcome = project.fit(
        grid,
        observed,
        sigma,
        on_iteration=lambda record: print(
            f'  iteration {record.iteration:2d}  Rwp {record.rwp:.4f}'
        ),
    )
    print(
        f'  {outcome.status.name.lower()} after {outcome.iterations} iterations: '
        f'Rwp {outcome.rwp:.6f}, reduced chi2 {outcome.reduced_chi_square:.6f}'
    )
    return outcome


def main() -> int:
    data = load_measurement(MEASUREMENT)
    print(
        f'measurement: {len(data[0])} points, {data[0][0]:g}-{data[0][-1]:g} deg 2theta '
        f'(committed in-repo; no network)'
    )

    project = build_project()

    # Stage A — profile and ADPs held at their plain starts; warm up scale/background/cell/zero.
    release(project, full=False)
    fit_stage('stage A (scale + background + cell a + zero-shift)', project, data)

    # Stage B — the full free set, released from stage A's warm state: everything stage A
    # refined carries forward (cell a, scale, zero-shift and the five background intensities,
    # written back onto the model), while the profile still starts at the tutorial's
    # 0.1/-0.1/0.1/0.1 and the ADPs at 0.5. Attempted cold, this exact set lands silently in
    # a wrong basin (docstring).
    release(project, full=True)
    outcome = fit_stage('stage B (full free set from the warm state)', project, data)

    # Engine parity: compare against diffraction-lib's own committed refinement of this data,
    # under that engine's own rtol. Nothing below was produced by edi's engine except the
    # candidate values themselves.
    baseline = json.loads(BASELINE.read_text(encoding='utf-8'))[BASELINE_KEY]
    rtol = baseline['rtol']
    comparisons = (
        (
            'cell a (angstrom)',
            project.structure.cell.length_a.value,
            baseline['parameters']['lbco.cell.length_a'],
        ),
        (
            'scale',
            project.experiment.linked_structure.scale.value,
            baseline['parameters']['hrpt.linked_structure.lbco.scale'],
        ),
        ('Rwp vs wr_factor_all', outcome.rwp, baseline['wr_factor_all']),
    )

    print()
    print(f'engine parity vs diffraction-lib baseline "{BASELINE_KEY}" (its own rtol {rtol}):')
    failures = 0
    for label, ours, theirs in comparisons:
        relative = abs(ours - theirs) / abs(theirs)
        verdict = 'within' if relative <= rtol else 'OUTSIDE'
        failures += verdict != 'within'
        print(
            f'  {label:24s} edi {ours:.6f}  baseline {theirs:.6f}  '
            f'relative {relative:.2%}  {verdict}'
        )

    # Reported, deliberately not compared: the engines' reduced chi2 definitions differ enough
    # (weighting, point/parameter counting) that edi's converged value sits ~3 % off — outside
    # the 2 % the refined parameters meet — and no honest single tolerance covers both. The
    # baseline's unweighted r_factor_all has no FitResultBase counterpart and is likewise named,
    # not compared.
    chi2 = outcome.reduced_chi_square
    theirs = baseline['reduced_chi_square']
    print(
        f'  reduced chi2 (reported, excluded from parity) edi {chi2:.6f}  '
        f'baseline {theirs:.6f}  relative {abs(chi2 - theirs) / theirs:.2%}'
    )

    if failures:
        print(f'ENGINE PARITY FAILED on {failures} quantity(ies)')
        return 1
    print('engine parity reached on all three compared quantities')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
