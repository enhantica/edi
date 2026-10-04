# %% [markdown]
# # Y2O3 — powder neutron CW — isotropic ADPs
#
# **Scattering table.** The experiment declares Sears (1992) —
# `_scattering_source.neutron_scattering_length sears1992`, the
# publication FullProf's own neutron lengths come from (Y and O equal FullProf's
# values).
#
# **Occupancies are chemical site fractions** (all fully occupied). The `.pcr`
# `Occ` column carries FullProf's multiplicity-weighted values (0.50000, 0.16667,
# 1.00000 for the 24d, 8b and 48e sites) and never passes through.
#
# **No Lorentzian broadening** is authored upstream (X and Y absent), so this
# pattern is pure Gaussian — which is why its agreement is far tighter than the
# other CW pages: with no Lorentzian component there is no tail intensity for the
# peak-base cutoff to truncate.
#
# **The bounds are labelled regression pins**, and they are the only CW gate
# tight enough to discriminate the declared table from edi's default (which
# differs only in O, 5.8037 vs 5.803 fm: measured 0.0127 % profile — a bound
# violation — under the default).

# %%
from edi import ExperimentFactory
from edi import Project
from edi import StructureFactory
from edi import verification as verify

# %% [markdown]
# ## Load the FullProf reference

# %%
FULLPROF_PROJECT_DIR = 'pd-neut-cwl_y2o3_isotropic-adp'
FULLPROF_PRF_FILE = 'y2o3_isotropic_adp.prf'
FULLPROF_SUM_FILE = 'y2o3_isotropic_adp.sum'
FULLPROF_BAC_FILE = 'y2o3_isotropic_adp.bac'
FULLPROF_LABEL = verify.fullprof_label(FULLPROF_PROJECT_DIR, FULLPROF_SUM_FILE)

# Structure
FULLPROF_SPACE_GROUP = 'I a -3'  # FullProf Space group symbol
FULLPROF_CELL_LENGTH_A = 10.605744  # FullProf a
FULLPROF_ATOM_SITES = [
    # FullProf Atom, Typ, Wyckoff, (X, Y, Z), Occ (chemical), Biso
    ('Y1', 'Y', 'd', (-0.03236, 0.0, 0.25), 1.0, 0.3),
    ('Y2', 'Y', 'b', (0.25, 0.25, 0.25), 1.0, 0.3),
    ('O1', 'O', 'e', (0.39072, 0.15204, 0.38030), 1.0, 0.5),
]
# Experiment
FULLPROF_ZERO = -0.01625  # FullProf Zero
FULLPROF_SCALE = 1.0602  # FullProf Scale
FULLPROF_WAVELENGTH = 1.54822  # FullProf Lambda
FULLPROF_U = 0.036631  # FullProf U
FULLPROF_V = -0.068345  # FullProf V
FULLPROF_W = 0.131426  # FullProf W
FULLPROF_X = 0.0  # FullProf X (absent upstream)
FULLPROF_Y = 0.0  # FullProf Y (absent upstream)
FULLPROF_WDT = 20.0  # FullProf Wdt
FULLPROF_EXCLUDED_REGIONS = [(0.0, 12.0), (137.5, 180.0)]  # FullProf Excluded regions

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
    'name': 'y2o3',
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
experiment = ExperimentFactory.from_cif_str(f"""data_y2o3
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
y2o3 {FULLPROF_SCALE}
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
        max_profile_difference_percent=0.01,
        max_deviation_percent=0.01,
        min_intensity_ratio=0.9999,
        max_intensity_ratio=1.0001,
        min_correlation=0.999999,
    ),
)
