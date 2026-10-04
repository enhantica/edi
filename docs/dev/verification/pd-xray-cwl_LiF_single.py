# %% [markdown]
# # LiF — powder X-ray CW — single wavelength
#
# Verifies the baseline LiF Cu K-alpha1 pattern with a pseudo-Voigt profile and no
# polarization or absorption correction (FullProf `Cthm = 0`, `Rpolarz = 0`: the
# Lorentz-polarization factor is the Lorentz factor alone). Every parameter is
# FullProf's own, fixed — nothing is fitted, not even the scale (upstream's page fits
# it; this one does not need to).
#
# **Scattering sources.** X-ray intensities depend on which f0 and anomalous-dispersion
# tables are used, so the experiment declares them: the International Tables Vol. C
# 4-Gaussian f0 (`it1992`, the coefficients FullProf's `.out` lists for Li and F) and
# Sasaki's 1989 Cromer-Liberman dispersion table (`sasaki1989`), which FullProf's own
# uncited lab-line table matches for these elements (F f'/f'' = 0.069/0.053 at Cu K-alpha1).
# They are declared in the experiment's `.edi` text, which is how a project carries them.
# With crysta's defaults (`wk1995` + `cromer-liberman`) the pattern differs from FullProf by
# 0.19 % relative L2, and without dispersion by 2.4 %.
#
# **The bounds are labelled regression pins** — this page's own measured closeness with
# stated headroom (profile difference 0.04 %, max deviation 0.04 %, area ratio
# 0.999927, correlation 0.999999967), all inside the task's original 1 % acceptance
# bound.

# %%
from edi import ExperimentFactory
from edi import Project
from edi import StructureFactory
from edi import verification as verify

# %% [markdown]
# ## Load the FullProf reference

# %%
FULLPROF_PROJECT_DIR = 'pd-xray-cwl_lif_single'
FULLPROF_PRF_FILE = 'lif_single_unpolarized.prf'
FULLPROF_SUM_FILE = 'lif_single_unpolarized.sum'
FULLPROF_BAC_FILE = 'lif_single_unpolarized.bac'
FULLPROF_LABEL = verify.fullprof_label(FULLPROF_PROJECT_DIR, FULLPROF_SUM_FILE)

# Structure
FULLPROF_SPACE_GROUP = 'F m -3 m'  # FullProf Space group symbol
FULLPROF_CELL_LENGTH_A = 4.026700  # FullProf a
FULLPROF_ATOM_SITES = [
    # FullProf Atom, Typ, Wyckoff, (X, Y, Z), Occ (chemical), Biso
    ('Li1', 'Li', 'a', (0.0, 0.0, 0.0), 1.0, 1.20000),
    ('F1', 'F', 'b', (0.5, 0.5, 0.5), 1.0, 0.80000),
]

# Experiment
FULLPROF_ZERO = 0.0  # FullProf Zero
FULLPROF_SCALE = 0.01  # FullProf Scale
FULLPROF_WAVELENGTH = 1.540560  # FullProf Lambda1
FULLPROF_U = 0.048457  # FullProf U
FULLPROF_V = -0.083053  # FullProf V
FULLPROF_W = 0.040000  # FullProf W
FULLPROF_X = 0.0  # FullProf X
FULLPROF_Y = 0.049268  # FullProf Y
FULLPROF_WDT = 48.0  # FullProf Wdt

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
    'name': 'lif',
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
# The X-ray experiment, with its two scattering-source selectors, as project-file text.

# %%
experiment = ExperimentFactory.from_cif_str(f"""data_lif
_edi.schema_version 3
_experiment_type.sample_form powder
_experiment_type.radiation_probe xray
_experiment_type.scattering_type bragg
_experiment_type.beam_mode "constant wavelength"
_scattering_source.xray_form_factor it1992
_scattering_source.xray_dispersion sasaki1989
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
_linked_structure.structure_id
_linked_structure.scale
lif {FULLPROF_SCALE}
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
        max_profile_difference_percent=0.10,
        max_deviation_percent=0.10,
        min_intensity_ratio=0.9995,
        max_intensity_ratio=1.0005,
        min_correlation=0.999999,
    ),
)
