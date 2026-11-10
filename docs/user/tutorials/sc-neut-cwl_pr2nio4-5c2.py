"""Single-crystal fit: Pr₂NiO₄, 5C2."""
# %% [markdown]
# # Single-crystal fit: Pr₂NiO₄, 5C2
#
# Fit the layered nickelate Pr₂NiO₄ to constant-wavelength neutron single-crystal data from 5C2 at
# LLB, with anisotropic displacements.
#
# The project is the catalogue case `sc-neut-cwl_pr2nio4-5c2`, the one the command line and the
# app's Examples open.

# %%
import easydiffraction as edi

# %% [markdown]
# ## Load the project

# %%
project_path = edi.download_data('sc-neut-cwl_pr2nio4-5c2', destination='data')
project = edi.Project.load(project_path)
structure = project.structures['pr2nio4']
experiment = project.experiments['llb_5c2']

# %% [markdown]
# The project marks what its fit frees. The fit below frees it in stages, so start with all of it
# fixed.

# %%
for parameter in project.free_parameters:
    parameter.free = False

# %%
project.display.pattern('llb_5c2')

# %% [markdown]
# ## Perform the analysis
#
# A single crystal has no background or profile: the stages are the scale, the positions, the
# interstitial oxygen's displacement, then the displacement tensors.

# %% [markdown]
# ### Scale
#
# The scale brings the calculated intensities to the measured ones.

# %%
experiment.linked_structures['pr2nio4'].scale.free = True

# %%
project.display.parameters.free()

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('llb_5c2')

# %% [markdown]
# ### Positions
#
# The coordinates each site's symmetry leaves free.

# %%
for site in structure.atom_sites:
    for coordinate in (site.fract_x, site.fract_y, site.fract_z):
        coordinate.free = not coordinate.symmetry_constrained

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('llb_5c2')

# %% [markdown]
# ### The interstitial displacement
#
# The isotropic displacement of the interstitial oxygen Od.

# %%
structure.atom_sites['Od'].adp_iso.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('llb_5c2')

# %% [markdown]
# ### Anisotropic displacements
#
# Last, the tensors, each with the components its site symmetry leaves free.

# %%
for tensor in structure.atom_site_aniso:
    for component in (tensor.adp_11, tensor.adp_22, tensor.adp_33, tensor.adp_12, tensor.adp_13, tensor.adp_23):
        component.free = not component.symmetry_constrained

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('llb_5c2')

# %%
project.display.fit.correlations()

# %%
project.display.structure('pr2nio4')

# %% [markdown]
# ## Save the project

# %%
project.save_as('sc-neut-cwl_pr2nio4-5c2')
project.report.save_html('sc-neut-cwl_pr2nio4-5c2.html')
