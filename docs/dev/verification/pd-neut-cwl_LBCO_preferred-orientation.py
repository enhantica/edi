# %% [markdown]
# # LBCO — powder neutron CW — preferred orientation
#
# The LBCO baseline with March-Dollase preferred orientation switched on:
# a `_preferred_orientation` row with r = 1.2 (FullProf `Pref1`), random
# fraction 0.3 (`Pref2`) and texture axis [0 0 1] (`Pr1 Pr2 Pr3`).
#
# **Fitting:** none — every parameter is taken from the FullProf
# reference, the scale included; only the calculated patterns are compared.
#
# **The model is FullProf's `Nor = 1`:**
# P = f + (1 - f)·⟨[r² cos²(alpha) + sin²(alpha) / r]^(-3/2)⟩, averaged over the
# symmetry-equivalent directions of each reflection, alpha measured in the
# reciprocal metric, no volume normalisation.
#
# **Application convention.** The factor multiplies each reflection's
# intensity, on the same per-reflection chain as absorption. It depends on
# the reflection's direction, not on 2θ, so there is no pointwise
# alternative to compare — diffraction-lib applies it per reflection too.
# **Where the method diverges from diffraction-lib's**: its only engine,
# cryspy, uses the reciprocal coefficient (g₁ = 1/r) and a differently
# normalised factor, so the upstream page must **fit the scale** before it
# agrees with FullProf. crysta evaluates FullProf's form directly, so this
# page compares at FullProf's own scale, with nothing fitted.
#
# **Scattering table.** Sears (1992), the publication FullProf's neutron
# lengths come from, as on the basic LBCO page.
#
# **The bounds are labelled regression pins** — this page's own measured
# closeness with stated headroom, never a page-port digit.

# %%
from edi import ExperimentFactory
from edi import Project
from edi import StructureFactory
from edi import verification as verify

# %% [markdown]
# ## Load the FullProf reference

# %%
FULLPROF_PROJECT_DIR = 'pd-neut-cwl_lbco-hrpt_preferred-orientation'
FULLPROF_PRF_FILE = 'lbco.prf'
FULLPROF_SUM_FILE = 'lbco.sum'
FULLPROF_BAC_FILE = 'lbco.bac'
FULLPROF_LABEL = verify.fullprof_label(FULLPROF_PROJECT_DIR, FULLPROF_SUM_FILE)

# Structure
FULLPROF_SPACE_GROUP = 'P m -3 m'  # FullProf Space group symbol
FULLPROF_CELL_LENGTH_A = 3.890790  # FullProf a
FULLPROF_ATOM_SITES = [
    # FullProf Atom, Typ, Wyckoff, (X, Y, Z), Occ (chemical), Biso
    ('La', 'La', 'a', (0.0, 0.0, 0.0), 0.5, 0.57511),
    ('Ba', 'Ba', 'a', (0.0, 0.0, 0.0), 0.5, 0.57511),
    ('Co', 'Co', 'b', (0.5, 0.5, 0.5), 1.0, 0.26023),
    ('O', 'O', 'c', (0.0, 0.5, 0.5), 0.97856, 1.36662),
]
# Experiment
FULLPROF_ZERO = 0.62040  # FullProf Zero
FULLPROF_SCALE = 9.405870  # FullProf Scale
FULLPROF_WAVELENGTH = 1.494000  # FullProf Lambda
FULLPROF_U = 0.081547  # FullProf U
FULLPROF_V = -0.115345  # FullProf V
FULLPROF_W = 0.121125  # FullProf W
FULLPROF_X = 0.0  # FullProf X
FULLPROF_Y = 0.083038  # FullProf Y
FULLPROF_WDT = 30.0  # FullProf Wdt
FULLPROF_EXCLUDED_REGIONS = [(0.0, 5.0), (165.0, 180.0)]  # FullProf Excluded regions
# Preferred orientation
FULLPROF_PREF_1 = 1.2  # FullProf Pref1
FULLPROF_PREF_2 = 0.3  # FullProf Pref2
FULLPROF_PR_1 = 0  # FullProf Pr1
FULLPROF_PR_2 = 0  # FullProf Pr2
FULLPROF_PR_3 = 1  # FullProf Pr3

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
    'name': 'lbco',
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
# The neutron experiment as project-file text; the preferred orientation
# is added through the experiment's `preferred_orientation` collection.

# %%
excluded_rows = '\n'.join(
    f'{index} {start} {end}'
    for index, (start, end) in enumerate(FULLPROF_EXCLUDED_REGIONS, start=1)
)
EXPERIMENT_EDI = f"""data_lbco
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
lbco {FULLPROF_SCALE}
"""
experiment = ExperimentFactory.from_cif_str(EXPERIMENT_EDI)
experiment.preferred_orientation.create(
    structure_id='lbco',
    march_r=FULLPROF_PREF_1,
    march_random_fract=FULLPROF_PREF_2,
    index_h=FULLPROF_PR_1,
    index_k=FULLPROF_PR_2,
    index_l=FULLPROF_PR_3,
)

# %% [markdown]
# ## Build the project

# %%
project = Project()
project.structure = structure
project.experiment = experiment
verify.set_reference_as_measured(project.experiment, x, calc_fullprof)

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
# ## Without the correction
#
# The same project with no `_preferred_orientation` row. It is what the
# pattern would be if the correction did not reach the intensities, so the
# check below also shows that this reference can tell the difference.

# %%
project_random = Project()
project_random.structure = structure
project_random.experiment = ExperimentFactory.from_cif_str(EXPERIMENT_EDI)
verify.set_reference_as_measured(project_random.experiment, x, calc_fullprof)
project_random.analysis.calculate()
calc_random = verify.restrict_to_included(
    project_random.experiment,
    project_random.experiment.data.intensity_calc,
)
LABEL_RANDOM = verify.engine_label('crysta', note='no preferred orientation')

verify.plot_pattern_comparison(
    project.experiment,
    reference=calc_fullprof,
    candidate=calc_random,
    reference_label=FULLPROF_LABEL,
    candidate_label=LABEL_RANDOM,
)

# %% [markdown]
# ## Agreement check
#
# The shipped correction against FullProf at the LBCO family's pins (the
# basic page's bounds; measured here 0.085 % profile difference, 0.37 %
# worst point, area ratio 0.99935, correlation 0.9999996) and — the escape
# the correction must not pass — the uncorrected pattern, measured 3.0 %
# from the reference, whose profile difference must stay above 1 %, ten
# times the shipped bound.

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
        max_profile_difference_percent=0.11,
        max_deviation_percent=0.45,
        min_intensity_ratio=0.999,
        max_intensity_ratio=1.001,
        min_correlation=0.99999,
    ),
)

# %%
random_closeness = verify.pattern_closeness(
    verify.restrict_to_included(project.experiment, calc_fullprof),
    calc_random,
)
if not random_closeness.profile_difference_percent > 1.0:
    msg = (
        'the uncorrected pattern agrees with the textured FullProf reference '
        f'({random_closeness.profile_difference_percent:.3f} % profile difference): '
        'the reference no longer tells the correction apart'
    )
    raise AssertionError(msg)
