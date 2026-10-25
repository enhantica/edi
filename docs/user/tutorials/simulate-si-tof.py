"""Si time-of-flight pattern simulation — a diffraction-lib tutorial port."""
# %% [markdown]
# # Calculation Without Data: Si, TOF
#
# This example shows how to **calculate and plot a time-of-flight
# diffraction pattern without any measured data**. As with the
# constant-wavelength example, the structure, instrument, peak profile,
# and background are defined in code, and the pattern is computed over a
# calculation range.
#
# For a time-of-flight instrument an absolute time window is meaningless
# without a calibration, so the default `data_range` is derived from the
# instrument's TOF calibration. No data file is downloaded or loaded.
#
# For this example, a time-of-flight neutron powder experiment for Si is
# used.

# %% [markdown]
# > ⛔ **Execution-disabled**: this tutorial is committed ahead of the API it
# > exercises and stays out of notebook execution until **tutorial-runner** lands — see
# > `execution-exclusions.yml`, whose list shrinks to empty as unblocking tasks land.
# > Upstream's minimizer/calculator selector switches are deferred to a later milestone
# >.

# %% [markdown]
# ## 🛠️ Import Library

# %%
import edi

# %% [markdown]
# ## 📦 Define Project

# %%
project = edi.Project(name='si_simulation')

# %% [markdown]
# ## 🧩 Define Structure

# %%
project.structures.create(name='si')

# %%
structure = project.structures['si']

# %%
structure.space_group.name_h_m = 'F d -3 m'
structure.space_group.coord_system_code = '2'

# %%
structure.cell.length_a = 5.431

# %%
structure.atom_sites.create(
    id='Si',
    type_symbol='Si',
    fract_x=0.125,
    fract_y=0.125,
    fract_z=0.125,
    adp_iso=0.5,
)

# %%
project.display.structure(struct_name='si')

# %% [markdown]
# ## 🔬 Define Experiment
#
# ### Create Experiment Without Data

# %%
project.experiments.create(
    name='sim',
    sample_form='powder',
    beam_mode='time-of-flight',
    radiation_probe='neutron',
)

# %%
experiment = project.experiments['sim']

# %% [markdown]
# ### Set Instrument
#
# The TOF calibration (offset, linear, and quadratic d-to-TOF terms) is
# what converts the default d-spacing window into a time window.

# %%
experiment.instrument.setup_twotheta_bank = 144.845
experiment.instrument.calib_d_to_tof_offset = 0.0
experiment.instrument.calib_d_to_tof_linear = 7476.91
experiment.instrument.calib_d_to_tof_quadratic = -1.54

# %% [markdown]
# ### Set Peak Profile

# %%
experiment.peak.broad_gauss_sigma_0 = 3.0
experiment.peak.broad_gauss_sigma_1 = 40.0
experiment.peak.broad_gauss_sigma_2 = 2.0
experiment.peak.decay_beta_0 = 0.04221
experiment.peak.decay_beta_1 = 0.00946
experiment.peak.rise_alpha_0 = 0.0
experiment.peak.rise_alpha_1 = 0.5971

# %% [markdown]
# ### Set Background

# %%
experiment.background.type = 'line-segment'
experiment.background.create(id='1', position=10000, intensity=500)
experiment.background.create(id='2', position=40000, intensity=500)

# %% [markdown]
# ### Set Calculation Range

# %%
experiment.data_range.time_of_flight_min = 5000.0
experiment.data_range.time_of_flight_max = 15000.0
experiment.data_range.time_of_flight_inc = 2.0

# %% [markdown]
# ### Set Linked Structures

# %%
experiment.linked_structures.create(structure_id='si', scale=10.0)

# %% [markdown]
# ## 🚀 Perform Calculation
#
# ### Display Pattern

# %%
project.display.pattern(expt_name='sim')

# %%
project.display.pattern(expt_name='sim', x_min=5000, x_max=6000)

# %% [markdown]
# ### Inspect as Text

# %%
project.experiments['sim'].show_as_text()

# %% [markdown]
# ## 💾 Save Project

# %%
project.save_as(dir_path='projects/simulate-si-tof')
