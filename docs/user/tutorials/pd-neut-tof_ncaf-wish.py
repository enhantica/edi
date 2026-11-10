"""Joint fit: Na₂Ca₃Al₂F₁₄, WISH."""
# %% [markdown]
# # Joint fit: Na₂Ca₃Al₂F₁₄, WISH
#
# Fit Na₂Ca₃Al₂F₁₄ to time-of-flight neutron powder data from WISH at ISIS, all five detector bank
# pairs at once. Each bank has its own calibration and profile; the structure is shared.
#
# The project is the catalogue case `pd-neut-tof_ncaf-wish`, the one the command line and the
# app's Examples open.

# %%
import easydiffraction as edi

# %% [markdown]
# ## Load the project

# %%
project_path = edi.download_data('pd-neut-tof_ncaf-wish', destination='data')
project = edi.Project.load(project_path)
structure = project.structures['ncaf']
wish_1_10 = project.experiments['wish_1_10']
wish_2_9 = project.experiments['wish_2_9']
wish_3_8 = project.experiments['wish_3_8']
wish_4_7 = project.experiments['wish_4_7']
wish_5_6 = project.experiments['wish_5_6']

# %% [markdown]
# The project marks what its fit frees. The fit below frees it in stages, so start with all of it
# fixed.

# %%
for parameter in project.free_parameters:
    parameter.free = False

# %%
project.display.pattern('wish_1_10')

# %% [markdown]
# ## Perform the analysis
#
# Five banks fit together. diffraction-lib's tutorial of this case fits two banks at once with
# everything free; this one has five, so it stages them.

# %% [markdown]
# ### Scales and time-of-flight calibration
#
# Each bank's scale and DIFC offset and linear term put its peaks in place and at the right
# height.

# %%
wish_1_10.linked_structures['ncaf'].scale.free = True
wish_1_10.instrument.calib_d_to_tof_offset.free = True
wish_1_10.instrument.calib_d_to_tof_linear.free = True
wish_2_9.linked_structures['ncaf'].scale.free = True
wish_2_9.instrument.calib_d_to_tof_offset.free = True
wish_2_9.instrument.calib_d_to_tof_linear.free = True
wish_3_8.linked_structures['ncaf'].scale.free = True
wish_3_8.instrument.calib_d_to_tof_offset.free = True
wish_3_8.instrument.calib_d_to_tof_linear.free = True
wish_4_7.linked_structures['ncaf'].scale.free = True
wish_4_7.instrument.calib_d_to_tof_offset.free = True
wish_4_7.instrument.calib_d_to_tof_linear.free = True
wish_5_6.linked_structures['ncaf'].scale.free = True
wish_5_6.instrument.calib_d_to_tof_offset.free = True
wish_5_6.instrument.calib_d_to_tof_linear.free = True

# %%
project.display.parameters.free()

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('wish_1_10')

# %%
project.display.pattern('wish_2_9')

# %%
project.display.pattern('wish_3_8')

# %%
project.display.pattern('wish_4_7')

# %%
project.display.pattern('wish_5_6')

# %% [markdown]
# ### Background
#
# Each bank's background points; bank 1-10's first and last stay fixed, as its source has them.

# %%
for point in wish_1_10.background:
    point.intensity.free = True
for point in wish_2_9.background:
    point.intensity.free = True
for point in wish_3_8.background:
    point.intensity.free = True
for point in wish_4_7.background:
    point.intensity.free = True
for point in wish_5_6.background:
    point.intensity.free = True
wish_1_10.background[0].intensity.free = False
wish_1_10.background[35].intensity.free = False

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('wish_1_10')

# %%
project.display.pattern('wish_2_9')

# %%
project.display.pattern('wish_3_8')

# %%
project.display.pattern('wish_4_7')

# %%
project.display.pattern('wish_5_6')

# %% [markdown]
# ### Peak asymmetry
#
# Each bank's back-to-back exponentials, the terms its data determine; bank 1-10 keeps its
# instrument values.

# %%
wish_2_9.peak.rise_alpha_0.free = True
wish_2_9.peak.rise_alpha_1.free = True
wish_2_9.peak.decay_beta_0.free = True
wish_2_9.peak.decay_beta_1.free = True
wish_3_8.peak.rise_alpha_0.free = True
wish_3_8.peak.rise_alpha_1.free = True
wish_3_8.peak.decay_beta_0.free = True
wish_3_8.peak.decay_beta_1.free = True
wish_4_7.peak.rise_alpha_0.free = True
wish_4_7.peak.rise_alpha_1.free = True
wish_4_7.peak.decay_beta_0.free = True
wish_4_7.peak.decay_beta_1.free = True
wish_5_6.peak.rise_alpha_0.free = True
wish_5_6.peak.rise_alpha_1.free = True
wish_5_6.peak.decay_beta_0.free = True
wish_5_6.peak.decay_beta_1.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('wish_2_9')

# %% [markdown]
# ### Gaussian widths
#
# The Gaussian width terms the banks' data determine.

# %%
wish_2_9.peak.broad_gauss_sigma_1.free = True
wish_2_9.peak.broad_gauss_sigma_2.free = True
wish_3_8.peak.broad_gauss_sigma_1.free = True
wish_3_8.peak.broad_gauss_sigma_2.free = True
wish_4_7.peak.broad_gauss_sigma_1.free = True
wish_4_7.peak.broad_gauss_sigma_2.free = True
wish_5_6.peak.broad_gauss_sigma_2.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('wish_2_9')

# %% [markdown]
# ### Lorentzian width
#
# Bank 2-9's Lorentzian term.

# %%
wish_2_9.peak.broad_lorentz_gamma_1.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('wish_1_10')

# %%
project.display.pattern('wish_2_9')

# %%
project.display.pattern('wish_3_8')

# %%
project.display.pattern('wish_4_7')

# %%
project.display.pattern('wish_5_6')

# %% [markdown]
# ### Absorption
#
# Banks 2-9 to 5-6 each fit their absorption.

# %%
wish_2_9.absorption.abscor1.free = True
wish_3_8.absorption.abscor1.free = True
wish_4_7.absorption.abscor1.free = True
wish_5_6.absorption.abscor1.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('wish_1_10')

# %%
project.display.pattern('wish_2_9')

# %%
project.display.pattern('wish_3_8')

# %%
project.display.pattern('wish_4_7')

# %%
project.display.pattern('wish_5_6')

# %% [markdown]
# ### Atom positions
#
# The coordinates the cubic symmetry leaves free.

# %%
for site in structure.atom_sites:
    for coordinate in (site.fract_x, site.fract_y, site.fract_z):
        coordinate.free = not coordinate.symmetry_constrained

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('wish_1_10')

# %%
project.display.pattern('wish_2_9')

# %%
project.display.pattern('wish_3_8')

# %%
project.display.pattern('wish_4_7')

# %%
project.display.pattern('wish_5_6')

# %% [markdown]
# ### Displacements

# %%
for site in structure.atom_sites:
    site.adp_iso.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('wish_1_10')

# %%
project.display.pattern('wish_2_9')

# %%
project.display.pattern('wish_3_8')

# %%
project.display.pattern('wish_4_7')

# %%
project.display.pattern('wish_5_6')

# %%
project.display.fit.correlations()

# %%
project.display.structure('ncaf')

# %% [markdown]
# ## Save the project

# %%
project.save_as('pd-neut-tof_ncaf-wish')
project.report.save_html('pd-neut-tof_ncaf-wish.html')
