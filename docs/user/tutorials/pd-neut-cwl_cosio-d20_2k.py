"""Magnetic structure fit: Co₂SiO₄ at 2.3 K, D20."""
# %% [markdown]
# # Magnetic structure fit: Co₂SiO₄ at 2.3 K, D20
#
# Fit the magnetic structure of the olivine Co₂SiO₄ to constant-wavelength neutron powder data
# from D20 at ILL, measured at 2.3 K, below its ordering temperature. The cobalt moments order with
# k = 0 in the magnetic space group Pnma.1: Co1 may point in any direction, Co2 only along b.
#
# The project is the catalogue case `pd-neut-cwl_cosio-d20_2k`, the one the command line and the
# app's Examples open. Its two Co sites share one displacement, and the two FCJ asymmetry terms are
# tied, from the start.

# %%
import easydiffraction as edi

# %% [markdown]
# ## Load the project

# %%
project_path = edi.download_data('pd-neut-cwl_cosio-d20_2k', destination='data')
project = edi.Project.load(project_path)
structure = project.structures['cosio']
experiment = project.experiments['d20']
project.display.constraints()

# %% [markdown]
# The project marks what its fit frees. The fit below frees it in stages, so start with all of it
# fixed.

# %%
for parameter in project.free_parameters:
    parameter.free = False

# %%
project.display.pattern('d20')

# %% [markdown]
# ## Perform the analysis
#
# Everything starts fixed, and five stages each free one more group, keeping the earlier ones free:
# the scale, cell and moments, then the background, the atoms, the peak widths and last the peak
# asymmetry.
#
# ### Scale, 2θ zero, cell and magnetic moments
#
# The first stage frees the phase scale, the 2θ zero shift, the three cell lengths and the magnetic
# model: the moment components the magnetic space group allows (Co1 in any direction, Co2 only
# along b) and the j2 term of the Co²⁺ form factor, which sets how the magnetic intensities fall
# with angle.

# %%
experiment.linked_structures['cosio'].scale.free = True
experiment.instrument.calib_twotheta_offset.free = True
structure.cell.length_a.free = True
structure.cell.length_b.free = True
structure.cell.length_c.free = True
structure.atom_site_moment['Co1'].crystalaxis_x.free = True
structure.atom_site_moment['Co1'].crystalaxis_y.free = True
structure.atom_site_moment['Co1'].crystalaxis_z.free = True
structure.atom_site_moment['Co2'].crystalaxis_y.free = True
structure.magnetic_form_factor['Co'].j2_coefficient.free = True

# %%
project.display.parameters.free()

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('d20')

# %% [markdown]
# ### Background
#
# The second stage frees the sixteen background points, which follow the level between the peaks.

# %%
for point in experiment.background:
    point.intensity.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('d20')

# %% [markdown]
# ### Atomic displacements and positions
#
# The third stage frees the atoms: each site's isotropic displacement (Co2's follows Co1's by the
# project's constraint) and the coordinates the symmetry leaves free. Co1 sits on a centre of
# symmetry, so it has none; the other sites lie on the mirror plane, except O3.

# %%
for site in structure.atom_sites:
    site.adp_iso.free = not site.adp_iso.user_constrained
    for coordinate in (site.fract_x, site.fract_y, site.fract_z):
        coordinate.free = not coordinate.symmetry_constrained

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('d20')

# %% [markdown]
# ### Peak widths
#
# The fourth stage frees the peak profile: the Gaussian widths U, V and W and the Lorentzian Y.

# %%
experiment.peak.broad_gauss_u.free = True
experiment.peak.broad_gauss_v.free = True
experiment.peak.broad_gauss_w.free = True
experiment.peak.broad_lorentz_y.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('d20')

# %% [markdown]
# ### Peak asymmetry
#
# The last stage frees the asymmetry: the low-angle peaks lean towards low angle. One FCJ term is
# freed; the other follows it by the project's constraint.

# %%
experiment.peak.asym_fcj_1.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('d20')

# %%
project.display.fit.correlations()

# %%
project.display.structure('cosio')

# %% [markdown]
# ## Save the project

# %%
project.save_as('pd-neut-cwl_cosio-d20_2k')
project.report.save_html('pd-neut-cwl_cosio-d20_2k.html')
