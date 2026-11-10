"""Rietveld fit: herbertsmithite, HRPT."""
# %% [markdown]
# # Rietveld fit: herbertsmithite, HRPT
#
# Fit herbertsmithite, ZnCu₃(OD)₆Cl₂, a deuterated kagome antiferromagnet, to constant-wavelength
# neutron powder data from HRPT at PSI, with a pseudo-Voigt profile and Bérar-Baldinozzi
# asymmetry.
#
# The project is the catalogue case `pd-neut-cwl_hs-hrpt`, the one the command line and the app's
# Examples open.

# %%
import easydiffraction as edi

# %% [markdown]
# ## Load the project

# %%
project_path = edi.download_data('pd-neut-cwl_hs-hrpt', destination='data')
project = edi.Project.load(project_path)
structure = project.structures['hs']
experiment = project.experiments['hrpt']

# %% [markdown]
# The project marks what its fit frees. The fit below frees it in stages, so start with all of it
# fixed.

# %%
for parameter in project.free_parameters:
    parameter.free = False

# %%
project.display.pattern('hrpt')

# %% [markdown]
# ## Perform the analysis
#
# The fit follows diffraction-lib's four cycles for this case.

# %% [markdown]
# ### Cell, scale and 2θ zero
#
# The cell lengths, the scale and the zero shift put the peaks in place and at the right height.

# %%
structure.cell.length_a.free = True
structure.cell.length_c.free = True
experiment.linked_structures['hs'].scale.free = True
experiment.instrument.calib_twotheta_offset.free = True

# %%
project.display.parameters.free()

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('hrpt')

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
project.display.pattern('hrpt')

# %% [markdown]
# ### Peak widths
#
# The Gaussian widths and the mixing η₀, with the background staying free. diffraction-lib frees
# the Lorentzian Y where this profile has η₀.

# %%
experiment.peak.broad_gauss_u.free = True
experiment.peak.broad_gauss_v.free = True
experiment.peak.broad_gauss_w.free = True
experiment.peak.mixing_eta_0.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('hrpt')

# %% [markdown]
# ### Atom positions
#
# The coordinates the symmetry leaves free: O and H in x and z, Cl in z.

# %%
for site in structure.atom_sites:
    for coordinate in (site.fract_x, site.fract_y, site.fract_z):
        coordinate.free = not coordinate.symmetry_constrained

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('hrpt')

# %% [markdown]
# ### Displacements
#
# Every site's displacement.

# %%
for site in structure.atom_sites:
    site.adp_iso.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('hrpt')

# %% [markdown]
# ### Asymmetry
#
# Last, the four Bérar-Baldinozzi asymmetry terms.

# %%
experiment.peak.asym_beba_a0.free = True
experiment.peak.asym_beba_b0.free = True
experiment.peak.asym_beba_a1.free = True
experiment.peak.asym_beba_b1.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('hrpt')

# %%
project.display.fit.correlations()

# %%
project.display.structure('hs')

# %% [markdown]
# ## Save the project

# %%
project.save_as('pd-neut-cwl_hs-hrpt')
project.report.save_html('pd-neut-cwl_hs-hrpt.html')
