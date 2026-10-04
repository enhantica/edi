# %% [markdown]
# # LaB6 — powder neutron CW — absorption
#
# The LaB6 baseline with only the Debye-Scherrer cylindrical absorption
# correction (Hewat) enabled: `_absorption.type cylinder-hewat` with
# μR = 0.7 (FullProf `muR`), CW face of the absorption slot.
#
# **Refinement:** none — every parameter is taken from the FullProf
# reference; only the calculated patterns are compared.
#
# **Application convention.** edi/crysta apply the absorption factor
# **per reflection**, at each reflection's own Bragg θ — because the
# physics depends on the reflection's diffraction angle and the μR
# analytical-derivative column rides the reflection. diffraction-lib
# applies the same Hewat factor **pointwise on the 2θ grid**. This page
# shows **both** against the FullProf reference: at this pattern's
# μR = 0.7 the two sit within 0.09 % of each other and the
# per-reflection application matches FullProf slightly *better*
# (integrated-intensity ratio 0.99947 vs 0.99873) — consistent with
# FullProf's own AC correction of per-reflection intensities. The gap
# between the conventions grows with μR (measured on the LBCO pattern
# at μR = 1.2 it exceeds that page's tolerance family), so the two
# conventions are gated separately below rather than averaged over.
#
# **The bounds are labelled regression pins** — this page's own measured
# closeness with stated headroom.

# %%
import numpy as np

from edi import ExperimentFactory
from edi import Parameter
from edi import Project
from edi import StructureFactory
from edi import verification as verify

# %% [markdown]
# ## Load the FullProf reference

# %%
FULLPROF_PROJECT_DIR = 'pd-neut-cwl_lab6-echidna_absorption'
FULLPROF_PRF_FILE = 'ECH0030684_LaB6_1p622A_absorption.prf'
FULLPROF_SUM_FILE = 'ECH0030684_LaB6_1p622A_absorption.sum'
FULLPROF_BAC_FILE = 'ECH0030684_LaB6_1p622A_absorption.bac'
FULLPROF_LABEL = verify.fullprof_label(FULLPROF_PROJECT_DIR, FULLPROF_SUM_FILE)

# Structure
FULLPROF_SPACE_GROUP = 'P m -3 m'  # FullProf Space group symbol
FULLPROF_CELL_LENGTH_A = 4.156885  # FullProf a
FULLPROF_ATOM_SITES = [
    # FullProf Atom, Typ, Wyckoff, (X, Y, Z), Occ (chemical), Biso
    ('La', 'La', 'a', (0.0, 0.0, 0.0), 1.0, 0.25812),
    ('B', 'B', 'f', (0.19972, 0.5, 0.5), 1.0, 0.11925),
]
# Experiment
FULLPROF_ZERO = -0.45778  # FullProf Zero
FULLPROF_SCALE = 42.98374  # FullProf Scale
FULLPROF_WAVELENGTH = 1.623899  # FullProf Lambda
FULLPROF_U = 0.143431  # FullProf U
FULLPROF_V = -0.523140  # FullProf V
FULLPROF_W = 0.590412  # FullProf W
FULLPROF_X = 0.0  # FullProf X
FULLPROF_Y = 0.054515  # FullProf Y
FULLPROF_WDT = 12.0  # FullProf Wdt
FULLPROF_MU_R = 0.7  # FullProf muR (Absorption correction (AC), muR-eff)
FULLPROF_EXCLUDED_REGIONS = [(0.0, 10.0), (164.0, 180.0)]  # FullProf Excluded regions

x, calc_fullprof = verify.load_fullprof_calc_profile(
    FULLPROF_PROJECT_DIR,
    FULLPROF_PRF_FILE,
    FULLPROF_BAC_FILE,
    FULLPROF_ZERO,
)

# %% [markdown]
# ## Define the structure

# %%
structure = StructureFactory.from_dict({
    'name': 'lab6',
    'space_group': {'name_h_m': FULLPROF_SPACE_GROUP},
    'cell': {'length_a': FULLPROF_CELL_LENGTH_A},
    'atom_sites': [
        {
            'id': site_id,
            'type_symbol': type_symbol,
            'wyckoff_letter': wyckoff,
            'fract': fract,
            'occupancy': occupancy,
            'adp_iso': adp_iso,
        }
        for site_id, type_symbol, wyckoff, fract, occupancy, adp_iso in FULLPROF_ATOM_SITES
    ],
})

# %% [markdown]
# ## Define the experiment
#
# The neutron experiment, with its scattering-length source (Sears 1992,
# `sears1992` — FullProf's own La and B lengths, crysta), as
# project-file text. The absorption category is engaged through its typed
# selector after the build: on a CW experiment `cylinder-hewat` selects the Hewat
# cylinder form and carries the single refinable `mu_r` parameter
# (μR = μ·R, R the cylinder **radius**).

# %%
excluded_rows = '\n'.join(
    f'{index} {start} {end}'
    for index, (start, end) in enumerate(FULLPROF_EXCLUDED_REGIONS, start=1)
)
EXPERIMENT_EDI = f"""data_lab6
_edi.schema_version 3
_experiment_type.beam_mode "constant wavelength"
_scattering_source.neutron_scattering_length sears1992
_peak.type cwl-pseudo-voigt
_peak.cutoff_fwhm {FULLPROF_WDT}
_peak.broad_gauss_u {FULLPROF_U}
_peak.broad_gauss_v {FULLPROF_V}
_peak.broad_gauss_w {FULLPROF_W}
_peak.broad_lorentz_x {FULLPROF_X}
_peak.broad_lorentz_y {FULLPROF_Y}
_instrument.setup_wavelength {FULLPROF_WAVELENGTH}
_instrument.calib_twotheta_offset {FULLPROF_ZERO}
loop_
_excluded_region.id
_excluded_region.start
_excluded_region.end
{excluded_rows}
loop_
_linked_structure.structure_id
_linked_structure.scale
lab6 {FULLPROF_SCALE}
"""

# %% [markdown]
# ## Build the project

# %%
project = Project()
project.structure = structure
project.experiment = ExperimentFactory.from_cif_str(EXPERIMENT_EDI)
verify.set_reference_as_measured(project.experiment, x, calc_fullprof)
project.experiment.absorption.type = 'cylinder-hewat'
project.experiment.absorption.mu_r = Parameter(FULLPROF_MU_R)

# %% [markdown]
# ## Calculate the pattern

# %%
project.analysis.calculate()

# %% [markdown]
# ## edi-crysta VS FullProf

# %%
calc_ed_crysta = verify.restrict_to_included(
    project.experiment,
    project.experiment.data.intensity_calc,
)
LABEL_ED_CRYSTA = verify.engine_label('crysta')

verify.plot_pattern_comparison(
    project.experiment,
    reference=calc_fullprof,
    candidate=calc_ed_crysta,
    reference_label=FULLPROF_LABEL,
    candidate_label=LABEL_ED_CRYSTA,
)

# %% [markdown]
# ## Per-reflection VS pointwise application
#
# The same Hewat factor applied the way diffraction-lib applies it —
# pointwise over the 2θ grid, `A(θ)` at each grid point's θ = 2θ/2 —
# on top of the unabsorbed edi pattern. Both conventions are then held
# against the same FullProf reference below.

# %%
project_none = Project()
project_none.structure = structure
project_none.experiment = ExperimentFactory.from_cif_str(EXPERIMENT_EDI)
verify.set_reference_as_measured(project_none.experiment, x, calc_fullprof)
project_none.analysis.calculate()
calc_unabsorbed = np.asarray(project_none.experiment.data.intensity_calc, dtype=float)

sin2_theta = np.sin(np.radians(np.asarray(x, dtype=float)) / 2.0) ** 2
hewat_grid_factor = np.exp(
    -(1.7133 - 0.0368 * sin2_theta) * FULLPROF_MU_R
    + (0.0927 + 0.375 * sin2_theta) * FULLPROF_MU_R**2
)
calc_pointwise = verify.restrict_to_included(
    project_none.experiment,
    calc_unabsorbed * hewat_grid_factor,
)
LABEL_POINTWISE = 'pointwise Hewat (diffraction-lib convention)'

verify.plot_pattern_comparison(
    project.experiment,
    reference=calc_fullprof,
    candidate=calc_pointwise,
    reference_label=FULLPROF_LABEL,
    candidate_label=LABEL_POINTWISE,
)

# %% [markdown]
# ## Agreement check
#
# Three gated comparisons, each with its own labelled pins:
#
# 1. **The shipped per-reflection application vs FullProf** — the page's
#    verification claim, pinned at the LaB6 family bounds.
# 2. **The pointwise application vs FullProf** — the convention
#    comparison; its integrated-intensity ratio (measured 0.99873) sits
#    outside the family's 0.999 floor, so it carries its own wider
#    ratio pin rather than silently loosening the shipped one.
# 3. **Pointwise vs per-reflection** — pins the measured size of the
#    convention gap at μR = 0.7 (profile difference 0.079 %), so growth
#    of the divergence is a visible failure, not a drifting footnote.

# %%
verify.assert_patterns_agree(
    [
        (
            f'{LABEL_ED_CRYSTA} vs {FULLPROF_LABEL}',
            verify.restrict_to_included(project.experiment, calc_fullprof),
            calc_ed_crysta,
        ),
    ],
    tolerances=verify.AgreementTolerances(
        max_profile_difference_percent=0.20,
        max_deviation_percent=0.65,
        min_intensity_ratio=0.999,
        max_intensity_ratio=1.001,
        min_correlation=0.99999,
    ),
)

# %%
verify.assert_patterns_agree(
    [
        (
            f'{LABEL_POINTWISE} vs {FULLPROF_LABEL}',
            verify.restrict_to_included(project.experiment, calc_fullprof),
            calc_pointwise,
        ),
    ],
    tolerances=verify.AgreementTolerances(
        max_profile_difference_percent=0.22,
        max_deviation_percent=0.65,
        min_intensity_ratio=0.998,
        max_intensity_ratio=1.001,
        min_correlation=0.99999,
    ),
)

# %%
verify.assert_patterns_agree(
    [
        (
            f'{LABEL_ED_CRYSTA} vs {LABEL_POINTWISE}',
            calc_pointwise,
            calc_ed_crysta,
        ),
    ],
    tolerances=verify.AgreementTolerances(
        max_profile_difference_percent=0.10,
        max_deviation_percent=0.12,
        min_intensity_ratio=0.9995,
        max_intensity_ratio=1.0015,
        min_correlation=0.9999995,
    ),
)
