"""Rietveld fit: high-entropy perovskite, P02.1."""
# %% [markdown]
# # Rietveld fit: high-entropy perovskite, P02.1
#
# Fit the high-entropy perovskite La(Ti,Cr,Mn,Fe,Co,Ni,Cu)O₃, seven cations on one site, to
# synchrotron X-ray powder data from P02.1 at PETRA III.
#
# The project is the catalogue case `pd-xray-cwl_lam7o3-p021`, the one the command line and the
# app's Examples open. The seven metals sharing one site have one displacement, held by
# constraints from the start.

# %%
import easydiffraction as edi

# %% [markdown]
# ## Load the project

# %%
project_path = edi.download_data('pd-xray-cwl_lam7o3-p021', destination='data')
project = edi.Project.load(project_path)
structure = project.structures['lam7o3']
experiment = project.experiments['p021']
project.display.constraints()

# %% [markdown]
# The project marks what its fit frees. The fit below frees it in stages, so start with all of it
# fixed.

# %%
for parameter in project.free_parameters:
    parameter.free = False

# %%
project.display.pattern('p021')

# %% [markdown]
# ## Perform the analysis
#
# The fit goes in stages, freeing one group of parameters at a time.

# %% [markdown]
# ### Scale, 2θ zero and cell
#
# The scale, the zero shift and the cell put the peaks in place and at the right height.

# %%
experiment.linked_structures['lam7o3'].scale.free = True
experiment.instrument.calib_twotheta_offset.free = True
structure.cell.length_a.free = True
structure.cell.length_b.free = True
structure.cell.length_c.free = True

# %%
project.display.parameters.free()

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('p021')

# %% [markdown]
# ### Background

# %%
for point in experiment.background:
    point.intensity.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('p021')

# %% [markdown]
# ### Peak widths
#
# The Gaussian widths and the Lorentzian X.

# %%
experiment.peak.broad_gauss_u.free = True
experiment.peak.broad_gauss_v.free = True
experiment.peak.broad_gauss_w.free = True
experiment.peak.broad_lorentz_x.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('p021')

# %% [markdown]
# ### Background from the fitted model
#
# With a fitted peak model, estimate the background again with the calculated peaks subtracted,
# which follows the low-angle background better, then free the new points and fit again.

# %%
experiment.background.auto_estimate(use_model='subtract', n_points=20)
for point in experiment.background:
    point.intensity.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('p021')

# %% [markdown]
# ### Atom positions

# %%
for site in structure.atom_sites:
    for coordinate in (site.fract_x, site.fract_y, site.fract_z):
        coordinate.free = not coordinate.symmetry_constrained

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('p021')

# %% [markdown]
# ### Displacements
#
# La's, the mixed site's (through Ti) and O1's; O2's follows O1's.

# %%
structure.atom_sites['La'].adp_iso.free = True
structure.atom_sites['Ti'].adp_iso.free = True
structure.atom_sites['O1'].adp_iso.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('p021')

# %%
project.display.fit.correlations()

# %%
project.display.structure('lam7o3')

# %% [markdown]
# ## Save the project

# %%
project.save_as('pd-xray-cwl_lam7o3-p021')
project.report.save_html('pd-xray-cwl_lam7o3-p021.html')
