"""CoSiO/D20 sequential temperature-scan fit — a diffraction-lib tutorial port."""
# %% [markdown]
# # Structure Refinement: Co2SiO4, D20 (T-scan)
#
# This example demonstrates a Rietveld refinement of the Co2SiO4 crystal
# structure using constant-wavelength neutron powder diffraction data
# from D20 at ILL. A sequential refinement is performed against a
# temperature scan using sequential fitting, which processes each data
# file independently without loading all datasets into memory at once.

# %% [markdown]
# > ⛔ **Execution-disabled**: this tutorial is committed ahead of the API it
# > exercises and stays out of notebook execution until **sequential-scan-tutorial** lands — see
# > `execution-exclusions.yml`, whose list shrinks to empty as unblocking tasks land.

# %% [markdown]
# ## 🛠️ Import Library

# %%
import edi

# %% [markdown]
# ## 📦 Define Project
#
# The project object manages structures, experiments, analysis, display,
# and other related components.

# %%
project = edi.Project(name='cosio_d20_scan')
analysis = project.analysis
display = project.display

# %% [markdown]
# The project must be saved before running sequential fitting, so that
# results can be written to `analysis/results.csv`.

# %%
project.save_as(dir_path='projects/refine-cosio-d20-tscan')

# %% [markdown]
# ## 🧩 Define Structure
#
# This section shows how to add structures and modify their
# parameters.
#
# ### Create Structure

# %%
project.structures.create(name='cosio')
struct = project.structures['cosio']

# %% [markdown]
# ### Set Space Group

# %%
struct.space_group.name_h_m = 'P n m a'
struct.space_group.coord_system_code = 'abc'

# %% [markdown]
# ### Set Unit Cell

# %%
struct.cell.length_a = 10.31
struct.cell.length_b = 6.0
struct.cell.length_c = 4.79

# %% [markdown]
# ### Set Atom Sites

# %%
struct.atom_sites.create(
    id='Co1',
    type_symbol='Co',
    fract_x=0,
    fract_y=0,
    fract_z=0,
    adp_iso=0.3,
)
struct.atom_sites.create(
    id='Co2',
    type_symbol='Co',
    fract_x=0.279,
    fract_y=0.25,
    fract_z=0.985,
    adp_iso=0.3,
)
struct.atom_sites.create(
    id='Si',
    type_symbol='Si',
    fract_x=0.094,
    fract_y=0.25,
    fract_z=0.429,
    adp_iso=0.34,
)
struct.atom_sites.create(
    id='O1',
    type_symbol='O',
    fract_x=0.091,
    fract_y=0.25,
    fract_z=0.771,
    adp_iso=0.63,
)
struct.atom_sites.create(
    id='O2',
    type_symbol='O',
    fract_x=0.448,
    fract_y=0.25,
    fract_z=0.217,
    adp_iso=0.59,
)
struct.atom_sites.create(
    id='O3',
    type_symbol='O',
    fract_x=0.164,
    fract_y=0.032,
    fract_z=0.28,
    adp_iso=0.83,
)

# %% [markdown]
# ### Display Structure

# %%
project.structure_style.atom_view = 'adp'
project.display.structure(struct_name='cosio')

# %% [markdown]
# ## 🔬 Define Experiment
#
# For sequential fitting, we create a single template experiment from
# the first data file. This template defines the instrument, peak
# profile, background, and linked structures that will be reused for every
# data file in the scan.
#
# ### Download Data

# %%
zip_path = edi.download_data('meas-cosio-d20-scan-3f', destination='data')

# %% [markdown]
# ### Extract Data Files

# %%
scan_data_dir = 'experiments/d20_scan'
data_paths = edi.extract_data_paths_from_zip(
    zip_path,
    destination=project.metadata.path / scan_data_dir,
)

# %% [markdown]
# ### Create Template Experiment

# %%
project.experiments.add_from_data_path(
    name='d20',
    data_path=data_paths[0],
)
expt = project.experiments['d20']

# %% [markdown]
# ### Set Instrument

# %%
expt.instrument.setup_wavelength = 1.87
expt.instrument.calib_twotheta_offset = 0.29

# %% [markdown]
# ### Set Peak Profile

# %%
expt.peak.broad_gauss_u = 0.24
expt.peak.broad_gauss_v = -0.53
expt.peak.broad_gauss_w = 0.38
expt.peak.broad_lorentz_y = 0.02
expt.peak.cutoff_fwhm = 8

# %% [markdown]
# ### Set Excluded Regions

# %%
expt.excluded_regions.create(id='1', start=0, end=8)
expt.excluded_regions.create(id='2', start=150, end=180)

# %% [markdown]
# ### Set Background

# %%
expt.background.create(id='1', position=8, intensity=609)
expt.background.create(id='2', position=9, intensity=581)
expt.background.create(id='3', position=10, intensity=563)
expt.background.create(id='4', position=11, intensity=540)
expt.background.create(id='5', position=12, intensity=520)
expt.background.create(id='6', position=15, intensity=507)
expt.background.create(id='7', position=25, intensity=463)
expt.background.create(id='8', position=30, intensity=434)
expt.background.create(id='9', position=50, intensity=451)
expt.background.create(id='10', position=70, intensity=431)
expt.background.create(id='11', position=90, intensity=414)
expt.background.create(id='12', position=110, intensity=361)
expt.background.create(id='13', position=130, intensity=292)
expt.background.create(id='14', position=150, intensity=241)

# %% [markdown]
# ### Set Linked Structures

# %%
expt.linked_structures.create(structure_id='cosio', scale=1.2)

# %% [markdown]
# ## 🚀 Perform Analysis
#
# This section shows how to set free parameters, define constraints,
# and run the sequential refinement.

# %% [markdown]
# ### Set Free Parameters

# %%
struct.cell.length_a.free = True
struct.cell.length_b.free = True
struct.cell.length_c.free = True

struct.atom_sites['Co2'].fract_x.free = True
struct.atom_sites['Co2'].fract_z.free = True
struct.atom_sites['Si'].fract_x.free = True
struct.atom_sites['Si'].fract_z.free = True
struct.atom_sites['O1'].fract_x.free = True
struct.atom_sites['O1'].fract_z.free = True
struct.atom_sites['O2'].fract_x.free = True
struct.atom_sites['O2'].fract_z.free = True
struct.atom_sites['O3'].fract_x.free = True
struct.atom_sites['O3'].fract_y.free = True
struct.atom_sites['O3'].fract_z.free = True

struct.atom_sites['Co1'].adp_iso.free = True
struct.atom_sites['Co2'].adp_iso.free = True
struct.atom_sites['Si'].adp_iso.free = True
struct.atom_sites['O1'].adp_iso.free = True
struct.atom_sites['O2'].adp_iso.free = True
struct.atom_sites['O3'].adp_iso.free = True

# %%
expt.linked_structures['cosio'].scale.free = True

expt.instrument.calib_twotheta_offset.free = True

expt.peak.broad_gauss_u.free = True
expt.peak.broad_gauss_v.free = True
expt.peak.broad_gauss_w.free = True
expt.peak.broad_lorentz_y.free = True

for point in expt.background:
    point.intensity.free = True

# %% [markdown]
# ### Set Constraints
#
# Set aliases for parameters.

# %%
analysis.aliases.create(
    id='biso_Co1',
    param=struct.atom_sites['Co1'].adp_iso,
)
analysis.aliases.create(
    id='biso_Co2',
    param=struct.atom_sites['Co2'].adp_iso,
)

# %% [markdown]
# Set constraints.

# %%
analysis.constraints.create(expression='biso_Co2 = biso_Co1')

# %% [markdown]
# ### Set Minimizer

# %%
# analysis.minimizer.type = 'bumps (lm)'
# ⛔ TASK-SCOPED PLACEHOLDER — the minimizer and calculator selectors are DEFERRED to a
# later milestone (owner
# ruling 2026-09-22, unfiled at porting time); this placeholder expires when that milestone lands.
print('[PLACEHOLDER] the fitting-backend selector is deferred to a later milestone — skipped')

# %% [markdown]
# ### Run Fitting
#
# This is the fitting of the first dataset to optimize the initial
# parameters for the sequential fitting. This step is optional but can
# help with convergence and speed of the sequential fitting, especially
# if the initial parameters are far from optimal.

# %%
analysis.fit()

# %%
display.fit.results()

# %% [markdown]
# ### Display Correlations

# %%
display.fit.correlations()

# %% [markdown]
# ### Display Pattern

# %%
display.pattern(expt_name='d20')

# %% [markdown]
# ### Display Structure

# %%
project.structure_style.atom_view = 'adp'
project.display.structure(struct_name='cosio')

# %% [markdown]
# ### Run Sequential Fitting
#
# Set output verbosity level to "short" to show only one-line status
# messages during the analysis process.

# %%
project.verbosity = 'short'

# %% [markdown]
#
# Create a persisted extract rule that reads the temperature from each
# data file.


# %%
temperature = 'diffrn.ambient_temperature'

# %%
analysis.sequential_fit_extract.create(
    id='temperature',
    target=temperature,
    pattern=r'^TEMP\s+([0-9.]+)',
    required=True,
)

# %% [markdown]
# Set the sequential fitting parameters.

# %%
analysis.fitting_mode.type = 'sequential'
analysis.sequential_fit.data_dir = scan_data_dir
# ⛔ DEVIATION-ALLOWLIST DELETION — upstream's parallel-worker knob is removed, not placeheld:
# edi executes sequential fits SERIALLY by declared invariant (edi/core/include/edi/model.hpp);
# owner ruling 2026-09-15: "remove, as we don't need it in edi".
analysis.sequential_fit.reverse = True

# %% [markdown]
# Run the sequential fit over all data files in the scan directory.

# %%
analysis.fit()

# %% [markdown]
# ### Replay a Dataset
#
# Apply fitted parameters from the first CSV row and plot the result.

# %%
# project.apply_params_from_csv(row_index=0)
# ⛔ WIP PLACEHOLDER — not yet in edi
print('[WIP] project.apply_params_from_csv is not implemented in edi yet — skipped')
display.pattern(expt_name='d20')

# %% [markdown]
#
# Apply fitted parameters from the last CSV row and plot the result.

# %%
# project.apply_params_from_csv(row_index=-1)
# ⛔ WIP PLACEHOLDER — not yet in edi
print('[WIP] project.apply_params_from_csv is not implemented in edi yet — skipped')
display.pattern(expt_name='d20')

# %% [markdown]
# ### Display Parameter Evolution
#
# Reuse the extracted diffrn path as the x-axis in the following plots.

# %% [markdown]
# Plot fit quality metrics vs. temperature.

# %%
display.fit.series(analysis.fit_result.success, versus=temperature)
display.fit.series(analysis.fit_result.reduced_chi_square, versus=temperature)
display.fit.series(analysis.fit_result.iterations, versus=temperature)

# %% [markdown]
# Plot unit cell parameters vs. temperature.

# %%
display.fit.series(struct.cell.length_a, versus=temperature)
display.fit.series(struct.cell.length_b, versus=temperature)
display.fit.series(struct.cell.length_c, versus=temperature)

# %% [markdown]
# Plot isotropic displacement parameters vs. temperature.

# %%
display.fit.series(struct.atom_sites['Co1'].adp_iso, versus=temperature)
display.fit.series(struct.atom_sites['Si'].adp_iso, versus=temperature)
display.fit.series(struct.atom_sites['O1'].adp_iso, versus=temperature)
display.fit.series(struct.atom_sites['O2'].adp_iso, versus=temperature)
display.fit.series(struct.atom_sites['O3'].adp_iso, versus=temperature)

# %% [markdown]
# Plot selected fractional coordinates vs. temperature.

# %%
display.fit.series(struct.atom_sites['Co2'].fract_x, versus=temperature)
display.fit.series(struct.atom_sites['Co2'].fract_z, versus=temperature)
display.fit.series(struct.atom_sites['O1'].fract_z, versus=temperature)
display.fit.series(struct.atom_sites['O2'].fract_z, versus=temperature)
display.fit.series(struct.atom_sites['O3'].fract_z, versus=temperature)
