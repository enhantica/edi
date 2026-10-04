# %% [markdown]
# # LBCO — powder neutron CW — basic pseudo-Voigt
#
# **Scattering table.** The experiment declares Sears (1992) —
# `_scattering_source.neutron_scattering_length sears1992`, the
# publication FullProf's own neutron lengths come from — so the page verifies
# FullProf's output against the table FullProf actually used (La, Ba, Co and O
# equal FullProf's values to the digits FullProf carries).
#
# **Occupancies are chemical site fractions.** The `.pcr` `Occ` column carries
# FullProf's multiplicity-weighted notation and never passes through; crysta
# derives the site multiplicity from the symmetry.
#
# **Known and carried by design.** The weak (100) reflection sits ~0.34 % below
# the FullProf net even under the declared table — the five-decimal `.pcr`
# storage residual (occupancies and lengths are stored rounded). Named here
# rather than tuned away; it is what sets the max-deviation bound.
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
FULLPROF_PROJECT_DIR = 'pd-neut-cwl_lbco-hrpt_basic'
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
# The neutron experiment, with its scattering-length source, as project-file text.

# %%
excluded_rows = '\n'.join(
    f'{index} {start} {end}'
    for index, (start, end) in enumerate(FULLPROF_EXCLUDED_REGIONS, start=1)
)
experiment = ExperimentFactory.from_cif_str(f"""data_lbco
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
        max_profile_difference_percent=0.11,
        max_deviation_percent=0.45,
        min_intensity_ratio=0.999,
        max_intensity_ratio=1.001,
        min_correlation=0.99999,
    ),
)
