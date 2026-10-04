# %% [markdown]
# # Na₂Ca₃Al₂F₁₄ — powder neutron TOF — Jorgensen-Von Dreele (Gaussian)
#
# The Lorentzian terms (γ₀, γ₁, γ₂) are zero in the reference, so the
# Jorgensen-Von Dreele pseudo-Voigt reduces to the Gaussian case.
#
# **Occupancy convention.** The `.pcr` states occupancy in FullProf's fractional
# notation, `site_mult / general_mult` (in `I 2₁ 3`: Ca1 12b = 0.5, Al1/Na1/F3
# 8a = 0.33333, F1/F2 24c = 1.0), which is what crysta expects. Intensity goes as
# occupancy squared, so the scale absorbs `(general_mult / 8) ** 2 = 9` relative
# to the older `site_mult / 8` notation: 4.019304 * 9 = 36.17374, the seeded
# scale below.

# %%
from edi import ExperimentFactory
from edi import Project
from edi import StructureFactory
from edi import verification as verify

# %% [markdown]
# ## Load the FullProf reference

# %%
FULLPROF_PROJECT_DIR = 'pd-neut-tof_ncaf-wish_jorgensen-von-dreele'
FULLPROF_PRF_FILE = 'tmpl_one_bank.prf'
FULLPROF_SUM_FILE = 'tmpl_one_bank.sum'
FULLPROF_BAC_FILE = 'tmpl_one_bank.bac'
FULLPROF_LABEL = verify.fullprof_label(FULLPROF_PROJECT_DIR, FULLPROF_SUM_FILE)

# Structure
FULLPROF_SPACE_GROUP = 'I 21 3'  # FullProf Space group symbol
FULLPROF_CELL_LENGTH_A = 10.250256  # FullProf a
FULLPROF_ATOM_SITES = [
    # FullProf Atom, Typ, Wyckoff, (X, Y, Z), Biso
    ('Ca', 'Ca', 'b', (0.46610, 0.0, 0.25), 0.88721),
    ('Al', 'Al', 'a', (0.25163, 0.25163, 0.25163), 0.65230),
    ('Na', 'Na', 'a', (0.08472, 0.08472, 0.08472), 1.89168),
    ('F1', 'F', 'c', (0.13748, 0.30533, 0.11947), 0.89535),
    ('F2', 'F', 'c', (0.36263, 0.36333, 0.18669), 1.27175),
    ('F3', 'F', 'a', (0.46120, 0.46120, 0.46120), 0.78029),
]

# Experiment
FULLPROF_ZERO = -13.88128  # FullProf Zero
FULLPROF_SCALE = 36.17374  # FullProf Scale
FULLPROF_TWOTHETA_BANK = 152.827  # FullProf 2ThetaBank
FULLPROF_DTT1 = 20773.12305  # FullProf Dtt1
FULLPROF_DTT2 = -1.08308  # FullProf Dtt2
FULLPROF_SIGMA_0 = 0.0  # FullProf Sigma-0
FULLPROF_SIGMA_1 = 0.0  # FullProf Sigma-1
FULLPROF_SIGMA_2 = 15.6959  # FullProf Sigma-2
FULLPROF_GAMMA_0 = 0.0  # FullProf Gamma-0
FULLPROF_GAMMA_1 = 0.0  # FullProf Gamma-1
FULLPROF_GAMMA_2 = 0.0  # FullProf Gamma-2
FULLPROF_ALPHA_0 = -0.009276  # FullProf alph0
FULLPROF_ALPHA_1 = 0.109622  # FullProf alph1
FULLPROF_BETA_0 = 0.006705  # FullProf beta0
FULLPROF_BETA_1 = 0.009708  # FullProf beta1
FULLPROF_WDT = 40.0  # FullProf Wdt
FULLPROF_EXCLUDED_REGIONS = [(0, 30000), (50000, 200000)]  # FullProf Excluded regions

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
    'name': 'ncaf',
    'space_group': {'name_h_m': FULLPROF_SPACE_GROUP},
    'cell': {'length_a': FULLPROF_CELL_LENGTH_A},
    'atom_sites': [
        {
            'id': site_id,
            'type_symbol': type_symbol,
            'wyckoff_letter': wyckoff,
            'fract': fract,
            'adp_iso': adp_iso,
        }
        for site_id, type_symbol, wyckoff, fract, adp_iso in FULLPROF_ATOM_SITES
    ],
})

# %% [markdown]
# ## Define the experiment

# %%
experiment = ExperimentFactory.from_dict({
    'name': 'ncaf',
    'peak': {
        'type': 'tof-jorgensen-von-dreele',
        'cutoff_fwhm': FULLPROF_WDT,
        'broad_gauss_sigma_0': FULLPROF_SIGMA_0,
        'broad_gauss_sigma_1': FULLPROF_SIGMA_1,
        'broad_gauss_sigma_2': FULLPROF_SIGMA_2,
        'broad_lorentz_gamma_0': FULLPROF_GAMMA_0,
        'broad_lorentz_gamma_1': FULLPROF_GAMMA_1,
        'broad_lorentz_gamma_2': FULLPROF_GAMMA_2,
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
        max_profile_difference_percent=0.0093,
        max_deviation_percent=0.015,
        min_intensity_ratio=0.999958,
        max_intensity_ratio=1.000042,
        min_correlation=0.999999998,
    ),
)
