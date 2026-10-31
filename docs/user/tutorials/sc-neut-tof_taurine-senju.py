"""Single-crystal fit: taurine, SENJU."""
# %% [markdown]
# # Single-crystal fit: taurine, SENJU
#
# Fit the amino-sulfonic acid taurine to six time-of-flight neutron single-crystal datasets from
# SENJU at J-PARC together, each reflection measured at its own wavelength.
#
# The project is the catalogue case `sc-neut-tof_taurine-senju`: the files the command line fits
# with `python -m edi fit docs/user/cli/sc-neut-tof_taurine-senju/project` and the app opens from
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
project = edi.Project.load('../cli/sc-neut-tof_taurine-senju/project')
print(project.metadata.title)
print('Structures:', ', '.join(structure.name for structure in project.structures))
print('Experiments:', ', '.join(experiment.name for experiment in project.experiments))
print('Fitting mode:', project.fitting_mode)

# %% [markdown]
# ## The start
#
# The project starts away from FullProf's fit: every beta tensor 0, four coordinates moved by
# 0.005, FullProf's scales and the anisotropic Larson extinction 0, every one free.
#
# The fit is free to change these parameters:

# %%
for parameter in project.free_parameters:
    print(f'{parameter.name:28} {parameter.value:12.6g} {parameter.units}')

# %% [markdown]
# ## Fit
#
# `analysis.fit()` runs the fit the project declares, here six experiments together, one per SENJU
# dataset.

# %%
result = project.analysis.fit()
print(f'{result.status.name.lower()} after {result.iterations} iterations')
print(f'reduced chi-square {result.reduced_chi_square:.3f}')

# %% [markdown]
# ## Fitted values

# %%
for label, value in result.values.items():
    print(f'{label:52} {value:12.6g} ± {result.uncertainty.get(label, 0):.2g}')

# %% [markdown]
# ## Report
#
# The HTML report lists the structure, the measured and calculated intensities and the fit. Open it
# in a browser.

# %%
project.report.save_html('sc-neut-tof_taurine-senju.html')

# %% [markdown]
# ## Save
#
# `save_as` writes the project with its new values to a folder of its own; the catalogue's copy
# stays as it was.

# %%
project.save_as('sc-neut-tof_taurine-senju')
