"""Rietveld fit: CeCoAl₃, POLARIS."""
# %% [markdown]
# # Rietveld fit: CeCoAl₃, POLARIS
#
# Fit CeCoAl₃ to time-of-flight neutron powder data from POLARIS at ISIS: structure and profile,
# with a 24-term Chebyshev background.
#
# The project is the catalogue case `pd-neut-tof_cecoal-polaris`, the one the command line and the
# app's Examples open.

# %%
import easydiffraction as edi

# %% [markdown]
# ## Load the project

# %%
project_path = edi.download_data('pd-neut-tof_cecoal-polaris', destination='data')
project = edi.Project.load(project_path)
structure = project.structures['cecoal']
experiment = project.experiments['polaris']

# %% [markdown]
# The project marks what its fit frees. The fit below frees it in stages, so start with all of it
# fixed.

# %%
for parameter in project.free_parameters:
    parameter.free = False

# %%
project.display.pattern('polaris')

# %% [markdown]
# ## Perform the analysis
#
# The fit goes in stages, freeing one group of parameters at a time.

# %% [markdown]
# ### Scale, time-of-flight calibration and cell
#
# The scale, the DIFC offset and its quadratic term, and the three cell lengths put the peaks in
# place and at the right height.

# %%
experiment.linked_structures['cecoal'].scale.free = True
experiment.instrument.calib_d_to_tof_offset.free = True
experiment.instrument.calib_d_to_tof_quadratic.free = True
structure.cell.length_a.free = True
structure.cell.length_b.free = True
structure.cell.length_c.free = True

# %%
project.display.parameters.free()

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('polaris')

# %% [markdown]
# ### Background
#
# The first twelve polynomial terms (orders 0 to 11) follow the level between the peaks; the
# higher ones stay at zero.

# %%
for term in list(experiment.background_terms)[:12]:
    term.coef.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('polaris')

# %% [markdown]
# ### Peak widths

# %%
experiment.peak.broad_gauss_sigma_1.free = True
experiment.peak.broad_lorentz_gamma_1.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('polaris')

# %% [markdown]
# ### Atom positions
#
# The coordinates the symmetry leaves free.

# %%
for site in structure.atom_sites:
    for coordinate in (site.fract_x, site.fract_y, site.fract_z):
        coordinate.free = not coordinate.symmetry_constrained

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('polaris')

# %% [markdown]
# ### Displacements

# %%
for site in structure.atom_sites:
    site.adp_iso.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('polaris')

# %% [markdown]
# ### Absorption
#
# Absorption weakens the intensities with time of flight, as the displacements do with angle, so
# it comes after them, on its own.

# %%
experiment.absorption.abscor1.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('polaris')

# %% [markdown]
# ### Al3 occupancy
#
# Last, Al3's occupancy, which moves with its displacement.

# %%
structure.atom_sites['Al3'].occupancy.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('polaris')

# %%
project.display.fit.correlations()

# %%
project.display.structure('cecoal')

# %% [markdown]
# ## Save the project

# %%
project.save_as('pd-neut-tof_cecoal-polaris')
project.report.save_html('pd-neut-tof_cecoal-polaris.html')
