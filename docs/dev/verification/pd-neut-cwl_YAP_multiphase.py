# %% [markdown]
# # YAlO3 and Al2O3 — powder neutron CW — two phases
#
# The **sum of two phases** in one constant-wavelength neutron pattern: YAlO3 (`P b n m`) and
# corundum Al2O3 (`R -3 c`, hexagonal axes) on SPODI (FRM II), against the owner's FullProf
# project for these data. Both phases share one profile, FullProf's **Npr 5 pseudo-Voigt**
# (`cwl-pseudo-voigt-berar-baldinozzi`): one Caglioti width `H² = U tan²θ + V tanθ + W` and a
# constant mixing η (FullProf's slope X is fixed at 0), with **Bérar-Baldinozzi** asymmetry below
# `AsyLim` = 160° and the cylinder absorption muR = 0.0221 (`cylinder-hewat`).
#
# **The reference** is FullProf's verification twin of the owner's fitting project
# (`pd-neut-cwl_yap-spodi_3k`): the fitted state with every parameter fixed, the scales fitted
# alone once. edi calculates at those parameters, loaded from the delivered CLI project
# `pd-neut-cwl_yap-spodi_3k`, and the Bragg-only profiles are compared.
#
# **FullProf's asymmetry coefficients mean something else.** As inferred in diffraction-lib issue
# 166 from FullProf's calculated output, FullProf uses the opposite sign of `z` and a different
# second function, so its Asy1..Asy4 enter through the inferred map
# `(-P1 - 3·P2, -P2, -P3 - 3·P4, -P4)`. The map is not exact, so the asymmetry is the one part of
# this model that is not FullProf's; the project's fit refines it in edi's convention.
#
# **The bounds are labelled regression pins** — this page's own measured closeness with stated
# headroom:
#
# | comparison | profile diff | max deviation | area ratio | correlation |
# | --- | --- | --- | --- | --- |
# | FullProf, both phases (gated) | 0.25 % | 1.64 % | 0.99984 | 0.9999959 |

# %%
import shutil
import tempfile
from pathlib import Path

from edi import Parameter
from edi import Project
from edi import verification as verify

# %% [markdown]
# ## Load the references

# %%
ROOT = Path(verify.bundled_reference_dir()).parents[2]
PROJECT_DIR = ROOT / 'docs/user/cli/pd-neut-cwl_yap-spodi_3k/project'
FULLPROF_PROJECT_DIR = 'pd-neut-cwl_yap-spodi_3k'
FULLPROF_PRF_FILE = 'yap_3k.prf'
FULLPROF_SUM_FILE = 'yap_3k.sum'
FULLPROF_BAC_FILE = 'yap_3k.bac'
FULLPROF_LABEL = verify.fullprof_label(FULLPROF_PROJECT_DIR, FULLPROF_SUM_FILE)

# The verification twin's values that differ from the fitting project's (its .pcr).
FULLPROF_ZERO = 0.00146  # FullProf Zero
FULLPROF_SCALES = {'YAlO3': 27.89617, 'Al2O3': 0.1891413}  # FullProf Scale, scale-fit-2.out
FULLPROF_YALO3_A = 5.172420  # FullProf a of phase 1

x, calc_fullprof = verify.load_fullprof_calc_profile(
    FULLPROF_PROJECT_DIR,
    FULLPROF_PRF_FILE,
    FULLPROF_BAC_FILE,
    FULLPROF_ZERO,
)

# %% [markdown]
# ## Load the delivered project at FullProf's parameters
#
# The background is left out, as the reference profile is Bragg-only.

# %%
work = Path(tempfile.mkdtemp())
shutil.copytree(PROJECT_DIR, work / 'project')
project = Project.load(str(work / 'project'))
experiment = project.experiments['spodi']
for link in experiment.linked_structures:
    link.scale = Parameter(FULLPROF_SCALES[link.structure_id])
project.structures['YAlO3'].cell.length_a = Parameter(FULLPROF_YALO3_A)
experiment.background = []
verify.set_reference_as_measured(experiment, x, calc_fullprof)

# %% [markdown]
# ## edi-crysta VS FullProf

# %%
project.analysis.calculate()
calc_ed_crysta = verify.restrict_to_included(experiment, experiment.data.intensity_calc)
reference = verify.restrict_to_included(experiment, calc_fullprof)
LABEL_ED_CRYSTA = verify.engine_label('crysta')

verify.plot_pattern_comparison(
    experiment,
    reference=reference,
    candidate=calc_ed_crysta,
    reference_label=FULLPROF_LABEL,
    candidate_label=LABEL_ED_CRYSTA,
)

# %%
print(verify.pattern_closeness(reference, calc_ed_crysta))
verify.assert_patterns_agree(
    [(f'{LABEL_ED_CRYSTA} vs {FULLPROF_LABEL}', reference, calc_ed_crysta)],
    tolerances=verify.AgreementTolerances(
        max_profile_difference_percent=0.4,
        max_deviation_percent=2.5,
        min_intensity_ratio=0.9995,
        max_intensity_ratio=1.0005,
        min_correlation=0.99999,
    ),
)
