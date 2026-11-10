"""Rietveld fit: Y₂O₃, SPODI."""
# %% [markdown]
# # Rietveld fit: Y₂O₃, SPODI
#
# Fit cubic Y₂O₃ to constant-wavelength neutron powder data from SPODI at FRM II, with anisotropic
# displacement tensors whose components the site symmetry ties together.
#
# The project is the catalogue case `pd-neut-cwl_y2o3-spodi`, the one the command line and the
# app's Examples open.

# %%
import easydiffraction as edi

# %% [markdown]
# ## Load the project

# %%
project_path = edi.download_data('pd-neut-cwl_y2o3-spodi', destination='data')
project = edi.Project.load(project_path)
structure = project.structures['y2o3']
experiment = project.experiments['spodi']

# %% [markdown]
# The project marks what its fit frees. The fit below frees it in stages, so start with all of it
# fixed.

# %%
for parameter in project.free_parameters:
    parameter.free = False

# %% [markdown]
# ## Estimate the background
#
# Start the background from an automatic estimate. The default method, arPLS, fits a smooth curve
# under the pattern that ignores the peaks, and places 21 points along it.

# %%
experiment.background.auto_estimate(n_points=21)

# %%
project.display.pattern('spodi')

# %% [markdown]
# ## Perform the analysis
#
# The fit goes in stages, freeing one group of parameters at a time.

# %% [markdown]
# ### Scale, 2θ zero and cell
#
# The scale, the zero shift and the cell length put the peaks in place and at the right height.

# %%
experiment.linked_structures['y2o3'].scale.free = True
experiment.instrument.calib_twotheta_offset.free = True
structure.cell.length_a.free = True

# %%
project.display.parameters.free()

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('spodi')

# %% [markdown]
# ### Background
#
# The estimated points are a starting point; fit them now that the peaks are in place.

# %%
for point in experiment.background:
    point.intensity.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('spodi')

# %% [markdown]
# ### Peak widths

# %%
experiment.peak.broad_gauss_u.free = True
experiment.peak.broad_gauss_v.free = True
experiment.peak.broad_gauss_w.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('spodi')

# %% [markdown]
# ### Atom positions
#
# Y1's x and O1's three coordinates are the ones the symmetry leaves free.

# %%
for site in structure.atom_sites:
    for coordinate in (site.fract_x, site.fract_y, site.fract_z):
        coordinate.free = not coordinate.symmetry_constrained

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('spodi')

# %% [markdown]
# ### Anisotropic displacements
#
# Last, the displacement tensors, each with only the components its site symmetry leaves free.

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
project.display.pattern('spodi')

# %%
project.display.fit.correlations()

# %%
project.display.structure('y2o3')

# %% [markdown]
# ## Save the project

# %%
project.save_as('pd-neut-cwl_y2o3-spodi')
project.report.save_html('pd-neut-cwl_y2o3-spodi.html')
