# %% [markdown]
# # LiF — powder X-ray CW — absorption
#
# The [single-wavelength LiF page](pd-xray-cwl_LiF_single.ipynb) with the Debye-Scherrer
# cylinder absorption correction (Hewat) switched on: `_absorption.type cylinder-hewat` with
# μR = 0.9 (FullProf `muR`). Nothing else differs from that page's FullProf input, and the data
# file is the same bytes. Every parameter is FullProf's own, fixed; nothing is fitted.
#
# **Where the factor is applied.** crysta applies the Hewat factor to each reflection at its own
# Bragg θ, as FullProf corrects per-reflection intensities. diffraction-lib applies it point by
# point on the 2θ grid. This page compares both against FullProf, as the
# [neutron absorption page](pd-neut-cwl_LaB6_absorption.ipynb) does.
#
# **Scattering sources** are declared as on the single-wavelength page: `it1992` f0 and
# `sasaki1989` dispersion.
#
# **The bounds are labelled regression pins**, the single-wavelength page's. Measured here, the
# per-reflection pattern differs from FullProf's by 0.05 % (max deviation 0.04 %, area ratio
# 0.999914, correlation 0.999999926). The pointwise one, plotted below but not gated, differs by
# 0.05 % (0.04 %, 0.999895, 0.999999918): LiF's peaks are narrow, so at μR = 0.9 the two
# applications barely differ.

# %%
import numpy as np

from edi import ExperimentFactory
from edi import Parameter
from edi import Project
from edi import StructureFactory
from edi import verification as verify

# %% [markdown]
# ## Load the FullProf reference

# %%
FULLPROF_PROJECT_DIR = 'pd-xray-cwl_lif_single-absorption'
FULLPROF_PRF_FILE = 'lif_single_absorption.prf'
FULLPROF_SUM_FILE = 'lif_single_absorption.sum'
FULLPROF_BAC_FILE = 'lif_single_absorption.bac'
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
FULLPROF_MU_R = 0.9  # FullProf muR

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
# The X-ray experiment as project-file text. The absorption category is set through its typed
# selector after the build: `cylinder-hewat` carries the one refinable `mu_r` (μR = μ·R, R the
# cylinder radius).

# %%
EXPERIMENT_EDI = f"""data_lif
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
loop_
_linked_structure.structure_id
_linked_structure.scale
lif {FULLPROF_SCALE}
"""

# %% [markdown]
# ## Build the project

# %%
experiment = ExperimentFactory.from_cif_str(EXPERIMENT_EDI)
project = Project()
project.structure = structure
project.experiment = experiment
verify.set_reference_as_measured(project.experiment, x, calc_fullprof)
project.experiment.absorption.type = 'cylinder-hewat'

# %% [markdown]
# ## Calculate the pattern

# %%
project.experiment.absorption.mu_r = Parameter(FULLPROF_MU_R)
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

# %% [markdown]
# ## Per-reflection VS pointwise application
#
# The same Hewat factor applied the way diffraction-lib applies it, at each grid point's
# θ = 2θ/2, on top of the pattern without absorption. Shown for comparison, not gated.

# %%
project.experiment.absorption.mu_r = Parameter(0.0)  # the Hewat factor is exactly 1 here
project.analysis.calculate()
calc_unabsorbed = np.array(project.experiment.data.intensity_calc, dtype=float)
project.experiment.absorption.mu_r = Parameter(FULLPROF_MU_R)
project.analysis.calculate()

sin2_theta = np.sin(np.radians(np.asarray(x, dtype=float)) / 2.0) ** 2
hewat_grid_factor = np.exp(
    -(1.7133 - 0.0368 * sin2_theta) * FULLPROF_MU_R
    + (0.0927 + 0.375 * sin2_theta) * FULLPROF_MU_R**2
)
calc_pointwise = verify.restrict_to_included(
    project.experiment,
    calc_unabsorbed * hewat_grid_factor,
)
LABEL_POINTWISE = 'pointwise Hewat (diffraction-lib convention)'

verify.plot_pattern_comparison(
    project.experiment,
    reference=calc_fullprof,
    candidate=calc_pointwise,
    reference_label=FULLPROF_LABEL,
    candidate_label=LABEL_POINTWISE,
)

# %% [markdown]
# ## Agreement check
#
# The shipped per-reflection application against FullProf is the page's claim.

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
