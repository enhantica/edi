"""Calculation without data: Tb₂Ti₂O₇, HEiDi."""
# %% [markdown]
# # Calculation without data: Tb₂Ti₂O₇, HEiDi
#
# Calculate the single-crystal neutron reflections of the pyrochlore Tb₂Ti₂O₇ on HEiDi at MLZ
# without any measured data. The structure, the wavelength and the extinction are in the project,
# and edi calculates every reflection up to the project's sin θ/λ limit.
#
# It builds the catalogue case `sc-neut-cwl_tb2ti2o7-heidi_simulation` step by step: the same
# project the command line calculates and the app's Examples open.

# %% [markdown]
# ## Import the library

# %%
import easydiffraction as edi

# %% [markdown]
# ## Define the project
#
# A new project is empty: it holds no structure and no experiment until you add them.

# %%
project = edi.Project(name='tb2ti2o7-heidi_simulation')

# %% [markdown]
# ## Define the structure
#
# Load the structure from EasyDiffraction's collection. Its CIF gives the space group, the cell and
# the atom sites.

# %%
path = edi.download_data('sc-neut-cwl_tb2ti2o7-heidi_simulation-tb2ti2o7', destination='data')
project.structures.add_from_cif_path(path)
structure = project.structures['tb2ti2o7']

# %%
project.display.structure('tb2ti2o7')

# %% [markdown]
# ## Define the experiment
#
# Create the experiment, then describe the instrument, the peak profile, the range to calculate and
# the structure it links. It has no measured data; the calculation gives the pattern.

# %%
project.experiments.create(
    name='heidi',
    sample_form='single crystal',
    beam_mode='constant wavelength',
    radiation_probe='neutron',
    scattering_type='bragg',
)
experiment = project.experiments['heidi']
experiment.neutron_scattering_length = 'sears1992'
experiment.extinction.type = 'becker-coppens-mixed'
experiment.instrument.name = 'HEiDi'
experiment.instrument.facility = 'MLZ (FRM II)'
experiment.instrument.setup_wavelength = 0.793
experiment.extinction.domain_radius = 25
experiment.extinction.crystal_radius = 3
experiment.data_range.sin_theta_over_lambda_max = 0.95
experiment.linked_structures.create(structure_id='tb2ti2o7', scale=4)

# %% [markdown]
# ## Perform the calculation
#
# There is nothing to fit: edi calculates the reflections from the model as it is.

# %%
project.calculate()

# %%
project.display.pattern('heidi')

# %%
project.display.structure('tb2ti2o7')

# %% [markdown]
# ## Report
#
# The HTML report lists the structure, the experiment and the calculated reflections. Open it in
# a browser.

# %%
project.report.save_html('sc-neut-cwl_tb2ti2o7-heidi_simulation.html')

# %% [markdown]
# ## Save the project
#
# `save_as` writes the project to a folder of its own.

# %%
project.save_as('sc-neut-cwl_tb2ti2o7-heidi_simulation')
