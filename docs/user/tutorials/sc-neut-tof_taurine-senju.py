"""Single-crystal fit: taurine, SENJU."""
# %% [markdown]
# # Single-crystal fit: taurine, SENJU
#
# Fit the amino-sulfonic acid taurine to six time-of-flight neutron single-crystal datasets from
# SENJU at J-PARC together, each reflection measured at its own wavelength.
#
# The project is the catalogue case `sc-neut-tof_taurine-senju`, the one the command line and the
# app's Examples open. Banks 2 to 6 share bank 1's three extinction terms, from the start.

# %%
import easydiffraction as edi

# %% [markdown]
# ## Load the project

# %%
project_path = edi.download_data('sc-neut-tof_taurine-senju', destination='data')
project = edi.Project.load(project_path)
structure = project.structures['taurine']
senju_1 = project.experiments['senju_1']
senju_2 = project.experiments['senju_2']
senju_3 = project.experiments['senju_3']
senju_4 = project.experiments['senju_4']
senju_5 = project.experiments['senju_5']
senju_6 = project.experiments['senju_6']
project.display.constraints()

# %% [markdown]
# The project marks what its fit frees. The fit below frees it in stages, so start with all of it
# fixed.

# %%
for parameter in project.free_parameters:
    parameter.free = False

# %%
project.display.pattern('senju_1')

# %% [markdown]
# ## Perform the analysis
#
# The fit follows diffraction-lib's change of model for this case: isotropic displacements first,
# then anisotropic tensors. diffraction-lib does not fit the positions, which this case does, so
# they get a stage of their own.

# %% [markdown]
# ### Scales, every site isotropic
#
# Each bank's scale, with every site's displacement isotropic for now.

# %%
for site in structure.atom_sites:
    site.adp_type = 'Biso'
for experiment in project.experiments:
    experiment.linked_structures['taurine'].scale.free = True

# %%
project.display.parameters.free()

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('senju_1')

# %% [markdown]
# ### Isotropic displacements
#
# Every site's isotropic displacement.

# %%
for site in structure.atom_sites:
    site.adp_iso.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('senju_1')

# %% [markdown]
# ### Extinction
#
# Bank 1's three extinction terms, which the other banks share.

# %%
senju_1.extinction.coefficient_11.free = True
senju_1.extinction.coefficient_22.free = True
senju_1.extinction.coefficient_33.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('senju_1')

# %% [markdown]
# ### Positions
#
# All fourteen sites' coordinates.

# %%
for site in structure.atom_sites:
    site.fract_x.free = True
    site.fract_y.free = True
    site.fract_z.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('senju_1')

# %% [markdown]
# ### Anisotropic displacements
#
# Back to anisotropic displacements (edi converts the values), with every tensor component free.

# %%
for site in structure.atom_sites:
    site.adp_type = 'beta'
for tensor in structure.atom_site_aniso:
    tensor.adp_11.free = True
    tensor.adp_22.free = True
    tensor.adp_33.free = True
    tensor.adp_12.free = True
    tensor.adp_13.free = True
    tensor.adp_23.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('senju_1')

# %%
project.display.fit.correlations()

# %%
project.display.structure('taurine')

# %% [markdown]
# ## Save the project

# %%
project.save_as('sc-neut-tof_taurine-senju')
project.report.save_html('sc-neut-tof_taurine-senju.html')
