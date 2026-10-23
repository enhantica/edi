"""Joint fit: Na₂Ca₃Al₂F₁₄, WISH."""
# %% [markdown]
# # Joint fit: Na₂Ca₃Al₂F₁₄, WISH
#
# Fit Na₂Ca₃Al₂F₁₄ to time-of-flight neutron powder data from WISH at ISIS, all five detector bank
# pairs at once. Each bank has its own calibration and profile; the structure is shared.
#
# The project is the catalogue case `pd-neut-tof_ncaf-wish`: the files the command line fits with
# `python -m edi fit docs/user/cli/pd-neut-tof_ncaf-wish/project` and the app opens from its
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
project = edi.Project.load('../cli/pd-neut-tof_ncaf-wish/project')
print(project.metadata.title)
print('Structures:', ', '.join(structure.name for structure in project.structures))
print('Experiments:', ', '.join(experiment.name for experiment in project.experiments))
print('Fitting mode:', project.fitting_mode)

# %% [markdown]
# ## The start
#
# The project starts the way your own measurement would: zero shift 0, profile terms to one
# significant figure, Biso 0.5 on every site, coordinates to two decimals, a flat background and
# the scale to one significant figure. The peaks start about 30 % narrower than they fit, with the
# shape moved towards Gaussian.
#
# The fit is free to change these parameters:

# %%
for parameter in project.free_parameters:
    print(f'{parameter.name:28} {parameter.value:12.6g} {parameter.units}')

# %% [markdown]
# ## Fit
#
# `analysis.fit()` runs the fit the project declares, here every experiment at once, sharing the
# structure.

# %%
result = project.analysis.fit()
print(f'{result.status.name.lower()} after {result.iterations} iterations')
print(f'reduced chi-square {result.reduced_chi_square:.3f}, Rwp {100 * result.rwp:.2f} %')
for bank in result.banks:
    print(f'  {bank.name}: Rwp {100 * bank.rwp:.2f} %')

# %% [markdown]
# ## Fitted values

# %%
for label, value in result.values.items():
    print(f'{label:52} {value:12.6g} ± {result.uncertainty.get(label, 0):.2g}')

# %% [markdown]
# ## Patterns and report
#
# The HTML report draws the measured, calculated and difference patterns with the reflection
# positions, and lists the structure and the fit. Open it in a browser.

# %%
project.report.save_html('pd-neut-tof_ncaf-wish.html')

# %% [markdown]
# ## Save
#
# `save_as` writes the project with its new values to a folder of its own; the catalogue's copy
# stays as it was.

# %%
project.save_as('pd-neut-tof_ncaf-wish')
