# %% [markdown]
# # LiF — powder X-ray CW — polarization
#
# Verifies the X-ray polarization correction on the same single-wavelength LiF reference
# as the [single-wavelength page](pd-xray-cwl_LiF_single.ipynb): FullProf `Cthm = 0.8`,
# `Rpolarz = 0.5`, nothing else changed. Every parameter is FullProf's own, fixed —
# nothing is fitted.
#
# **The polarization factor.** A monochromated beam is partially polarized, and each
# reflection's intensity is multiplied by
# `P = 1 - K + K cos²(2θ_m) cos²(2θ)` (FullProf manual section 3.4),
# with `K` the polarization coefficient (`setup_polarization_coefficient`, FullProf
# `Rpolarz`) and `2θ_m` the monochromator angle in degrees
# (`setup_monochromator_twotheta`). FullProf stores `Cthm = cos²(2θ_m)` instead of the
# angle, so `Cthm = 0.8` is `2θ_m = acos(√0.8) = 26.5650511771°`.
#
# **Method — one difference from the diffraction-lib page.** For characteristic radiation
# (`Ilo = 0`, this `.pcr`) FullProf multiplies the Lorentz factor by
# `1 + Cthm cos²(2θ)`, which is exactly twice `P` at `K = 0.5`. diffraction-lib's page
# absorbs that constant by fitting the scale before it compares. This page sets the scale
# to twice FullProf's instead and fits nothing, so the comparison is a forward calculation
# at fixed parameters like its single-wavelength sibling, and a wrong angle dependence
# cannot be hidden by a fitted scale.
#
# **Scattering sources** are declared as on the single-wavelength page: `it1992` f0 and
# `sasaki1989` dispersion.
#
# **Where the factor is applied.** diffraction-lib multiplies the summed pattern by `P` point
# by point; crysta applies it to each reflection at its own Bragg angle (ADR-0076), as FullProf
# does, so the two differ only by the variation of `P` across one reflection's profile.
#
# **The bounds are labelled regression pins** — this page's own measured closeness with stated
# headroom, the single-wavelength page's bounds (profile difference 0.04 %, max deviation 0.04
# %, area ratio 0.999968, correlation 0.999999970), all inside the task's original 1 %
# acceptance bound. Without the polarization factor the pattern differs from FullProf's by 48
# % relative L2, far outside them.

# %%
from edi import ExperimentFactory
from edi import Project
from edi import StructureFactory
from edi import verification as verify

# %% [markdown]
# ## Load the FullProf reference

# %%
FULLPROF_PROJECT_DIR = 'pd-xray-cwl_lif_single-polarization'
FULLPROF_PRF_FILE = 'lif_single_polarized.prf'
FULLPROF_SUM_FILE = 'lif_single_polarized.sum'
FULLPROF_BAC_FILE = 'lif_single_polarized.bac'
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
FULLPROF_POLARIZATION_COEFFICIENT = 0.5  # FullProf Rpolarz
FULLPROF_CTHM = 0.8  # FullProf Cthm = cos^2(2theta_m)
FULLPROF_MONOCHROMATOR_TWOTHETA = 26.5650511771  # acos(sqrt(Cthm)) in degrees

# FullProf's characteristic-radiation factor 1 + Cthm cos^2(2theta) is 2 P at K = 0.5.
FULLPROF_CHARACTERISTIC_FACTOR = 2.0

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
# The X-ray experiment, with its two scattering-source selectors and the two polarization
# parameters, as project-file text.

# %%
experiment = ExperimentFactory.from_cif_str(f"""data_lif
_edi.schema_version 3
_experiment_type.sample_form powder
_experiment_type.radiation_probe xray
_experiment_type.scattering_type bragg
_experiment_type.beam_mode "constant wavelength"
_scattering_source.xray_form_factor it1992
_scattering_source.xray_dispersion sasaki1989
_peak.type cwl-tch-pseudo-voigt
_peak.broad_gauss_u {FULLPROF_U}
_peak.broad_gauss_v {FULLPROF_V}
_peak.broad_gauss_w {FULLPROF_W}
_peak.broad_lorentz_x {FULLPROF_X}
_peak.broad_lorentz_y {FULLPROF_Y}
_peak.cutoff_fwhm {FULLPROF_WDT}
_instrument.calib_twotheta_offset {FULLPROF_ZERO}
_instrument.setup_wavelength {FULLPROF_WAVELENGTH}
_instrument.setup_polarization_coefficient {FULLPROF_POLARIZATION_COEFFICIENT}
_instrument.setup_monochromator_twotheta {FULLPROF_MONOCHROMATOR_TWOTHETA}
loop_
_linked_structure.structure_id
_linked_structure.scale
lif {FULLPROF_CHARACTERISTIC_FACTOR * FULLPROF_SCALE}
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
