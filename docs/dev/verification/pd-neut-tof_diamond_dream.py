# %% [markdown]
# # Diamond — powder neutron TOF — DREAM (ESS, McStas)
#
# Verifies the Jorgensen back-to-back exponential TOF profile against a
# FullProf reference fitted to McStas-simulated reduced data from the
# DREAM diffractometer at ESS.
#
# **Occupancy convention.** The `.pcr` places C at (1/8, 1/8, 1/8) in
# `F d -3 m:1` — Wyckoff 16c in origin choice 1 — with FullProf's fractional
# `Occ = site_mult / general_mult` (16 / 192), so its scale is directly
# crysta's: the seeded scale below is the `.pcr` scale.

# %%
from edi import ExperimentFactory
from edi import Project
from edi import StructureFactory
from edi import verification as verify

# %% [markdown]
# ## Load the FullProf reference

# %%
FULLPROF_PROJECT_DIR = 'pd-neut-tof_diamond-dream_basic'
FULLPROF_PRF_FILE = 'diamond.prf'
FULLPROF_SUM_FILE = 'diamond.sum'
FULLPROF_BAC_FILE = 'diamond.bac'
FULLPROF_LABEL = verify.fullprof_label(FULLPROF_PROJECT_DIR, FULLPROF_SUM_FILE)

# Structure
FULLPROF_SPACE_GROUP = 'F d -3 m'  # FullProf Space group symbol
FULLPROF_CELL_LENGTH_A = 3.567  # FullProf a
FULLPROF_C_ATOM = 'C'  # FullProf Atom
FULLPROF_C_TYPE = 'C'  # FullProf Typ
FULLPROF_C_FRACT = (0.125, 0.125, 0.125)  # FullProf X, Y, Z
FULLPROF_C_ADP_ISO = 0.89263  # FullProf Biso

# Experiment
FULLPROF_ZERO = 0.0  # FullProf Zero
FULLPROF_SCALE = 14.57259  # FullProf Scale
FULLPROF_TWOTHETA_BANK = 90.0  # FullProf 2ThetaBank
FULLPROF_DTT1 = 28385.86133  # FullProf Dtt1
FULLPROF_DTT2 = 0.0  # FullProf Dtt2
FULLPROF_SIGMA_0 = 46937.7188  # FullProf Sigma-0
FULLPROF_SIGMA_1 = 4887.9180  # FullProf Sigma-1
FULLPROF_SIGMA_2 = 0.0  # FullProf Sigma-2
FULLPROF_ALPHA_0 = 0.0  # FullProf alph0
FULLPROF_ALPHA_1 = 0.022544  # FullProf alph1
FULLPROF_BETA_0 = 0.014330  # FullProf beta0
FULLPROF_BETA_1 = 0.0  # FullProf beta1
FULLPROF_WDT = 30.0  # FullProf Wdt
FULLPROF_EXCLUDED_REGIONS = [(0, 10000), (70000, 200000)]  # FullProf Excluded regions

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
    'name': 'diamond',
    'space_group': {'name_h_m': FULLPROF_SPACE_GROUP, 'coord_system_code': '1'},
    'cell': {'length_a': FULLPROF_CELL_LENGTH_A},
    'atom_sites': [
        {
            'id': FULLPROF_C_ATOM,
            'type_symbol': FULLPROF_C_TYPE,
            'wyckoff_letter': 'c',
            'fract': FULLPROF_C_FRACT,
            'adp_iso': FULLPROF_C_ADP_ISO,
        },
    ],
})

# %% [markdown]
# ## Define the experiment

# %%
experiment = ExperimentFactory.from_dict({
    'name': 'diamond',
    'peak': {
        'type': 'tof-jorgensen',
        'cutoff_fwhm': FULLPROF_WDT,
        'broad_gauss_sigma_0': FULLPROF_SIGMA_0,
        'broad_gauss_sigma_1': FULLPROF_SIGMA_1,
        'broad_gauss_sigma_2': FULLPROF_SIGMA_2,
        'rise_alpha_0': FULLPROF_ALPHA_0,
        'rise_alpha_1': FULLPROF_ALPHA_1,
        'decay_beta_0': FULLPROF_BETA_0,
        'decay_beta_1': FULLPROF_BETA_1,
    },
    'instrument': {
        'calib_d_to_tof_offset': FULLPROF_ZERO,
        'calib_d_to_tof_linear': FULLPROF_DTT1,
        'calib_d_to_tof_quadratic': FULLPROF_DTT2,
        'setup_twotheta_bank': FULLPROF_TWOTHETA_BANK,
    },
    'linked_structure': {'scale': FULLPROF_SCALE},
    'excluded_regions': FULLPROF_EXCLUDED_REGIONS,
})

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
        max_profile_difference_percent=0.13,
        max_deviation_percent=0.087,
        min_intensity_ratio=0.99937,
        max_intensity_ratio=1.00063,
        min_correlation=0.99999967,
    ),
)
