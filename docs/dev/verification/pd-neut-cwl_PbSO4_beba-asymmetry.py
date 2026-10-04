# %% [markdown]
# # PbSO4 — powder neutron CW — Bérar-Baldinozzi asymmetry
#
# Verifies the empirical **Bérar-Baldinozzi** asymmetry
# (`cwl-pseudo-voigt-berar-baldinozzi-asymmetry`) on anglesite. crysta multiplies the TCH
# pseudo-Voigt by the paper's Hermite factor (J. Appl. Cryst. 26, 128 (1993)):
#
# `1 + (A0 F_a(z) + B0 F_b(z)) / tan θ + (A1 F_a(z) + B1 F_b(z)) / tan 2θ`, with
# `z = Δ2θ / H`, `F_a = 2z·exp(-z²)` and `F_b = 2(2z² - 3)·F_a`,
#
# with diffraction-lib's `asym_beba_{a0,b0,a1,b1}` in FullProf's P1..P4 roles. `H` and `θ` are
# taken at the reflection's 2θ_k (ObjCryst's definition).
#
# **The evaluation point is chosen on merit**. Per reflection, the correction is odd in `z` about
# the centre, so it conserves each reflection's integrated intensity exactly. Evaluated at each
# pattern point, as cryspy does, it drifts that intensity by up to +13.8 % at 5° on this page's
# coefficients. It also costs 3.4 times as much per fit iteration. The two are equally stable, and
# fit quality against FullProf, the tie-break, was not needed.
#
# **cryspy is a measured divergence, not the oracle.** cryspy implements the same published
# form, but evaluates `H` and `θ` (and its symmetric core) at each pattern point. It was this
# page's oracle until the evaluation point was chosen on merit. The unfitted comparison at the same
# four coefficients is kept, measured and printed, but no longer gates.
#
# **FullProf's coefficients mean something else — a documented divergence, not an error.**
# Upstream's page states it: *"FullProf and cryspy use different coefficient conventions."* The
# two conventions are the paper's (cryspy's, and crysta's) and FullProf's. FullProf's source is
# closed and crysfml2008 has no Bérar-Baldinozzi, so FullProf's behaviour is known only **as
# inferred in diffraction-lib issue 166** from its calculated output, to the `.prf` precision
# floor. That inference finds two differences:
#
# 1. FullProf uses the opposite sign of `z`.
# 2. Its second function behaves as `F_b ≈ (8z³ - 6z)·exp(-z²)` where the paper's is
#    `(8z³ - 12z)·exp(-z²)`.
#
# Everything else, including both angular factors, agrees. The inferred map from FullProf's
# P1..P4 to the paper's coefficients is `(-P1 - 3·P2, -P2, -P3 - 3·P4, -P4)`. It is not exact —
# the two F_b differ in shape — so FullProf is compared only through that map, or after fitting
# the four coefficients to its profile, never at its raw P values.
#
# **One limit angle, 180°.** FullProf's upstream `.pcr` corrects only reflections below
# `AsyLim` = 160°; cryspy has no limit. Every comparison here uses 180° (owner direction
# 2026-09-26): crysta's `asym_beba_limit` default, cryspy's native behaviour, and a FullProf
# reference regenerated once at authoring time with `AsyLim` = 180 (see its `PROVENANCE.md`).
#
# **Method differences from upstream's page, with the reasons.** Upstream gates only a cryspy
# fit to FullProf. This page gates two comparisons and records a third:
#
# 1. FullProf through the inferred map — **unfitted**;
# 2. FullProf after the same asymmetry-only fit upstream runs;
# 3. unfitted cryspy — the measured divergence, printed, not gated.
#
# A fit alone can be satisfied by a wrong kernel with compensating coefficients, so it is
# never the only check.
#
# **The bounds are labelled regression pins** — this page's own measured closeness with
# stated headroom (crysta per-reflection default, all at the 180° limit):
#
# | comparison | profile diff | max deviation | area ratio | correlation |
# | --- | --- | --- | --- | --- |
# | FullProf, issue-166 map (gated) | 0.83 % | 6.09 % | 0.99987 | 0.9999518 |
# | FullProf, fitted (gated) | 0.83 % | 6.06 % | 0.99984 | 0.9999520 |
# | cryspy, unfitted (measured) | 0.60 % | 0.43 % | 0.99607 | 0.9999784 |
#
# The fit barely moves the mapped coefficients' agreement: the residual is the F_b shape
# difference, which no choice of the paper's coefficients absorbs. Against cryspy, the evaluation
# point alone accounts for 0.108 % at identical coefficients; the rest of the 0.39 % area
# difference is not decomposed here.

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

# cryspy 0.12.1's unfitted calculation of upstream's page, on the same grid (its PROVENANCE.md).
CRYSPY_REFERENCE = (
    verify.bundled_reference_dir().parent / 'cryspy' / FULLPROF_PROJECT_DIR / 'pbso4_cryspy.tsv'
)
LABEL_CRYSPY = 'cryspy 0.12.1'

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
FULLPROF_X = 0.0  # FullProf X
FULLPROF_Y = 0.086818  # FullProf Y
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
cryspy_x, calc_cryspy = np.loadtxt(CRYSPY_REFERENCE, unpack=True)
if not np.array_equal(cryspy_x, x):
    raise ValueError('the cryspy reference must sit on the FullProf grid')

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
# FullProf's P1..P4 enter as the paper's coefficients unchanged — exactly what upstream's page
# hands cryspy before it fits.
#
# The neutron experiment, as project-file text, declares Sears (1992) as its scattering-length
# source — FullProf's own Pb, S and O lengths; cryspy's table is the
# same publication.

# %%
experiment = ExperimentFactory.from_cif_str(f"""data_pbso4
_edi.schema_version 3
_experiment_type.beam_mode "constant wavelength"
_scattering_source.neutron_scattering_length sears1992
_peak.type cwl-pseudo-voigt-berar-baldinozzi-asymmetry
_peak.cutoff_fwhm {FULLPROF_WDT}
_peak.broad_gauss_u {FULLPROF_U}
_peak.broad_gauss_v {FULLPROF_V}
_peak.broad_gauss_w {FULLPROF_W}
_peak.broad_lorentz_x {FULLPROF_X}
_peak.broad_lorentz_y {FULLPROF_Y}
_peak.asym_beba_a0 {FULLPROF_ASY_1}
_peak.asym_beba_b0 {FULLPROF_ASY_2}
_peak.asym_beba_a1 {FULLPROF_ASY_3}
_peak.asym_beba_b1 {FULLPROF_ASY_4}
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
# ## edi-crysta VS cryspy — unfitted, the measured divergence

# %%
project.analysis.calculate()
calc_ed_crysta = np.array(project.experiment.data.intensity_calc)
LABEL_ED_CRYSTA = verify.engine_label('crysta')

verify.plot_pattern_comparison(
    project.experiment,
    reference=calc_cryspy,
    candidate=calc_ed_crysta,
    reference_label=LABEL_CRYSPY,
    candidate_label=LABEL_ED_CRYSTA,
)

# %%
divergence = verify.pattern_closeness(calc_cryspy, calc_ed_crysta)
print(f'{LABEL_ED_CRYSTA} vs {LABEL_CRYSPY} (measured, not gated): {divergence}')

# %% [markdown]
# ## edi-crysta VS FullProf — through issue 166's inferred map
#
# The same calculation with FullProf's P1..P4 carried to the paper's coefficients by the map
# inferred in diffraction-lib issue 166. What remains is the F_b shape difference the map
# cannot absorb.

# %%
peak = project.experiment.peak
peak.asym_beba_a0 = -FULLPROF_ASY_1 - 3.0 * FULLPROF_ASY_2
peak.asym_beba_b0 = -FULLPROF_ASY_2
peak.asym_beba_a1 = -FULLPROF_ASY_3 - 3.0 * FULLPROF_ASY_4
peak.asym_beba_b1 = -FULLPROF_ASY_4

project.analysis.calculate()
calc_ed_crysta_mapped = np.array(project.experiment.data.intensity_calc)
LABEL_ED_CRYSTA_MAPPED = verify.engine_label('crysta', note='issue-166 map')

verify.plot_pattern_comparison(
    project.experiment,
    reference=calc_fullprof,
    candidate=calc_ed_crysta_mapped,
    reference_label=FULLPROF_LABEL,
    candidate_label=LABEL_ED_CRYSTA_MAPPED,
)

# %% [markdown]
# ## Fit edi-crysta's four coefficients to FullProf
#
# Upstream's method: free only the four asymmetry coefficients, every other parameter fixed at
# FullProf's values, and fit the FullProf profile.

# %%
peak.asym_beba_a0.free = True
peak.asym_beba_b0.free = True
peak.asym_beba_a1.free = True
peak.asym_beba_b1.free = True

project.analysis.fit()
for name in ('asym_beba_a0', 'asym_beba_b0', 'asym_beba_a1', 'asym_beba_b1'):
    print(f'{name} = {getattr(peak, name).value:.6f}')

project.analysis.calculate()
calc_ed_crysta_fitted = np.array(project.experiment.data.intensity_calc)
LABEL_ED_CRYSTA_FITTED = verify.engine_label('crysta', note='fitted')

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
        (f'{LABEL_ED_CRYSTA_MAPPED} vs {FULLPROF_LABEL}', calc_fullprof, calc_ed_crysta_mapped),
        (f'{LABEL_ED_CRYSTA_FITTED} vs {FULLPROF_LABEL}', calc_fullprof, calc_ed_crysta_fitted),
    ],
    tolerances=verify.AgreementTolerances(
        max_profile_difference_percent=1.0,
        max_deviation_percent=7.0,
        min_intensity_ratio=0.9995,
        max_intensity_ratio=1.0008,
        min_correlation=0.99993,
    ),
)
