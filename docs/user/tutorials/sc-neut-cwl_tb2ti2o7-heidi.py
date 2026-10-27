"""Single-crystal fit: Tb₂Ti₂O₇, HEiDi."""
# %% [markdown]
# # Single-crystal fit: Tb₂Ti₂O₇, HEiDi
#
# Fit the pyrochlore Tb₂Ti₂O₇ to constant-wavelength neutron single-crystal data from HEiDi at MLZ,
# with anisotropic displacements and Becker-Coppens extinction.
#
# The project is the catalogue case `sc-neut-cwl_tb2ti2o7-heidi`: the files the command line fits
# with `python -m edi fit docs/user/cli/sc-neut-cwl_tb2ti2o7-heidi/project` and the app opens from
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
project = edi.Project.load('../cli/sc-neut-cwl_tb2ti2o7-heidi/project')
print(project.metadata.title)
print('Structures:', ', '.join(structure.name for structure in project.structures))
print('Experiments:', ', '.join(experiment.name for experiment in project.experiments))
print('Fitting mode:', project.fitting_mode)

# %% [markdown]
# ## The start
#
# The project starts from rough values: anisotropic displacements at a small isotropic-equivalent
# value, the free O1 x moved off its refined value, mixed Becker-Coppens extinction with a crystal
# radius of 3 mm and the domain radius (from 25 μm) and mosaic spread (from 0) free, and the scale
# to one significant figure.
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
project.report.save_html('sc-neut-cwl_tb2ti2o7-heidi.html')

# %% [markdown]
# ## Save
#
# `save_as` writes the project with its new values to a folder of its own; the catalogue's copy
# stays as it was.

# %%
project.save_as('sc-neut-cwl_tb2ti2o7-heidi')
