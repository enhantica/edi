# %% [markdown]
# # Si — powder neutron TOF — Jorgensen-Von Dreele profile
#
# **Occupancy convention.** The `.pcr` states occupancy in FullProf's fractional
# notation, `site_mult / general_mult` (Si 8a in `F d -3 m`: 8 / 192 = 0.04167),
# which is what crysta expects. Intensity goes as occupancy squared, so the scale
# absorbs `(general_mult / 8) ** 2 = 576` relative to the older `site_mult / 8`
# notation: 0.6750847 * 576 = 388.8488, the seeded scale below.

# %%
from edi import ExperimentFactory
from edi import Project
from edi import StructureFactory
from edi import verification as verify

# %% [markdown]
# ## Load the FullProf reference

# %%
FULLPROF_PROJECT_DIR = 'pd-neut-tof_si-sepd_jorgensen-von-dreele'
FULLPROF_PRF_FILE = 'arg_si.prf'
FULLPROF_SUM_FILE = 'arg_si.sum'
FULLPROF_BAC_FILE = 'arg_si.bac'
FULLPROF_LABEL = verify.fullprof_label(FULLPROF_PROJECT_DIR, FULLPROF_SUM_FILE)

# Structure
FULLPROF_SPACE_GROUP = 'F d -3 m'  # FullProf Space group symbol
FULLPROF_CELL_LENGTH_A = 5.431342  # FullProf a
FULLPROF_SI_ATOM = 'Si'  # FullProf Atom
FULLPROF_SI_TYPE = 'Si'  # FullProf Typ
FULLPROF_SI_FRACT = (0.125, 0.125, 0.125)  # FullProf X, Y, Z
FULLPROF_SI_ADP_ISO = 0.52448  # FullProf Biso

# Experiment
FULLPROF_ZERO = -9.18766  # FullProf Zero
FULLPROF_SCALE = 388.8488  # FullProf Scale
FULLPROF_TWOTHETA_BANK = 144.845  # FullProf 2ThetaBank
FULLPROF_DTT1 = 7476.91016  # FullProf Dtt1
FULLPROF_DTT2 = -1.54  # FullProf Dtt2
FULLPROF_SIGMA_0 = 3.5544  # FullProf Sigma-0
FULLPROF_SIGMA_1 = 33.0419  # FullProf Sigma-1
FULLPROF_SIGMA_2 = 0.0  # FullProf Sigma-2
FULLPROF_GAMMA_0 = 0.0  # FullProf Gamma-0
FULLPROF_GAMMA_1 = 2.5430  # FullProf Gamma-1
FULLPROF_GAMMA_2 = 0.0  # FullProf Gamma-2
FULLPROF_ALPHA_0 = 0.0  # FullProf alph0
FULLPROF_ALPHA_1 = 0.597100  # FullProf alph1
FULLPROF_BETA_0 = 0.042210  # FullProf beta0
FULLPROF_BETA_1 = 0.009460  # FullProf beta1
FULLPROF_WDT = 8.2  # FullProf Wdt
FULLPROF_EXCLUDED_REGIONS = [(0, 5000), (10000, 100000)]  # FullProf Excluded regions

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
    'name': 'si',
    'space_group': {'name_h_m': FULLPROF_SPACE_GROUP, 'coord_system_code': '2'},
    'cell': {'length_a': FULLPROF_CELL_LENGTH_A},
    'atom_sites': [
        {
            'id': FULLPROF_SI_ATOM,
            'type_symbol': FULLPROF_SI_TYPE,
            'wyckoff_letter': 'a',
            'fract': FULLPROF_SI_FRACT,
            'adp_iso': FULLPROF_SI_ADP_ISO,
        },
    ],
})

# %% [markdown]
# ## Define the experiment

# %%
experiment = ExperimentFactory.from_dict({
    'name': 'si',
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
        max_profile_difference_percent=0.36,
        max_deviation_percent=0.2,
        min_intensity_ratio=0.9943,
        max_intensity_ratio=1.0057,
        min_correlation=0.9999976,
    ),
)
