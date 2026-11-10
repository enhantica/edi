# %% [markdown]
# # Co2SiO4 — powder neutron CW — Co Biso tied by a constraint
#
# Co2SiO4 (D20, ILL, 497 K) with the isotropic displacement parameters of Co1 and
# Co2 refined as one parameter. FullProf ties them with a shared codeword; edi declares
# two aliases and the constraint `biso_Co2 = biso_Co1`, as diffraction-lib's CoSiO
# tutorial does.
#
# **Two checks.** First the fixed twin: FullProf's converged values, every parameter
# fixed, calculated here and compared with FullProf's calculated profile. Then the fit
# itself: edi starts from FullProf's start, declares the constraint through its Python
# API and fits. Co1 and Co2 must come out with the same Biso, and that value must agree
# with FullProf's within five combined standard uncertainties.

# %%
import math

import numpy as np

from edi import ExperimentFactory
from edi import PdCwlData
from edi import Project
from edi import StructureFactory
from edi import verification as verify

# %% [markdown]
# ## Load the FullProf reference

# %%
FULLPROF_PROJECT_DIR = 'pd-neut-cwl_cosio-d20_biso-tied'
FULLPROF_PRF_FILE = 'cosio.prf'
FULLPROF_SUM_FILE = 'cosio.sum'
FULLPROF_BAC_FILE = 'cosio.bac'
FULLPROF_DAT_FILE = 'cosio.dat'
FULLPROF_LABEL = verify.fullprof_label(FULLPROF_PROJECT_DIR, FULLPROF_SUM_FILE)

# Shared by both checks
FULLPROF_SPACE_GROUP = 'P n m a'  # FullProf Space group symbol
FULLPROF_WAVELENGTH = 1.87  # FullProf Lambda
FULLPROF_WDT = 8.0  # FullProf Wdt
FULLPROF_EXCLUDED_REGIONS = [(0.0, 8.0), (150.0, 180.0)]  # FullProf Excluded regions
FULLPROF_BACKGROUND_POSITIONS = [8.5, 9, 10, 11, 12, 15, 25, 30, 50, 70, 90, 110, 130, 149]

# The fixed twin: the tied fit's converged values (the verification .pcr)
TWIN_ZERO = 0.29052  # FullProf Zero
TWIN_SCALE = 1.294665  # FullProf Scale
TWIN_UVWXY = (0.231446, -0.517217, 0.376236, 0.0, 0.010994)  # FullProf U V W X Y
TWIN_CELL = (10.335916, 6.029712, 4.797578)  # FullProf a b c
TWIN_ATOM_SITES = [
    # FullProf Atom, Typ, Wyckoff, (X, Y, Z), Occ (chemical), Biso
    ('Co1', 'Co', 'a', (0.0, 0.0, 0.0), 1.0, 0.67350),
    ('Co2', 'Co', 'c', (0.28089, 0.25, 0.98242), 1.0, 0.67350),
    ('Si', 'Si', 'c', (0.09411, 0.25, 0.42981), 1.0, 0.66774),
    ('O1', 'O', 'c', (0.09066, 0.25, 0.76958), 1.0, 1.11432),
    ('O2', 'O', 'c', (0.44876, 0.25, 0.21563), 1.0, 1.10683),
    ('O3', 'O', 'd', (0.16404, 0.03218, 0.28000), 1.0, 1.32391),
]

# The fit: FullProf's start (the fitting project's full-fit.inp) and its result (full-fit.out)
START_ZERO = 0.290079
START_SCALE = 1.230743
START_UVWXY = (0.230911, -0.514025, 0.372616, 0.0, 0.012942)
START_CELL = (10.335842, 6.029695, 4.797570)
START_BACKGROUND = [
    631.521870,
    589.406220,
    581.828799,
    561.848518,
    539.588392,
    510.502712,
    472.669168,
    461.908577,
    473.213452,
    459.250060,
    448.655426,
    393.452793,
    317.994767,
    260.916498,
]
START_ATOM_SITES = [
    ('Co1', 'Co', 'a', (0.0, 0.0, 0.0), 1.0, 0.98759),
    ('Co2', 'Co', 'c', (0.281984, 0.25, 0.981765), 1.0, 0.98759),
    ('Si', 'Si', 'c', (0.094155, 0.25, 0.429738), 1.0, 0.67424),
    ('O1', 'O', 'c', (0.090899, 0.25, 0.769413), 1.0, 1.04155),
    ('O2', 'O', 'c', (0.448610, 0.25, 0.215465), 1.0, 1.03151),
    ('O3', 'O', 'd', (0.164063, 0.032361, 0.280122), 1.0, 1.29339),
]
FULLPROF_BISO_CO = 0.67350078  # full-fit.out, Biso_Co1_ph1 (Co2 shares it)
FULLPROF_BISO_CO_SU = 0.10028064

x, calc_fullprof = verify.load_fullprof_calc_profile(
    FULLPROF_PROJECT_DIR,
    FULLPROF_PRF_FILE,
    FULLPROF_BAC_FILE,
    TWIN_ZERO,
)

# %% [markdown]
# ## The model, shared by both checks


# %%
def build_structure(cell: tuple, sites: list) -> object:
    """The Co2SiO4 structure at the given cell and sites."""
    return StructureFactory.from_dict({
        'name': 'cosio',
        'space_group': {'name_h_m': FULLPROF_SPACE_GROUP},
        'cell': {'length_a': cell[0], 'length_b': cell[1], 'length_c': cell[2]},
        'atom_sites': [
            {
                'id': site_id,
                'type_symbol': type_symbol,
                'wyckoff_letter': wyckoff,
                'fract': fract,
                'occupancy': occupancy,
                'adp_iso': adp_iso,
            }
            for site_id, type_symbol, wyckoff, fract, occupancy, adp_iso in sites
        ],
    })


def build_experiment(
    zero: float, scale: float, uvwxy: tuple, background: list | None = None
) -> object:
    """The D20 experiment as project-file text; a background is added only when given."""
    u, v, w, lorentz_x, lorentz_y = uvwxy
    excluded = '\n'.join(
        f'{index} {start} {end}'
        for index, (start, end) in enumerate(FULLPROF_EXCLUDED_REGIONS, start=1)
    )
    text = f"""data_d20
_edi.schema_version 3
_experiment_type.beam_mode "constant wavelength"
_peak.type cwl-tch-pseudo-voigt
_peak.cutoff_fwhm {FULLPROF_WDT}
_peak.broad_gauss_u {u}
_peak.broad_gauss_v {v}
_peak.broad_gauss_w {w}
_peak.broad_lorentz_x {lorentz_x}
_peak.broad_lorentz_y {lorentz_y}
_instrument.setup_wavelength {FULLPROF_WAVELENGTH}
_instrument.calib_twotheta_offset {zero}
loop_
_excluded_region.id
_excluded_region.start
_excluded_region.end
{excluded}
loop_
_linked_structure.structure_id
_linked_structure.scale
cosio {scale}
"""
    if background is not None:
        rows = '\n'.join(
            f'{index} {position} {intensity}'
            for index, (position, intensity) in enumerate(
                zip(FULLPROF_BACKGROUND_POSITIONS, background, strict=True), start=1
            )
        )
        text += f"""_background.type line-segment
loop_
_background.id
_background.position
_background.intensity
{rows}
"""
    return ExperimentFactory.from_cif_str(text)


# %% [markdown]
# ## Check 1: the fixed project
#
# FullProf's converged values with no background, against FullProf's calculated profile
# with its background removed.

# %%
project = Project()
project.structure = build_structure(TWIN_CELL, TWIN_ATOM_SITES)
project.experiment = build_experiment(TWIN_ZERO, TWIN_SCALE, TWIN_UVWXY)
verify.set_reference_as_measured(project.experiment, x, calc_fullprof)
project.analysis.calculate()

calc_ed_crysta = verify.restrict_to_included(
    project.experiment, project.experiment.data.intensity_calc
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
    tolerances=verify.AgreementTolerances(),
)

# %% [markdown]
# ## Check 2: the tied fit
#
# FullProf's start, the measured D20 pattern, and FullProf's free set: the background,
# the zero, the scale, U V W Y, the cell lengths, every free coordinate and every Biso,
# with Co2's Biso set by the constraint instead of being free.

# %%
measured = np.loadtxt(
    verify.bundled_reference_dir() / FULLPROF_PROJECT_DIR / FULLPROF_DAT_FILE, skiprows=6
)

tied = Project()
tied.structure = build_structure(START_CELL, START_ATOM_SITES)
tied.experiment = build_experiment(START_ZERO, START_SCALE, START_UVWXY, START_BACKGROUND)
tied.experiment.data = PdCwlData(
    two_theta=list(measured[:, 0]),
    intensity_meas=list(measured[:, 1]),
    intensity_meas_su=list(measured[:, 2]),
)

structure = tied.structure
for length in (structure.cell.length_a, structure.cell.length_b, structure.cell.length_c):
    length.free = True
free_coordinates = {
    'Co2': ('fract_x', 'fract_z'),
    'Si': ('fract_x', 'fract_z'),
    'O1': ('fract_x', 'fract_z'),
    'O2': ('fract_x', 'fract_z'),
    'O3': ('fract_x', 'fract_y', 'fract_z'),
}
for site_id, axes in free_coordinates.items():
    for axis in axes:
        getattr(structure.atom_sites[site_id], axis).free = True
for site_id in ('Co1', 'Si', 'O1', 'O2', 'O3'):
    structure.atom_sites[site_id].adp_iso.free = True

experiment = tied.experiment
experiment.instrument.calib_twotheta_offset.free = True
experiment.linked_structure.scale.free = True
for name in ('broad_gauss_u', 'broad_gauss_v', 'broad_gauss_w', 'broad_lorentz_y'):
    getattr(experiment.peak, name).free = True
for point in experiment.background:
    point.intensity.free = True

tied.analysis.aliases.create(id='biso_Co1', param=structure.atom_sites['Co1'].adp_iso)
tied.analysis.aliases.create(id='biso_Co2', param=structure.atom_sites['Co2'].adp_iso)
tied.analysis.constraints.create(expression='biso_Co2 = biso_Co1')

# %%
result = tied.analysis.fit()
print(f'converged: {result.converged}, reduced chi-square: {result.reduced_chi_square:.4f}')

# %%
biso_co1 = structure.atom_sites['Co1'].adp_iso
biso_co2 = structure.atom_sites['Co2'].adp_iso
print(f'Co1 Biso {biso_co1.value:.6f}({biso_co1.uncertainty:.6f})')
print(f'Co2 Biso {biso_co2.value:.6f}({biso_co2.uncertainty:.6f})')
print(f'FullProf {FULLPROF_BISO_CO:.6f}({FULLPROF_BISO_CO_SU:.6f})')

if not biso_co2.user_constrained:
    raise AssertionError('Co2 Biso is not marked as set by the constraint')
if biso_co1.value != biso_co2.value:
    raise AssertionError(f'Co1 Biso {biso_co1.value!r} differs from Co2 Biso {biso_co2.value!r}')
for biso in (biso_co1, biso_co2):
    bound = 5 * math.hypot(FULLPROF_BISO_CO_SU, biso.uncertainty)
    if abs(biso.value - FULLPROF_BISO_CO) > bound:
        msg = f'Biso {biso.value} is not within {bound} of FullProf {FULLPROF_BISO_CO}'
        raise AssertionError(msg)
