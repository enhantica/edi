"""Calculation without data: NaCl, laboratory X-ray."""
# %% [markdown]
# # Calculation without data: NaCl, laboratory X-ray
#
# Calculate a laboratory X-ray pattern of rock salt with Cu K&alpha;₁ radiation and a
# monochromator's polarization correction, without any measured data.
#
# The project is the catalogue case `pd-xray-cwl_nacl_simulation`: the files the command line fits
# with `python -m edi fit docs/user/cli/pd-xray-cwl_nacl_simulation/project` and the app opens from
# its Examples.

# %% [markdown]
# > This tutorial is not run when the documentation is built yet. It loads its project from the edi
# > repository, so it runs once a tutorial runner can provide the project elsewhere
# > (`execution-exclusions.yml`).

# %%
import edi

# %% [markdown]
# ## Load the project

# %%
project = edi.Project.load('../cli/pd-xray-cwl_nacl_simulation/project')
print(project.metadata.title)
print('Structures:', ', '.join(structure.name for structure in project.structures))
print('Experiments:', ', '.join(experiment.name for experiment in project.experiments))
print('Fitting mode:', project.fitting_mode)

# %% [markdown]
# ## Calculate
#
# There is nothing to fit: edi calculates the pattern from the model as it is.

# %%
project.calculate()
pattern = project.experiments[0].data
print(len(pattern.intensity_calc), 'points, highest', round(max(pattern.intensity_calc), 1))

# %% [markdown]
# ## Patterns and report
#
# The HTML report draws the measured, calculated and difference patterns with the reflection
# positions, and lists the structure and the fit. Open it in a browser.

# %%
project.report.save_html('pd-xray-cwl_nacl_simulation.html')

# %% [markdown]
# ## Save
#
# `save_as` writes the project with its new values to a folder of its own; the catalogue's copy
# stays as it was.

# %%
project.save_as('pd-xray-cwl_nacl_simulation')
