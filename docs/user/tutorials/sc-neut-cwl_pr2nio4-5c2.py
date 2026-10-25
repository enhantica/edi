"""Single-crystal fit: Pr₂NiO₄, 5C2."""
# %% [markdown]
# # Single-crystal fit: Pr₂NiO₄, 5C2
#
# Fit the layered nickelate Pr₂NiO₄ to constant-wavelength neutron single-crystal data from 5C2 at
# LLB, with anisotropic displacements.
#
# The project is the catalogue case `sc-neut-cwl_pr2nio4-5c2`: the files the command line fits with
# `python -m edi fit docs/user/cli/sc-neut-cwl_pr2nio4-5c2/project` and the app opens from its
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
project = edi.Project.load('../cli/sc-neut-cwl_pr2nio4-5c2/project')
print(project.metadata.title)
print('Structures:', ', '.join(structure.name for structure in project.structures))
print('Experiments:', ', '.join(experiment.name for experiment in project.experiments))
print('Fitting mode:', project.fitting_mode)

# %% [markdown]
# ## The start
#
# The project starts from zero: every displacement at 0 (Bani on every site but Od, which is Biso)
# and free, the free coordinates moved off their refined values, no extinction, and the scale to
# one significant figure.
#
# The fit is free to change these parameters:

# %%
for parameter in project.free_parameters:
    print(f'{parameter.name:28} {parameter.value:12.6g} {parameter.units}')

# %% [markdown]
# ## Fit
#
# `analysis.fit()` runs the fit the project declares, here one experiment.

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
project.report.save_html('sc-neut-cwl_pr2nio4-5c2.html')

# %% [markdown]
# ## Save
#
# `save_as` writes the project with its new values to a folder of its own; the catalogue's copy
# stays as it was.

# %%
project.save_as('sc-neut-cwl_pr2nio4-5c2')
