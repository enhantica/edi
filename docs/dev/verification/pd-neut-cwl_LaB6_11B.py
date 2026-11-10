# %% [markdown]
# # LaB6 — powder neutron CW — 11B isotope
#
# The baseline LaB6 pattern with 11B instead of natural boron.
#
# **Scattering table.** The experiment declares Sears (1992) —
# `_scattering_source.neutron_scattering_length sears1992`. Sears
# tabulates the isotope, and its `11B` row (6.65 fm) is the value the reference
# `.pcr`'s own "Additional scattering factors" line carries; La is FullProf's own
# value too. An isotope no declared source carries fails closed rather than
# silently reverting to natural boron.
#
# **Known and carried by design.** Like the natural-boron page, the profile-level
# deviation is dominated by Lorentzian tail truncation at the tight peak base
# (Wdt = 12) — a stated modelling convention, not a tuning target.
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
FULLPROF_PROJECT_DIR = 'pd-neut-cwl_lab6-echidna_11b'
FULLPROF_PRF_FILE = 'ECH0030684_LaB6_1p622A_11B.prf'
FULLPROF_SUM_FILE = 'ECH0030684_LaB6_1p622A_11B.sum'
FULLPROF_BAC_FILE = 'ECH0030684_LaB6_1p622A_11B.bac'
FULLPROF_LABEL = verify.fullprof_label(FULLPROF_PROJECT_DIR, FULLPROF_SUM_FILE)

# Structure
FULLPROF_SPACE_GROUP = 'P m -3 m'  # FullProf Space group symbol
FULLPROF_CELL_LENGTH_A = 4.156885  # FullProf a
FULLPROF_ATOM_SITES = [
    # FullProf Atom, Typ, Wyckoff, (X, Y, Z), Occ (chemical), Biso
    ('La', 'La', 'a', (0.0, 0.0, 0.0), 1.0, 0.25812),
    ('B', '11B', 'f', (0.19972, 0.5, 0.5), 1.0, 0.11925),  # FullProf Additional B11
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
        max_profile_difference_percent=0.19,
        max_deviation_percent=0.58,
        min_intensity_ratio=0.999,
        max_intensity_ratio=1.001,
        min_correlation=0.99999,
    ),
)
