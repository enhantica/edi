"""Rietveld fit: PbSO₄, laboratory X-ray."""
# %% [markdown]
# # Rietveld fit: PbSO₄, laboratory X-ray
#
# Fit PbSO₄ to the Rietveld round robin's laboratory X-ray pattern, with the Cu K&alpha; doublet
# and Bérar-Baldinozzi asymmetry.
#
# The project is the catalogue case `pd-xray-cwl_pbso4-lab`, the one the command line and the
# app's Examples open.

# %%
import easydiffraction as edi

# %% [markdown]
# ## Load the project

# %%
project_path = edi.download_data('pd-xray-cwl_pbso4-lab', destination='data')
project = edi.Project.load(project_path)
structure = project.structures['pbso4']
lab = project.experiments['lab']

# %% [markdown]
# The project marks what its fit frees. The fit below frees it in stages, so start with all of it
# fixed.

# %%
for parameter in project.free_parameters:
    parameter.free = False

# %%
project.display.pattern('lab')

# %% [markdown]
# ## Perform the analysis
#
# The fit goes in stages, freeing one group of parameters at a time.

# %% [markdown]
# ### Scale and 2θ zero
#
# The 2θ zero first: freed together with the cell from the start, the two pull against each
# other and the fit cannot take a step.

# %%
lab.linked_structures['pbso4'].scale.free = True
lab.instrument.calib_twotheta_offset.free = True

# %%
project.display.parameters.free()

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('lab')

# %% [markdown]
# ### Cell

# %%
structure.cell.length_a.free = True
structure.cell.length_b.free = True
structure.cell.length_c.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('lab')

# %% [markdown]
# ### Background
#
# The six Chebyshev terms.

# %%
for term in lab.background_terms:
    term.coef.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('lab')

# %% [markdown]
# ### Peak widths

# %%
lab.peak.broad_gauss_u.free = True
lab.peak.broad_gauss_v.free = True
lab.peak.broad_gauss_w.free = True
lab.peak.mixing_eta_0.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('lab')

# %% [markdown]
# ### Peak asymmetry

# %%
lab.peak.asym_beba_a0.free = True
lab.peak.asym_beba_b0.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('lab')

# %% [markdown]
# ### Lead and sulphur positions
#
# X-rays see the heavy atoms first, so their coordinates come before the oxygens'.

# %%
for site in structure.atom_sites:
    if site.type_symbol != 'O':
        for coordinate in (site.fract_x, site.fract_y, site.fract_z):
            coordinate.free = not coordinate.symmetry_constrained

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('lab')

# %% [markdown]
# ### Oxygen positions

# %%
for site in structure.atom_sites:
    if site.type_symbol == 'O':
        for coordinate in (site.fract_x, site.fract_y, site.fract_z):
            coordinate.free = not coordinate.symmetry_constrained

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('lab')

# %% [markdown]
# ### Displacements
#
# The correlations after this stage show how far the oxygen displacements can be told apart; the
# case keeps them separate.

# %%
for site in structure.atom_sites:
    site.adp_iso.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('lab')

# %%
project.display.fit.correlations()

# %%
project.display.structure('pbso4')

# %% [markdown]
# ## Save the project

# %%
project.save_as('pd-xray-cwl_pbso4-lab')
project.report.save_html('pd-xray-cwl_pbso4-lab.html')
