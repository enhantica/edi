# %% [markdown]
# # PbSO4 — powder neutron CW — basic pseudo-Voigt
#
# Orthorhombic `Pnma` — the first non-cubic CW page, so the first to exercise the
# general cell metric (all three independent cell edges) on a real reference. A
# cell block carrying `a` alone would leave `b = c = 1.0 A` and collapse the
# pattern (measured: max deviation 99.97 %).
#
# **Scattering table.** The experiment declares Sears (1992) —
# `_scattering_source.neutron_scattering_length sears1992`, the
# publication FullProf's own neutron lengths come from (Pb, S and O equal
# FullProf's values). Here they agree to four significant figures with crysta's
# default table, so the declared source is source fidelity, not a correctness
# requirement.
#
# **Occupancies are chemical site fractions.** The `.pcr` `Occ` column is
# `site_mult / general_mult` (general multiplicity 8 for `Pnma`), so the four 4c
# sites' `0.50000` and the 8d site's `1.00000` all convert to chemical 1.0.
#
# **Exclusion windows are recorded but deliberately not applied.** The source
# `.pcr` windows (0-10 deg, 155.45-180 deg) meet the committed grid's endpoints,
# and edi's exclusion mask is inclusive at both bounds, so applying them would
# remove the first row (10.000 deg) *and* the artifact row (155.450 deg),
# reducing the comparison from 2910 points to 2908. The comparison is full-grid.
#
# **Known and carried by design.** The final `.prf` row (2theta = 155.450 deg) is
# background-only — its net reference intensity is slightly negative (-0.26)
# against edi's 95.66 — and that one artifact point dominates both point-sensitive
# metrics: it *is* the 4.35 % max deviation, and it contributes 97 % of the
# profile-difference mean-square (0.605 % with the row, 0.103 % without). Exactly
# 1 of 2910 points exceeds 0.5 %; the second-worst deviation is 0.037 %. Both
# point pins sit above the artifact, and the agreement claim rests on the
# area-ratio and correlation pins, which one background-only point cannot
# dominate.

# %%
from edi import ExperimentFactory
from edi import Project
from edi import StructureFactory
from edi import verification as verify

# %% [markdown]
# ## Load the FullProf reference

# %%
FULLPROF_PROJECT_DIR = 'pd-neut-cwl_pbso4_basic'
FULLPROF_PRF_FILE = 'pbso4.prf'
FULLPROF_SUM_FILE = 'pbso4.sum'
FULLPROF_BAC_FILE = 'pbso4.bac'
FULLPROF_LABEL = verify.fullprof_label(FULLPROF_PROJECT_DIR, FULLPROF_SUM_FILE)

# Structure
FULLPROF_SPACE_GROUP = 'P n m a'  # FullProf Space group symbol
FULLPROF_CELL_LENGTH_A = 8.477992  # FullProf a
FULLPROF_CELL_LENGTH_B = 5.396482  # FullProf b
FULLPROF_CELL_LENGTH_C = 6.957715  # FullProf c
FULLPROF_ATOM_SITES = [
    # FullProf Atom, Typ, Wyckoff, (X, Y, Z), Occ (chemical), Biso
    ('Pb', 'Pb', 'c', (0.18754, 0.25000, 0.16709), 1.0, 1.38058),
    ('S', 'S', 'c', (0.06532, 0.25000, 0.68401), 1.0, 0.36192),
    ('O1', 'O', 'c', (0.90822, 0.25000, 0.59542), 1.0, 2.03661),
    ('O2', 'O', 'c', (0.19390, 0.25000, 0.54359), 1.0, 1.50417),
    ('O3', 'O', 'd', (0.08114, 0.02713, 0.80863), 1.0, 1.34347),
]
# Experiment
FULLPROF_ZERO = -0.14357  # FullProf Zero
FULLPROF_SCALE = 1.467900  # FullProf Scale
FULLPROF_WAVELENGTH = 1.912000  # FullProf Lambda
FULLPROF_U = 0.139488  # FullProf U
FULLPROF_V = -0.414074  # FullProf V
FULLPROF_W = 0.388200  # FullProf W
FULLPROF_X = 0.0  # FullProf X
FULLPROF_Y = 0.086383  # FullProf Y
FULLPROF_WDT = 30.0  # FullProf Wdt

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
    'name': 'pbso4',
    'space_group': {'name_h_m': FULLPROF_SPACE_GROUP},
    'cell': {
        'length_a': FULLPROF_CELL_LENGTH_A,
        'length_b': FULLPROF_CELL_LENGTH_B,
        'length_c': FULLPROF_CELL_LENGTH_C,
    },
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
experiment = ExperimentFactory.from_cif_str(f"""data_pbso4
_edi.schema_version 3
_experiment_type.beam_mode "constant wavelength"
_scattering_source.neutron_scattering_length sears1992
_peak.type cwl-tch-pseudo-voigt
_peak.cutoff_fwhm {FULLPROF_WDT}
_peak.broad_gauss_u {FULLPROF_U}
_peak.broad_gauss_v {FULLPROF_V}
_peak.broad_gauss_w {FULLPROF_W}
_peak.broad_lorentz_x {FULLPROF_X}
_peak.broad_lorentz_y {FULLPROF_Y}
_instrument.setup_wavelength {FULLPROF_WAVELENGTH}
_instrument.calib_twotheta_offset {FULLPROF_ZERO}
loop_
_linked_structure.structure_id
_linked_structure.scale
pbso4 {FULLPROF_SCALE}
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
        max_profile_difference_percent=0.75,
        max_deviation_percent=4.5,
        min_intensity_ratio=0.999,
        max_intensity_ratio=1.001,
        min_correlation=0.99995,
    ),
)
