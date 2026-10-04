# %% [markdown]
# # LaB6 — powder neutron CW — basic
#
# Natural boron, and no SyCos/SySin, FCJ asymmetry or absorption.
#
# **Scattering table.** The experiment declares Sears (1992) —
# `_scattering_source.neutron_scattering_length sears1992`, the
# publication FullProf's own neutron lengths come from: its real parts equal
# FullProf's La and B values to the digits FullProf carries.
#
# **Known and carried by design.** The profile-level deviation is roughly twice
# LBCO's: sharp peaks with a Lorentzian component (Y = 0.0545) under the tightest
# CW peak base (Wdt = 12), so the cutoff truncates more Lorentzian tail
# intensity — a stated modelling convention, not a tuning target.
#
# **The bounds are labelled regression pins** — this page's own measured
# closeness with stated headroom.

# %%
from edi import ExperimentFactory
from edi import Project
from edi import StructureFactory
from edi import verification as verify

# %% [markdown]
# ## Load the FullProf reference

# %%
FULLPROF_PROJECT_DIR = 'pd-neut-cwl_lab6-echidna_basic'
FULLPROF_PRF_FILE = 'ECH0030684_LaB6_1p622A_baseline.prf'
FULLPROF_SUM_FILE = 'ECH0030684_LaB6_1p622A_baseline.sum'
FULLPROF_BAC_FILE = 'ECH0030684_LaB6_1p622A_baseline.bac'
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
# The neutron experiment, with its scattering-length source, as project-file text.

# %%
excluded_rows = '\n'.join(
    f'{index} {start} {end}'
    for index, (start, end) in enumerate(FULLPROF_EXCLUDED_REGIONS, start=1)
)
experiment = ExperimentFactory.from_cif_str(f"""data_lab6
_edi.schema_version 3
_experiment_type.beam_mode "constant wavelength"
_scattering_source.neutron_scattering_length sears1992
_peak.type cwl-pseudo-voigt
_peak.broad_gauss_u {FULLPROF_U}
_peak.broad_gauss_v {FULLPROF_V}
_peak.broad_gauss_w {FULLPROF_W}
_peak.broad_lorentz_x {FULLPROF_X}
_peak.broad_lorentz_y {FULLPROF_Y}
_peak.cutoff_fwhm {FULLPROF_WDT}
_instrument.calib_twotheta_offset {FULLPROF_ZERO}
_instrument.setup_wavelength {FULLPROF_WAVELENGTH}
loop_
_excluded_region.id
_excluded_region.start
_excluded_region.end
{excluded_rows}
loop_
_linked_structure.structure_id
_linked_structure.scale
lab6 {FULLPROF_SCALE}
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
        max_profile_difference_percent=0.20,
        max_deviation_percent=0.65,
        min_intensity_ratio=0.999,
        max_intensity_ratio=1.001,
        min_correlation=0.99999,
    ),
)
