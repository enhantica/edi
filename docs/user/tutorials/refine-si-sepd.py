"""Si/SEPD standard Rietveld fit — a diffraction-lib tutorial port."""
# %% [markdown]
# # Structure Refinement: Si, SEPD
#
# This example demonstrates a Rietveld refinement of Si crystal
# structure using time-of-flight neutron powder diffraction data from
# SEPD at Argonne.
#
# It also shows how to switch calculation engine and peak profile type.

# %% [markdown]
# > ⛔ **Execution-disabled**: this tutorial is committed ahead of the API it
# > exercises and stays out of notebook execution until **tutorial-runner** lands — see
# > `execution-exclusions.yml`, whose list shrinks to empty as unblocking tasks land.

# %% [markdown]
# ## 🛠️ Import Library

# %%
from edi import ExperimentFactory, Project, StructureFactory, download_data

# %% [markdown]
# ## 🧩 Define Structure
#
# This section shows how to add structures and modify their
# parameters.
#
# ### Create Structure

# %%
structure = StructureFactory.from_scratch(name='si')

# %% [markdown]
# ### Set Space Group

# %%
structure.space_group.name_h_m = 'F d -3 m'
structure.space_group.coord_system_code = '2'

# %% [markdown]
# ### Set Unit Cell

# %%
structure.cell.length_a = 5.431

# %% [markdown]
# ### Set Atom Sites

# %%
structure.atom_sites.create(
    id='Si',
    type_symbol='Si',
    fract_x=0.125,
    fract_y=0.125,
    fract_z=0.125,
    adp_iso=0.5,
)

# %% [markdown]
# ## 🔬 Define Experiment
#
# This section shows how to add experiments, configure their
# parameters, and link the structures defined in the previous step.
#
# ### Download Data

# %%
data_path = download_data('meas-si-sepd', destination='data')

# %% [markdown]
# ### Create Experiment

# %%
expt = ExperimentFactory.from_data_path(
    name='sepd',
    data_path=data_path,
    beam_mode='time-of-flight',
)

# %% [markdown]
# ### Set Instrument

# %%
expt.instrument.setup_twotheta_bank = 144.845
expt.instrument.calib_d_to_tof_offset = -10.0
expt.instrument.calib_d_to_tof_linear = 7476.91
expt.instrument.calib_d_to_tof_quadratic = -1.54

# %% [markdown]
# ### Set Peak Profile

# %%
expt.peak.show_supported()

# %%
expt.peak.type = 'jorgensen-von-dreele'

# %%
expt.peak.broad_gauss_sigma_0 = 3.0148
expt.peak.broad_gauss_sigma_1 = 33.3451
expt.peak.broad_gauss_sigma_2 = 0.0
expt.peak.broad_lorentz_gamma_0 = 0.0
expt.peak.broad_lorentz_gamma_1 = 2.5489
expt.peak.broad_lorentz_gamma_2 = 0.0
expt.peak.rise_alpha_0 = 0.0
expt.peak.rise_alpha_1 = 0.5971
expt.peak.decay_beta_0 = 0.0408
expt.peak.decay_beta_1 = 0.0123

# %%
expt.peak.cutoff_fwhm = 8.2

# %% [markdown]
# ### Set Background

# %%
expt.background.auto_estimate()

# %% [markdown]
# ### Set Linked Structures

# %%
expt.linked_structures.create(structure_id='si', scale=600.0)

# %% [markdown]
# ## 📦 Define Project
#
# The project object is used to manage the structure, experiment, and
# analysis.
#
# ### Create Project

# %%
project = Project(name='si_sepd')

# %% [markdown]
# ### Add Structure

# %%
project.structures.add(structure)

# %% [markdown]
# ### Add Experiment

# %%
project.experiments.add(expt)

# %% [markdown]
# ## 🚀 Perform Analysis
#
# This section shows the analysis process, including how to set up
# calculation and fitting engines.
#
# ### Display Structure

# %%
project.display.structure(struct_name='si')

# %% [markdown]
# ### Display Pattern

# %%
project.display.pattern(expt_name='sepd')
project.display.pattern(expt_name='sepd', x_min=23200, x_max=23700)

# %% [markdown]
# ### Perform Fit 1/4
#
# Set parameters to be refined.

# %%
structure.cell.length_a.free = True

expt.linked_structures['si'].scale.free = True
expt.instrument.calib_d_to_tof_offset.free = True

# %% [markdown]
# Show free parameters after selection.

# %%
project.display.parameters.free()

# %% [markdown]
# #### Run Fitting

# %%
# project.analysis.minimizer.type = 'bumps (lm)'
# ⛔ TASK-SCOPED PLACEHOLDER — the minimizer and calculator selectors are DEFERRED to a
# later milestone (owner
# ruling 2026-09-22, unfiled at porting time); this placeholder expires when that milestone lands.
print('[PLACEHOLDER] the fitting-backend selector is deferred to a later milestone — skipped')

# %%
project.analysis.fit()
project.display.fit.results()

# %% [markdown]
# #### Display Pattern

# %%
project.display.pattern(expt_name='sepd')

# %%
project.display.pattern(expt_name='sepd', x_min=23200, x_max=23700)

# %% [markdown]
# ### Perform Fit 2/4
#
# Set more parameters to be refined.

# %%
for point in expt.background:
    point.intensity.free = True

# %% [markdown]
# Show free parameters after selection.

# %%
project.display.parameters.free()

# %% [markdown]
# #### Run Fitting

# %%
project.analysis.fit()
project.display.fit.results()

# %% [markdown]
# #### Display Pattern

# %%
project.display.pattern(expt_name='sepd')

# %%
project.display.pattern(expt_name='sepd', x_min=23200, x_max=23700)

# %% [markdown]
# ### Perform Fit 3/4
#
# Fix background points.

# %%
for point in expt.background:
    point.intensity.free = False

# %% [markdown]
# Set more parameters to be refined.

# %%
expt.peak.broad_gauss_sigma_0.free = True
expt.peak.broad_gauss_sigma_1.free = True
expt.peak.broad_lorentz_gamma_1.free = True

# %% [markdown]
# Show free parameters after selection.

# %%
project.display.parameters.free()

# %% [markdown]
# #### Run Fitting

# %%
project.analysis.fit()
project.display.fit.results()

# %% [markdown]
# #### Display Pattern

# %%
project.display.pattern(expt_name='sepd')

# %%
project.display.pattern(expt_name='sepd', x_min=23200, x_max=23700)

# %% [markdown]
# ### Perform Fit 4/4
#
# Set more parameters to be refined.

# %%
structure.atom_sites['Si'].adp_iso.free = True

expt.peak.decay_beta_0.free = True
expt.peak.decay_beta_1.free = True

# %% [markdown]
# Show free parameters after selection.

# %%
project.display.parameters.free()

# %% [markdown]
# #### Run Fitting

# %%
project.analysis.fit()
project.display.fit.results()

# %% [markdown]
# #### Display Correlations

# %%
# project.display.fit.correlations()
# ⛔ WIP PLACEHOLDER — not yet in edi
print('[WIP] project.display.fit.correlations is not implemented in edi yet — skipped')

# %% [markdown]
# #### Display Pattern

# %%
project.display.pattern(expt_name='sepd')

# %%
project.display.pattern(expt_name='sepd', x_min=23200, x_max=23700)

# %%
project.display.pattern(expt_name='sepd', x='d_spacing')

# %% [markdown]
# ## 💾 Save Project

# %%
project.save_as(dir_path='projects/refine-si-sepd')
