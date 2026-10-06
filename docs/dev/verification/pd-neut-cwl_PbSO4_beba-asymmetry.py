# %% [markdown]
# # PbSO4 — powder neutron CW — Bérar-Baldinozzi asymmetry
#
# Verifies the empirical **Bérar-Baldinozzi** asymmetry on the **pseudo-Voigt**
# (`cwl-pseudo-voigt-berar-baldinozzi`, FullProf's Npr 5) on anglesite. crysta multiplies the
# pseudo-Voigt by the paper's Hermite factor (J. Appl. Cryst. 26, 128 (1993)):
#
# `1 + (A0 F_a(z) + B0 F_b(z)) / tan θ + (A1 F_a(z) + B1 F_b(z)) / tan 2θ`, with
# `z = Δ2θ / H`, `F_a = 2z·exp(-z²)` and `F_b = 2(2z² - 3)·F_a`,
#
# with diffraction-lib's `asym_beba_{a0,b0,a1,b1}` in FullProf's P1..P4 roles. `H` and `θ` are
# taken at the reflection's 2θ_k (ObjCryst's definition), which conserves each reflection's
# integrated intensity exactly. The pseudo-Voigt has one Caglioti width
# `H² = U tan²θ + V tanθ + W` and the mixing `η = η₀ + η₁·2θ`.
#
# **The model changed on 2026-10-05.** Until then this page used the TCH pseudo-Voigt with
# Bérar-Baldinozzi, diffraction-lib's model and FullProf's Npr 7 with asymmetry. That pair is
# removed: Bérar-Baldinozzi now acts on the pseudo-Voigt, its usual partner.
# FullProf's reference is still the Npr 7 calculation, so no parameter set reproduces it exactly.
# The page fits the pseudo-Voigt's widths, mixing and the four coefficients to FullProf's profile
# and records how close the Npr 5 shape gets. It no longer uses diffraction-lib's model, so it no
# longer counts toward diffraction-lib parity, and the cryspy comparison of the old model is gone.
#
# **FullProf's coefficients mean something else.** FullProf's source is closed; as inferred in
# diffraction-lib issue 166 from its calculated output, it uses the opposite sign of `z` and its
# second function behaves as `F_b ≈ (8z³ - 6z)·exp(-z²)`. The inferred map from its P1..P4 to the
# paper's coefficients, `(-P1 - 3·P2, -P2, -P3 - 3·P4, -P4)`, gives the fit its starting point.
#
# **One limit angle, 180°**, crysta's default, and the FullProf reference regenerated once at
# authoring time with `AsyLim` = 180 (see its `PROVENANCE.md`).
#
# **The bounds are labelled regression pins** — this page's own measured closeness after the fit,
# with stated headroom:
#
# | comparison | profile diff | max deviation | area ratio | correlation |
# | --- | --- | --- | --- | --- |
# | FullProf, fitted (gated) | 1.08 % | 5.96 % | 1.00170 | 0.9999191 |
#
# The old TCH model reached 0.83 % on the same profile; the remainder is the Npr 5 shape, which
# has one width and a linear mixing where FullProf's Npr 7 has two widths.

# %%
import numpy as np

from edi import ExperimentFactory
from edi import Project
from edi import StructureFactory
from edi import verification as verify

# %% [markdown]
# ## Load the references

# %%
FULLPROF_PROJECT_DIR = 'pd-neut-cwl_pbso4_beba-asymmetry'
FULLPROF_PRF_FILE = 'pbso4.prf'
FULLPROF_SUM_FILE = 'pbso4.sum'
FULLPROF_BAC_FILE = 'pbso4.bac'
FULLPROF_LABEL = verify.fullprof_label(FULLPROF_PROJECT_DIR, FULLPROF_SUM_FILE)

# Structure
FULLPROF_SPACE_GROUP = 'P n m a'  # FullProf Space group symbol
FULLPROF_CELL_LENGTH_A = 8.479506  # FullProf a
FULLPROF_CELL_LENGTH_B = 5.397256  # FullProf b
FULLPROF_CELL_LENGTH_C = 6.958973  # FullProf c
FULLPROF_ATOM_SITES = [
    # FullProf Atom, Typ, Wyckoff, (X, Y, Z), Occ (chemical), Biso
    ('Pb', 'Pb', 'c', (0.18752, 0.25, 0.16705), 1.0, 1.39017),
    ('S', 'S', 'c', (0.06549, 0.25, 0.68373), 1.0, 0.39270),
    ('O1', 'O', 'c', (0.90816, 0.25, 0.59544), 1.0, 1.99307),
    ('O2', 'O', 'c', (0.19355, 0.25, 0.54331), 1.0, 1.47771),
    ('O3', 'O', 'd', (0.08109, 0.02727, 0.80869), 1.0, 1.30007),
]
# Experiment
FULLPROF_ZERO = -0.08424  # FullProf Zero
FULLPROF_SCALE = 1.463815  # FullProf Scale
FULLPROF_WAVELENGTH = 1.912000  # FullProf Lambda
FULLPROF_U = 0.153402  # FullProf U
FULLPROF_V = -0.453103  # FullProf V
FULLPROF_W = 0.419409  # FullProf W
ETA_0_START = 0.25  # near the TCH mixing at mid-angle
FULLPROF_WDT = 30.0  # FullProf Wdt
FULLPROF_ASY_1 = 0.29465  # FullProf Asy1 (P1)
FULLPROF_ASY_2 = 0.02261  # FullProf Asy2 (P2)
FULLPROF_ASY_3 = -0.10961  # FullProf Asy3 (P3)
FULLPROF_ASY_4 = 0.04941  # FullProf Asy4 (P4)
FULLPROF_ASY_LIM = 180.0  # FullProf AsyLim, regenerated at 180 (upstream: 160)

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
# FullProf's Gaussian widths and its P1..P4 through issue 166's map are the fit's starts; the
# mixing starts near the TCH value at mid-angle. The neutron experiment, as project-file text,
# declares Sears (1992) as its scattering-length source, FullProf's own Pb, S and O lengths.

# %%
experiment = ExperimentFactory.from_cif_str(f"""data_pbso4
_edi.schema_version 3
_experiment_type.beam_mode "constant wavelength"
_scattering_source.neutron_scattering_length sears1992
_peak.type cwl-pseudo-voigt-berar-baldinozzi
_peak.cutoff_fwhm {FULLPROF_WDT}
_peak.broad_gauss_u {FULLPROF_U}
_peak.broad_gauss_v {FULLPROF_V}
_peak.broad_gauss_w {FULLPROF_W}
_peak.mixing_eta_0 {ETA_0_START}
_peak.mixing_eta_1 0
_peak.asym_beba_a0 {-FULLPROF_ASY_1 - 3.0 * FULLPROF_ASY_2}
_peak.asym_beba_b0 {-FULLPROF_ASY_2}
_peak.asym_beba_a1 {-FULLPROF_ASY_3 - 3.0 * FULLPROF_ASY_4}
_peak.asym_beba_b1 {-FULLPROF_ASY_4}
_peak.asym_beba_limit {FULLPROF_ASY_LIM}
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

project.analysis.calculate()
calc_ed_crysta_fitted = np.array(project.experiment.data.intensity_calc)
LABEL_ED_CRYSTA_FITTED = verify.engine_label('crysta', note='pseudo-Voigt, fitted')

verify.plot_pattern_comparison(
    project.experiment,
    reference=calc_fullprof,
    candidate=calc_ed_crysta_fitted,
    reference_label=FULLPROF_LABEL,
    candidate_label=LABEL_ED_CRYSTA_FITTED,
)

# %%
print(verify.pattern_closeness(calc_fullprof, calc_ed_crysta_fitted))
verify.assert_patterns_agree(
    [(f'{LABEL_ED_CRYSTA_FITTED} vs {FULLPROF_LABEL}', calc_fullprof, calc_ed_crysta_fitted)],
    tolerances=verify.AgreementTolerances(
        max_profile_difference_percent=1.3,
        max_deviation_percent=7.0,
        min_intensity_ratio=0.9995,
        max_intensity_ratio=1.003,
        min_correlation=0.99990,
    ),
)
