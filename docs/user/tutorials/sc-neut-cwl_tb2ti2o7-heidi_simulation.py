"""Calculation without data: Tb₂Ti₂O₇, HEiDi."""
# %% [markdown]
# # Calculation without data: Tb₂Ti₂O₇, HEiDi
#
# Calculate the single-crystal neutron reflections of the pyrochlore Tb₂Ti₂O₇ on HEiDi at MLZ
# without any measured data. The structure, the wavelength and the extinction are in the project,
# and edi calculates every reflection up to the project's sin θ/λ limit.
#
# The project is the catalogue case `sc-neut-cwl_tb2ti2o7-heidi_simulation`: the files the command
# line calculates with
# `python -m edi calc docs/user/cli/sc-neut-cwl_tb2ti2o7-heidi_simulation/project` and the app
# opens from its Examples.

# %%
import easydiffraction as edi

# %% [markdown]
# ## Load the project

# %%
project_path = edi.download_data('sc-neut-cwl_tb2ti2o7-heidi_simulation', destination='data')
project = edi.Project.load(project_path)
print(project.metadata.title)
print('Structures:', ', '.join(structure.name for structure in project.structures))
print('Experiments:', ', '.join(experiment.name for experiment in project.experiments))

# %% [markdown]
# ## Calculate
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
# ## Save
#
# `save_as` writes the project to a folder of its own; the catalogue's copy stays as it was.

# %%
project.save_as('sc-neut-cwl_tb2ti2o7-heidi_simulation')
