# %% [markdown]
# # Ferrite and austenite — powder neutron TOF — two phases, two banks
#
# Verifies the **sum of two phases** in one pattern: ferrite (`I m -3 m`) and austenite
# (`F m -3 m`), both Fe, against two BEER (ESS) time-of-flight banks at 90°, with the
# time-of-flight pseudo-Voigt profile. Each bank is the sum of both phases' patterns, each with
# its own scale, over one shared background.
#
# **The reference is CrySPY**, not FullProf: the diffraction-lib tutorial
# `calibrate-beer-ess.py`, fitted with CrySPY 0.12.1, recorded its fitted values and its
# calculated pattern for each bank (`tests/fixtures/multiphase/beer/`, `PROVENANCE.md` there).
# Nothing is fitted here: every parameter is set to CrySPY's first-stage value and the pattern
# is calculated once.
#
# **Scale convention.** edi's time-of-flight intensity carries sin θ of the bank (FullProf's
# convention, as the `pd-neut-tof_Fe_pseudo-voigt` page shows with FullProf's own scale);
# CrySPY's does not. The same pattern therefore needs each phase scale divided by sin θ_bank,
# here sin 45°. That is the only conversion.
#
# **Parameter uncertainties.** CrySPY reports each fitted value with its standard uncertainty
# (`reference.json`). This page sets the values and compares patterns; a fit of the same
# project is held to those values within one uncertainty each, the scales after the sin θ
# conversion.
#
# **The bounds are labelled regression pins**: this page's own measured closeness with stated
# headroom (profile difference 0.12 %, max deviation 0.11 %, area ratio 0.999998, correlation
# 0.9999992 in both banks).

# %%
import json
import math
import shutil
import tempfile
from pathlib import Path

import numpy as np

from edi import Project
from edi import verification as verify

# %% [markdown]
# ## Load the CrySPY reference

# %%
ROOT = Path(verify.bundled_reference_dir()).parents[2]
REFERENCE_DIR = ROOT / 'tests/fixtures/multiphase/beer'
REFERENCE = json.loads((REFERENCE_DIR / 'reference.json').read_text())
CRYSPY_VALUES = REFERENCE['stages'][0]['all_parameters']
CRYSPY_LABEL = f'CrySPY {REFERENCE["versions"]["cryspy"]}'
# The delivered CLI project, the tutorial's starting point (a copy of the reference's own).
PROJECT_DIR = ROOT / 'docs/user/cli/pd-neut-tof_ferrite-austenite-beer_joint/project'
BANKS = ('expt_n2', 'expt_s2')


def cryspy_calculated(bank: str) -> np.ndarray:
    """Return the time of flight and CrySPY's calculated intensity of one bank, as two rows."""
    stage = REFERENCE_DIR / 'reference-run/stage-1/experiments' / f'{bank}.edi'
    rows = []
    for line in stage.read_text().splitlines():
        fields = line.split()
        if len(fields) == 8 and fields[-1] in {'incl', 'excl'}:
            rows.append((float(fields[0]), float(fields[5])))
    return np.array(rows).T


# %% [markdown]
# ## Build the project at CrySPY's values

# %%
work = Path(tempfile.mkdtemp())
shutil.copytree(PROJECT_DIR, work / 'project')
project = Project.load(str(work / 'project'))


def value(key: str) -> float:
    """Return CrySPY's first-stage value of one parameter."""
    return float(CRYSPY_VALUES[key]['value'])


def sin_theta(bank: str) -> float:
    """Return sin θ of a bank, from the reference's geometry, never from the project under test."""
    return math.sin(math.radians(value(f'{bank}.instrument.twotheta_bank') / 2))


for name in project.structures.names:
    structure = project.structures[name]
    structure.cell.length_a.value = value(f'{name}.cell.length_a')
    for site in structure.atom_sites:
        site.adp_iso.value = value(f'{name}.atom_site.{site.id}.adp_iso')

PROFILE_FIELDS = (
    'broad_gauss_sigma_0',
    'broad_gauss_sigma_1',
    'broad_gauss_sigma_2',
    'broad_lorentz_gamma_0',
    'broad_lorentz_gamma_1',
    'broad_lorentz_gamma_2',
)
for bank in BANKS:
    experiment = project.experiments[bank]
    for link in experiment.linked_structures:
        scale = value(f'{bank}.linked_structure.{link.structure_id}.scale')
        link.scale.value = scale / sin_theta(bank)
    for field in PROFILE_FIELDS:
        getattr(experiment.peak, field).value = value(f'{bank}.peak.{field}')
    experiment.instrument.calib_d_to_tof_offset.value = value(f'{bank}.instrument.d_to_tof_offset')
    for index, point in enumerate(experiment.background, start=1):
        point.intensity.value = value(f'{bank}.background.{index}.intensity')

# %% [markdown]
# ## Calculate the patterns

# %%
project.analysis.calculate()

# %% [markdown]
# ## edi-crysta VS CrySPY, each bank

# %%
LABEL_ED_CRYSTA = verify.engine_label('crysta')
rows = []
for bank in BANKS:
    experiment = project.experiments[bank]
    x, calc_cryspy = cryspy_calculated(bank)
    if not np.allclose(x, experiment.data.time_of_flight):
        msg = f'{bank}: the reference grid differs from the project data'
        raise ValueError(msg)
    calc_ed_crysta = verify.restrict_to_included(experiment, experiment.data.intensity_calc)
    verify.plot_pattern_comparison(
        experiment,
        reference=calc_cryspy,
        candidate=calc_ed_crysta,
        reference_label=CRYSPY_LABEL,
        candidate_label=LABEL_ED_CRYSTA,
    )
    rows.append((
        f'{bank}: {LABEL_ED_CRYSTA} vs {CRYSPY_LABEL}',
        verify.restrict_to_included(experiment, calc_cryspy),
        calc_ed_crysta,
    ))

# %%
verify.assert_patterns_agree(
    rows,
    tolerances=verify.AgreementTolerances(
        max_profile_difference_percent=0.2,
        max_deviation_percent=0.2,
        min_intensity_ratio=0.9998,
        max_intensity_ratio=1.0002,
        min_correlation=0.999998,
    ),
)

# %% [markdown]
# ## Fit from the tutorial's start and compare with CrySPY's fit
#
# The delivered project is fitted jointly from its starting values, as the tutorial's first
# fit is. Every parameter CrySPY fitted must land within one of CrySPY's standard uncertainties
# of CrySPY's value, as the agreement gates require; a scale is compared after the sin θ
# conversion, with the bank angle taken from the reference.


# %%
def parameter(fitted: Project, key: str) -> object:
    """Return the parameter a `reference.json` key names in `fitted`."""
    block, category, *rest = key.split('.')
    if category == 'atom_site':
        site = next(s for s in fitted.structures[block].atom_sites if s.id == rest[0])
        return getattr(site, rest[1])
    if category == 'cell':
        return getattr(fitted.structures[block].cell, rest[0])
    experiment = fitted.experiments[block]
    if category == 'linked_structure':
        link = next(r for r in experiment.linked_structures if r.structure_id == rest[0])
        return getattr(link, rest[1])
    if category == 'background':
        return getattr(experiment.background[int(rest[0]) - 1], rest[1])
    if category == 'instrument':
        return getattr(experiment.instrument, 'calib_' + rest[0])
    return getattr(getattr(experiment, category), rest[0])


fit_dir = work / 'fit'
shutil.copytree(PROJECT_DIR, fit_dir)
fitted = Project.load(str(fit_dir))
fitted.analysis.fit()

misses = []
for key, record in REFERENCE['stages'][0]['parameters'].items():
    reference, uncertainty = float(record['value']), float(record['su'])
    if '.linked_structure.' in key:
        factor = sin_theta(key.split('.')[0])
        reference, uncertainty = reference / factor, uncertainty / factor
    actual = parameter(fitted, key).value
    if abs(actual - reference) > uncertainty:
        misses.append(f'{key}: {actual:.6g} vs {reference:.6g} +/- {uncertainty:.2g}')
assert not misses, '\n'.join(['outside one standard uncertainty:', *misses])  # noqa: S101
