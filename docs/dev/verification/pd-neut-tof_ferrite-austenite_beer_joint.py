# %% [markdown]
# # Ferrite and austenite — powder neutron TOF — two phases, two banks
#
# The **sum of two phases** in one pattern: ferrite (`I m -3 m`) and austenite (`F m -3 m`),
# both Fe, against two BEER (ESS) time-of-flight banks at 90°, with the time-of-flight
# pseudo-Voigt profile. Each bank is the sum of both phases' patterns, each with its own scale,
# over one shared background.
#
# **No reference comparison yet.** This page calculates and fits the delivered project
# `pd-neut-tof_ferrite-austenite-beer_joint` and shows the result; it checks only that both
# phases contribute to both banks and that the fit improves the agreement. The owner's FullProf
# project for these data is kept beside the other FullProf references; the comparison against it
# needs a constraint the fit does not support yet (one B iso shared by both Fe sites) and comes
# with that.

# %%
import shutil
import tempfile
from pathlib import Path

import numpy as np

from edi import Project
from edi import verification as verify

# %% [markdown]
# ## Load the delivered project

# %%
ROOT = Path(verify.bundled_reference_dir()).parents[2]
PROJECT_DIR = ROOT / 'docs/user/cli/pd-neut-tof_ferrite-austenite-beer_joint/project'
BANKS = ('expt_n2', 'expt_s2')

work = Path(tempfile.mkdtemp())
shutil.copytree(PROJECT_DIR, work / 'project')
project = Project.load(str(work / 'project'))


def rwp(fitted: Project) -> float:
    """Return the weighted profile R-factor over both banks' included points."""
    numerator = denominator = 0.0
    for bank in BANKS:
        experiment = fitted.experiments[bank]
        measured = verify.restrict_to_included(experiment, experiment.data.intensity_meas)
        su = verify.restrict_to_included(experiment, experiment.data.intensity_meas_su)
        calculated = verify.restrict_to_included(experiment, experiment.data.intensity_calc)
        numerator += float(np.nansum(((measured - calculated) / su) ** 2))
        denominator += float(np.nansum((measured / su) ** 2))
    return float(np.sqrt(numerator / denominator))


# %% [markdown]
# ## Calculate at the starting values

# %%
project.analysis.calculate()
start = rwp(project)
for bank in BANKS:
    experiment = project.experiments[bank]
    structures = {link.structure_id for link in experiment.linked_structures}
    if structures != {'ferrite', 'austenite'}:
        msg = f'{bank}: expected both phases linked, found {sorted(structures)}'
        raise ValueError(msg)
print(f'Rwp at the starting values: {start:.4f}')

# %% [markdown]
# ## Fit both banks jointly

# %%
project.analysis.fit()
fitted = rwp(project)
print(f'Rwp after the joint fit: {fitted:.4f}')
if not fitted < start:
    msg = f'the fit did not improve the agreement ({start:.4f} -> {fitted:.4f})'
    raise ValueError(msg)

# %%
for bank in BANKS:
    experiment = project.experiments[bank]
    verify.plot_pattern_comparison(
        experiment,
        reference=verify.restrict_to_included(experiment, experiment.data.intensity_meas),
        candidate=verify.restrict_to_included(experiment, experiment.data.intensity_calc),
        reference_label='measured',
        candidate_label=verify.engine_label('crysta'),
    )
