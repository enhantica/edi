# %% [markdown]
# # Calculation without data: Si, time of flight
#
# Calculate a time-of-flight neutron pattern of silicon without any measured data. For a
# time-of-flight instrument a time window means nothing without a calibration, so the calculation
# range follows from the instrument's d-to-TOF calibration.
#
# The project is the catalogue case `pd-neut-tof_si_simulation`: the files the command line fits with
# `python -m edi fit docs/user/cli/pd-neut-tof_si_simulation/project` and the app opens from its
# Examples.

# %% [markdown]
# > This tutorial is not run when the documentation is built yet. It loads its project from the edi
# > repository, so it runs once a tutorial runner can provide the project elsewhere
# > (`execution-exclusions.yml`).

# %%
import edi

# %% [markdown]
# ## Load the project

# %%
project = edi.Project.load('../cli/pd-neut-tof_si_simulation/project')
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
project.report.save_html('pd-neut-tof_si_simulation.html')

# %% [markdown]
# ## Save
#
# `save_as` writes the project with its new values to a folder of its own; the catalogue's copy stays
# as it was.

# %%
project.save_as('pd-neut-tof_si_simulation')
