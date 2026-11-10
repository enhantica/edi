"""Single-crystal fit: Tb₂Ti₂O₇, HEiDi."""
# %% [markdown]
# # Single-crystal fit: Tb₂Ti₂O₇, HEiDi
#
# Fit the pyrochlore Tb₂Ti₂O₇ to constant-wavelength neutron single-crystal data from HEiDi at
# MLZ, with anisotropic displacements and Becker-Coppens extinction.
#
# The project is the catalogue case `sc-neut-cwl_tb2ti2o7-heidi`, the one the command line and the
# app's Examples open.

# %%
import easydiffraction as edi

# %% [markdown]
# ## Load the project

# %%
project_path = edi.download_data('sc-neut-cwl_tb2ti2o7-heidi', destination='data')
project = edi.Project.load(project_path)
structure = project.structures['tb2ti2o7']
experiment = project.experiments['heidi']

# %% [markdown]
# The project marks what its fit frees. The fit below frees it in stages, so start with all of it
# fixed.

# %%
for parameter in project.free_parameters:
    parameter.free = False

# %%
project.display.pattern('heidi')

# %% [markdown]
# ## Perform the analysis
#
# One new group per fit: the scale, O1's position, the displacement tensors, then the extinction.
# diffraction-lib also fits occupancies and isotropic displacements, which this case keeps fixed.

# %% [markdown]
# ### Scale
#
# The scale brings the calculated intensities to the measured ones.

# %%
experiment.linked_structures['tb2ti2o7'].scale.free = True

# %%
project.display.parameters.free()

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('heidi')

# %% [markdown]
# ### O1's position
#
# The one coordinate the symmetry leaves free.

# %%
structure.atom_sites['O1'].fract_x.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('heidi')

# %% [markdown]
# ### Anisotropic displacements

# %%
for tensor in structure.atom_site_aniso:
    for component in (
        tensor.adp_11,
        tensor.adp_22,
        tensor.adp_33,
        tensor.adp_12,
        tensor.adp_13,
        tensor.adp_23,
    ):
        component.free = not component.symmetry_constrained

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('heidi')

# %% [markdown]
# ### Extinction
#
# The domain radius and the mosaic spread.

# %%
experiment.extinction.domain_radius.free = True
experiment.extinction.mosaic_spread.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('heidi')

# %%
project.display.fit.correlations()

# %%
project.display.structure('tb2ti2o7')

# %% [markdown]
# ## Save the project

# %%
project.save_as('sc-neut-cwl_tb2ti2o7-heidi')
project.report.save_html('sc-neut-cwl_tb2ti2o7-heidi.html')
