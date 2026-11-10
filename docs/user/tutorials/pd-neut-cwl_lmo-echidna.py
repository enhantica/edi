"""Rietveld fit: LiNiO₂, ECHIDNA."""
# %% [markdown]
# # Rietveld fit: LiNiO₂, ECHIDNA
#
# Fit the layered oxide LiNiO₂ to constant-wavelength neutron powder data from ECHIDNA at ANSTO.
# Li and Ni mix between two sites, held to full occupancy by constraints, and the profile has
# Finger-Cox-Jephcoat asymmetry.
#
# The project is the catalogue case `pd-neut-cwl_lmo-echidna`, the one the command line and the
# app's Examples open. Li and Ni share their sites through five relations (displacements and
# occupancies), kept from the start.

# %%
import easydiffraction as edi

# %% [markdown]
# ## Load the project

# %%
project_path = edi.download_data('pd-neut-cwl_lmo-echidna', destination='data')
project = edi.Project.load(project_path)
structure = project.structures['lmo']
experiment = project.experiments['echidna']
project.display.constraints()

# %% [markdown]
# The project marks what its fit frees. The fit below frees it in stages, so start with all of it
# fixed.

# %%
for parameter in project.free_parameters:
    parameter.free = False

# %%
project.display.pattern('echidna')

# %% [markdown]
# ## Perform the analysis
#
# The fit goes in stages, freeing one group of parameters at a time.

# %% [markdown]
# ### Scale, 2θ zero and cell
#
# The scale, the zero shift and the two cell lengths put the peaks in place and at the right
# height.

# %%
experiment.linked_structures['lmo'].scale.free = True
experiment.instrument.calib_twotheta_offset.free = True
structure.cell.length_a.free = True
structure.cell.length_c.free = True

# %%
project.display.parameters.free()

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('echidna')

# %% [markdown]
# ### Sample displacement and transparency
#
# The sample sits a little off the diffractometer axis and the beam goes into it; both shift the
# peaks with angle, unlike the zero.

# %%
experiment.instrument.calib_sample_displacement.free = True
experiment.instrument.calib_sample_transparency.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('echidna')

# %% [markdown]
# ### Background
#
# The nine background points follow the level between the peaks.

# %%
for point in experiment.background:
    point.intensity.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('echidna')

# %% [markdown]
# ### Peak widths

# %%
experiment.peak.broad_gauss_u.free = True
experiment.peak.broad_gauss_v.free = True
experiment.peak.broad_gauss_w.free = True
experiment.peak.broad_lorentz_y.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('echidna')

# %% [markdown]
# ### Oxygen position
#
# O's height along c is the only coordinate the symmetry leaves free.

# %%
structure.atom_sites['O'].fract_z.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('echidna')

# %% [markdown]
# ### Displacements
#
# Li1's, Ni2's and O's; Ni1 and Li2 follow by the relations.

# %%
structure.atom_sites['Li1'].adp_iso.free = True
structure.atom_sites['Ni2'].adp_iso.free = True
structure.atom_sites['O'].adp_iso.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('echidna')

# %% [markdown]
# ### Li/Ni mixing
#
# Last, Li1's occupancy, which sets how much Ni sits on the Li site; it moves with the
# displacements, so it comes after them.

# %%
structure.atom_sites['Li1'].occupancy.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('echidna')

# %%
project.display.fit.correlations()

# %%
project.display.structure('lmo')

# %% [markdown]
# ## Save the project

# %%
project.save_as('pd-neut-cwl_lmo-echidna')
project.report.save_html('pd-neut-cwl_lmo-echidna.html')
