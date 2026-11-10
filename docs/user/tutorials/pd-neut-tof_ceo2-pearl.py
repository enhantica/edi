"""Calibration fit: CeO₂, PEARL."""
# %% [markdown]
# # Calibration fit: CeO₂, PEARL
#
# Fit the CeO₂ standard to time-of-flight neutron powder data from PEARL at ISIS: the calibration
# and the profile, with a polynomial background.
#
# The project is the catalogue case `pd-neut-tof_ceo2-pearl`, the one the command line and the
# app's Examples open.

# %%
import easydiffraction as edi

# %% [markdown]
# ## Load the project

# %%
project_path = edi.download_data('pd-neut-tof_ceo2-pearl', destination='data')
project = edi.Project.load(project_path)
structure = project.structures['ceo2']
experiment = project.experiments['pearl']

# %% [markdown]
# The project marks what its fit frees. The fit below frees it in stages, so start with all of it
# fixed.

# %%
for parameter in project.free_parameters:
    parameter.free = False

# %%
project.display.pattern('pearl')

# %% [markdown]
# ## Perform the analysis
#
# The fit goes in stages, freeing one group of parameters at a time.

# %% [markdown]
# ### Scale and time-of-flight calibration
#
# CeO₂ is the calibration standard, so its cell stays fixed and the DIFC terms put the peaks in
# place.

# %%
experiment.linked_structures['ceo2'].scale.free = True
experiment.instrument.calib_d_to_tof_offset.free = True
experiment.instrument.calib_d_to_tof_linear.free = True
experiment.instrument.calib_d_to_tof_quadratic.free = True

# %%
project.display.parameters.free()

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('pearl')

# %% [markdown]
# ### Background
#
# The six polynomial terms follow the level between the peaks.

# %%
for term in experiment.background_terms:
    term.coef.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('pearl')

# %% [markdown]
# ### Gaussian widths
#
# The Gaussian terms that grow with d spacing.

# %%
experiment.peak.broad_gauss_sigma_1.free = True
experiment.peak.broad_gauss_sigma_2.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('pearl')

# %% [markdown]
# ### Lorentzian width
#
# The Lorentzian term that grows with d spacing.

# %%
experiment.peak.broad_lorentz_gamma_1.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('pearl')

# %% [markdown]
# ### Rise and decay
#
# The back-to-back exponentials that shape each time-of-flight peak.

# %%
experiment.peak.rise_alpha_1.free = True
experiment.peak.decay_beta_0.free = True
experiment.peak.decay_beta_1.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('pearl')

# %% [markdown]
# ### Displacements

# %%
structure.atom_sites['Ce'].adp_iso.free = True
structure.atom_sites['O'].adp_iso.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('pearl')

# %% [markdown]
# ### Absorption
#
# Absorption weakens the intensities with time of flight, as the displacements do, so it comes
# after them, on its own.

# %%
experiment.absorption.abscor1.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('pearl')

# %%
project.display.fit.correlations()

# %%
project.display.structure('ceo2')

# %% [markdown]
# ## Save the project

# %%
project.save_as('pd-neut-tof_ceo2-pearl')
project.report.save_html('pd-neut-tof_ceo2-pearl.html')
