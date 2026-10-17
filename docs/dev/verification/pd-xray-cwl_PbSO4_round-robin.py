# %% [markdown]
# # PbSO4 — powder X-ray CW — round robin
#
# Anglesite from the X-ray Rietveld refinement round robin (R. J. Hill, J. Appl. Cryst. 25, 589
# (1992)), with the Cu K-alpha doublet (FullProf `Lambda1`, `Lambda2`, `Ratio = 0.5`), the
# monochromator polarization (`Cthm = 0.8`) and the Bérar-Baldinozzi asymmetry.
#
# **FullProf's model is not one edi has.** The reference is FullProf's Npr 7 (the
# Thompson-Cox-Hastings pseudo-Voigt) with Bérar-Baldinozzi asymmetry. edi pairs
# Bérar-Baldinozzi with the plain pseudo-Voigt (one Caglioti width, linear mixing; FullProf Npr
# 5), and FullProf's Bérar-Baldinozzi coefficients mean something else than the paper's. So, as
# on the [neutron PbSO4 page](pd-neut-cwl_PbSO4_beba-asymmetry.ipynb), the
# page fits the pseudo-Voigt's widths, its mixing and the four asymmetry coefficients to
# FullProf's profile and records how close the Npr 5 shape gets. Everything else is FullProf's
# own and fixed. The page does not count toward diffraction-lib parity.
#
# **Starting point.** The Caglioti widths and mixing that best match FullProf's TCH full width
# and mixing over 10-154 degrees (a least-squares fit of `U tan²θ + V tanθ + W` to the TCH FWHM²,
# FullProf's Gaussian variance taken as 0 where its own U, V, W make it negative), and
# FullProf's Asy1..Asy4 through the map inferred in diffraction-lib issue 166,
# `(-P1 - 3·P2, -P2, -P3 - 3·P4, -P4)`. The asymmetry limit angle is FullProf's `AsyLim`, 160°.
#
# **Polarization.** For characteristic radiation (`Ilo = 0`) FullProf multiplies the Lorentz
# factor by `1 + Cthm cos²(2θ)` and reads no `Rpolarz` (manual section 3.4). That is twice
# `P = 1 - K + K cos²(2θ_m) cos²(2θ)` at `K = 0.5` and `2θ_m = acos(√0.8)`, so the page sets
# `K = 0.5` and twice FullProf's scale, as the
# [polarization page](pd-xray-cwl_LiF_single_polarization.ipynb) does.
#
# **Scattering sources** as on the LiF pages: `it1992` f0 and `sasaki1989` dispersion.
#
# **The bounds are labelled regression pins**: this page's own measured closeness after the fit,
# with stated headroom.
#
# | comparison | profile diff | max deviation | area ratio | correlation |
# | --- | --- | --- | --- | --- |
# | FullProf, fitted (gated) | 0.99 % | 0.80 % | 0.995976 | 0.999947815 |
#
# The remainder is the Npr 5 shape, which has one width and a linear mixing where FullProf's Npr 7
# has two widths; the area ratio is the scale, which stays at FullProf's.

# %%
from edi import ExperimentFactory
from edi import Project
from edi import StructureFactory
from edi import verification as verify

# %% [markdown]
# ## Load the FullProf reference

# %%
FULLPROF_PROJECT_DIR = 'pd-xray-cwl_pbso4-lab_round-robin'
FULLPROF_PRF_FILE = 'pbsox.prf'
FULLPROF_SUM_FILE = 'pbsox.sum'
FULLPROF_BAC_FILE = 'pbsox.bac'
FULLPROF_LABEL = verify.fullprof_label(FULLPROF_PROJECT_DIR, FULLPROF_SUM_FILE)

# Structure
FULLPROF_SPACE_GROUP = 'P n m a'  # FullProf Space group symbol
FULLPROF_CELL_LENGTH_A = 8.485900  # FullProf a
FULLPROF_CELL_LENGTH_B = 5.402259  # FullProf b
FULLPROF_CELL_LENGTH_C = 6.964587  # FullProf c
FULLPROF_ATOM_SITES = [
    # FullProf Atom, Typ, Wyckoff, (X, Y, Z), Occ (chemical), Biso
    ('Pb', 'Pb', 'c', (0.18822, 0.25, 0.16711), 1.0, 1.86290),
    ('S', 'S', 'c', (0.06306, 0.25, 0.68485), 1.0, 1.34971),
    ('O1', 'O', 'c', (0.90281, 0.25, 0.59724), 1.0, 1.19713),
    ('O2', 'O', 'c', (0.18443, 0.25, 0.54586), 1.0, 2.56174),
    ('O3', 'O', 'd', (0.08094, 0.02239, 0.81289), 1.0, 1.37463),
]

# Experiment
FULLPROF_ZERO = 0.00363  # FullProf Zero
FULLPROF_SCALE = 0.0004703142  # FullProf Scale
FULLPROF_WAVELENGTH = 1.540560  # FullProf Lambda1
FULLPROF_WAVELENGTH_2 = 1.544400  # FullProf Lambda2
FULLPROF_WAVELENGTH_2_TO_1_RATIO = 0.5  # FullProf Ratio
FULLPROF_CTHM = 0.8  # FullProf Cthm = cos^2(2theta_m)
POLARIZATION_COEFFICIENT = 0.5  # characteristic radiation (FullProf Ilo = 0)
MONOCHROMATOR_TWOTHETA = 26.5650511771  # acos(sqrt(Cthm)) in degrees
U_START = 0.065374  # FullProf's TCH FWHM, fitted as Caglioti U, V, W
V_START = -0.102354
W_START = 0.047897
ETA_0_START = 0.625  # FullProf's TCH mixing, fitted as eta_0 + eta_1 2theta
FULLPROF_WDT = 48.0  # FullProf Wdt
FULLPROF_ASY_1 = -0.41356  # FullProf Asy1 (P1)
FULLPROF_ASY_2 = 0.0  # FullProf Asy2 (P2)
FULLPROF_ASY_3 = 1.26777  # FullProf Asy3 (P3)
FULLPROF_ASY_4 = 0.0  # FullProf Asy4 (P4)
FULLPROF_ASY_LIM = 160.0  # FullProf AsyLim
FULLPROF_EXCLUDED_REGIONS = [(0.0, 10.0), (154.0, 180.0)]  # FullProf excluded regions

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
# The X-ray experiment as project-file text: the doublet, the polarization at twice FullProf's
# scale, and the pseudo-Voigt with Bérar-Baldinozzi asymmetry at its starting values.

# %%
excluded_rows = '\n'.join(
    f'{index} {start} {end}'
    for index, (start, end) in enumerate(FULLPROF_EXCLUDED_REGIONS, start=1)
)
experiment = ExperimentFactory.from_cif_str(f"""data_pbso4
_edi.schema_version 3
_experiment_type.sample_form powder
_experiment_type.radiation_probe xray
_experiment_type.scattering_type bragg
_experiment_type.beam_mode "constant wavelength"
_scattering_source.xray_form_factor it1992
_scattering_source.xray_dispersion sasaki1989
_peak.type cwl-pseudo-voigt-berar-baldinozzi
_peak.cutoff_fwhm {FULLPROF_WDT}
_peak.broad_gauss_u {U_START}
_peak.broad_gauss_v {V_START}
_peak.broad_gauss_w {W_START}
_peak.mixing_eta_0 {ETA_0_START}
_peak.mixing_eta_1 0
_peak.asym_beba_a0 {-FULLPROF_ASY_1 - 3.0 * FULLPROF_ASY_2}
_peak.asym_beba_b0 {-FULLPROF_ASY_2}
_peak.asym_beba_a1 {-FULLPROF_ASY_3 - 3.0 * FULLPROF_ASY_4}
_peak.asym_beba_b1 {-FULLPROF_ASY_4}
_peak.asym_beba_limit {FULLPROF_ASY_LIM}
_instrument.calib_twotheta_offset {FULLPROF_ZERO}
_instrument.setup_wavelength {FULLPROF_WAVELENGTH}
_instrument.setup_wavelength_2 {FULLPROF_WAVELENGTH_2}
_instrument.setup_wavelength_2_to_1_ratio {FULLPROF_WAVELENGTH_2_TO_1_RATIO}
_instrument.setup_polarization_coefficient {POLARIZATION_COEFFICIENT}
_instrument.setup_monochromator_twotheta {MONOCHROMATOR_TWOTHETA}
loop_
_excluded_region.id
_excluded_region.start
_excluded_region.end
{excluded_rows}
loop_
_linked_structure.structure_id
_linked_structure.scale
pbso4 {2.0 * FULLPROF_SCALE}
""")

# %% [markdown]
# ## Build the project

# %%
project = Project()
project.structure = structure
project.experiment = experiment
verify.set_reference_as_measured(project.experiment, x, calc_fullprof)

# %% [markdown]
# ## Fit the pseudo-Voigt and its asymmetry to FullProf
#
# The widths, the mixing and the four coefficients are free; the structure, the scale and the
# instrument stay at FullProf's values.

# %%
peak = project.experiment.peak
for name in (
    'broad_gauss_u',
    'broad_gauss_v',
    'broad_gauss_w',
    'mixing_eta_0',
    'mixing_eta_1',
    'asym_beba_a0',
    'asym_beba_b0',
    'asym_beba_a1',
    'asym_beba_b1',
):
    getattr(peak, name).free = True

project.analysis.fit()
for name in (
    'broad_gauss_u',
    'broad_gauss_v',
    'broad_gauss_w',
    'mixing_eta_0',
    'mixing_eta_1',
    'asym_beba_a0',
    'asym_beba_b0',
    'asym_beba_a1',
    'asym_beba_b1',
):
    print(f'{name} = {getattr(peak, name).value:.6f}')

# %% [markdown]
# ## Calculate the fitted pattern

# %%
project.analysis.calculate()

# %% [markdown]
# ## edi-crysta VS FullProf

# %%
calc_ed_crysta_fitted = verify.restrict_to_included(
    project.experiment,
    project.experiment.data.intensity_calc,
)
LABEL_ED_CRYSTA_FITTED = verify.engine_label('crysta', note='pseudo-Voigt, fitted')

verify.plot_pattern_comparison(
    project.experiment,
    reference=calc_fullprof,
    candidate=calc_ed_crysta_fitted,
    reference_label=FULLPROF_LABEL,
    candidate_label=LABEL_ED_CRYSTA_FITTED,
)

# %%
verify.assert_patterns_agree(
    [
        (
            f'{LABEL_ED_CRYSTA_FITTED} vs {FULLPROF_LABEL}',
            verify.restrict_to_included(project.experiment, calc_fullprof),
            calc_ed_crysta_fitted,
        ),
    ],
    tolerances=verify.AgreementTolerances(
        max_profile_difference_percent=1.2,
        max_deviation_percent=1.0,
        min_intensity_ratio=0.995,
        max_intensity_ratio=1.001,
        min_correlation=0.99993,
    ),
)
