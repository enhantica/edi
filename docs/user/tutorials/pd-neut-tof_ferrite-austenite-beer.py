"""Joint fit: ferrite and austenite, BEER."""
# %% [markdown]
# # Joint fit: ferrite and austenite, BEER
#
# Calibrate the BEER instrument at ESS with two McStas-simulated banks of a ferrite and austenite
# duplex steel, fitted together: each bank has its own zero and resolution.
#
# The project is the catalogue case `pd-neut-tof_ferrite-austenite-beer`, the one the command line
# and the app's Examples open. Austenite's displacement follows ferrite's, and each phase's scale
# in bank n2 follows bank s2, from the start.

# %%
import easydiffraction as edi

# %% [markdown]
# ## Load the project

# %%
project_path = edi.download_data('pd-neut-tof_ferrite-austenite-beer', destination='data')
project = edi.Project.load(project_path)
ferrite = project.structures['ferrite']
austenite = project.structures['austenite']
bank_s2 = project.experiments['expt_s2']
bank_n2 = project.experiments['expt_n2']
project.display.constraints()

# %% [markdown]
# The project marks what its fit frees. The fit below frees it in stages, so start with all of it
# fixed.

# %%
for parameter in project.free_parameters:
    parameter.free = False

# %%
project.display.pattern('expt_s2')

# %% [markdown]
# ## Perform the analysis
#
# The cells stay fixed: this is a calibration, and the two phases are the standards.

# %% [markdown]
# ### Scales and time-of-flight calibration
#
# Both phases' scales and each bank's DIFC offset put the peaks in place and at the right height.

# %%
bank_s2.linked_structures['ferrite'].scale.free = True
bank_s2.linked_structures['austenite'].scale.free = True
bank_s2.instrument.calib_d_to_tof_offset.free = True
bank_n2.instrument.calib_d_to_tof_offset.free = True

# %%
project.display.parameters.free()

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('expt_s2')

# %%
project.display.pattern('expt_n2')

# %% [markdown]
# ### Background
#
# Each bank's background points; the last, past the end of the data, stays fixed.

# %%
for point in bank_s2.background:
    point.intensity.free = True
for point in bank_n2.background:
    point.intensity.free = True
bank_s2.background[30].intensity.free = False
bank_n2.background[30].intensity.free = False

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('expt_s2')

# %%
project.display.pattern('expt_n2')

# %% [markdown]
# ### Peak widths
#
# Each bank's widths.

# %%
bank_s2.peak.broad_gauss_sigma_0.free = True
bank_s2.peak.broad_gauss_sigma_1.free = True
bank_s2.peak.broad_gauss_sigma_2.free = True
bank_s2.peak.broad_lorentz_gamma_0.free = True
bank_n2.peak.broad_gauss_sigma_0.free = True
bank_n2.peak.broad_gauss_sigma_1.free = True
bank_n2.peak.broad_gauss_sigma_2.free = True
bank_n2.peak.broad_lorentz_gamma_0.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('expt_s2')

# %%
project.display.pattern('expt_n2')

# %% [markdown]
# ### Displacement
#
# Last, ferrite's displacement; austenite's follows it.

# %%
ferrite.atom_sites['Fe'].adp_iso.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('expt_s2')

# %%
project.display.pattern('expt_n2')

# %%
project.display.fit.correlations()

# %%
project.display.structure('ferrite')

# %%
project.display.structure('austenite')

# %% [markdown]
# ## Save the project

# %%
project.save_as('pd-neut-tof_ferrite-austenite-beer')
project.report.save_html('pd-neut-tof_ferrite-austenite-beer.html')
