# %% [markdown]
# # Fe — powder neutron TOF — pseudo-Voigt profile
#
# Verifies the simple **non-convoluted** time-of-flight pseudo-Voigt (`tof-pseudo-voigt`,
# FullProf `Npr` = 7): the TCH pseudo-Voigt at the Bragg time of flight, with the
# Jorgensen-Von Dreele Gaussian (`sigma_0..2`) and Lorentzian (`gamma_0..2`) widths, and no
# back-to-back exponentials. The data are ferrite (BEER, ESS) on a 90° bank.
#
# **Every parameter at FullProf's value, the scale included.** Upstream's page fits the scale
# only. Here nothing is fitted: this is a fixed-parameter forward comparison, like the other
# FullProf pages.
#
# **Occupancy convention.** The `.pcr` `Occ` is `site_mult / general_mult` (Fe 2a in `I m -3 m`:
# 2 / 96 = 0.02083), so chemical occupancy 1.0 carries FullProf's scale unchanged.
#
# **Scattering table.** Sears (1992), declared as `sears1992`: its Fe length is
# FullProf's own.
#
# **The bounds are labelled regression pins** — this page's own measured closeness with stated
# headroom (profile difference 0.03 %, max deviation 0.03 %, area ratio 1.00012, correlation
# 0.999999992).

# %%
from edi import ExperimentFactory
from edi import Project
from edi import StructureFactory
from edi import verification as verify

# %% [markdown]
# ## Load the FullProf reference

# %%
FULLPROF_PROJECT_DIR = 'pd-neut-tof_fe_pseudo-voigt'
FULLPROF_PRF_FILE = 'fe_1.prf'
FULLPROF_SUM_FILE = 'fe.sum'
FULLPROF_BAC_FILE = 'fe_1.bac'
FULLPROF_LABEL = verify.fullprof_label(FULLPROF_PROJECT_DIR, FULLPROF_SUM_FILE)

# Structure
FULLPROF_SPACE_GROUP = 'I m -3 m'  # FullProf Space group symbol
FULLPROF_CELL_LENGTH_A = 2.886  # FullProf a
FULLPROF_FE_FRACT = (0.0, 0.0, 0.0)  # FullProf X, Y, Z
FULLPROF_FE_ADP_ISO = 1.71513  # FullProf Biso
# Experiment
FULLPROF_ZERO = -10.29183  # FullProf Zero
FULLPROF_SCALE = 401.4629  # FullProf Scale
FULLPROF_TWOTHETA_BANK = 90.0  # FullProf 2ThetaBank
FULLPROF_DTT1 = 54902.18750  # FullProf Dtt1
FULLPROF_DTT2 = 0.0  # FullProf Dtt2
FULLPROF_SIGMA_0 = 893.6397  # FullProf Sigma-0
FULLPROF_SIGMA_1 = 1283.6387  # FullProf Sigma-1
FULLPROF_SIGMA_2 = 311.7041  # FullProf Sigma-2
FULLPROF_GAMMA_0 = 5.0330  # FullProf Gamma-0
FULLPROF_GAMMA_1 = 0.0  # FullProf Gamma-1
FULLPROF_GAMMA_2 = 0.0  # FullProf Gamma-2
FULLPROF_WDT = 12.0  # FullProf Wdt
FULLPROF_EXCLUDED_REGIONS = [(20000.0, 40000.0), (130000.0, 180000.0)]  # FullProf Excluded

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
    'name': 'fe',
    'space_group': {'name_h_m': FULLPROF_SPACE_GROUP},
    'cell': {'length_a': FULLPROF_CELL_LENGTH_A},
    'atom_sites': [
        {
            'id': 'Fe',
            'type_symbol': 'Fe',
            'wyckoff_letter': 'a',
            'fract': FULLPROF_FE_FRACT,
            'adp_iso': FULLPROF_FE_ADP_ISO,
        },
    ],
})

# %% [markdown]
# ## Define the experiment
#
# The neutron experiment, with its scattering-length source, as project-file text.

# %%
excluded_rows = '\n'.join(
    f'{index} {start} {end}'
    for index, (start, end) in enumerate(FULLPROF_EXCLUDED_REGIONS, start=1)
)
experiment = ExperimentFactory.from_cif_str(f"""data_fe
_edi.schema_version 3
_scattering_source.neutron_scattering_length sears1992
_peak.type tof-pseudo-voigt
_peak.cutoff_fwhm {FULLPROF_WDT}
_peak.broad_gauss_sigma_0 {FULLPROF_SIGMA_0}
_peak.broad_gauss_sigma_1 {FULLPROF_SIGMA_1}
_peak.broad_gauss_sigma_2 {FULLPROF_SIGMA_2}
_peak.broad_lorentz_gamma_0 {FULLPROF_GAMMA_0}
_peak.broad_lorentz_gamma_1 {FULLPROF_GAMMA_1}
_peak.broad_lorentz_gamma_2 {FULLPROF_GAMMA_2}
_instrument.calib_d_to_tof_offset {FULLPROF_ZERO}
_instrument.calib_d_to_tof_linear {FULLPROF_DTT1}
_instrument.calib_d_to_tof_quadratic {FULLPROF_DTT2}
_instrument.setup_twotheta_bank {FULLPROF_TWOTHETA_BANK}
loop_
_excluded_region.id
_excluded_region.start
_excluded_region.end
{excluded_rows}
loop_
_linked_structure.structure_id
_linked_structure.scale
fe {FULLPROF_SCALE}
""")

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
        max_profile_difference_percent=0.05,
        max_deviation_percent=0.05,
        min_intensity_ratio=0.9998,
        max_intensity_ratio=1.0004,
        min_correlation=0.9999999,
    ),
)
