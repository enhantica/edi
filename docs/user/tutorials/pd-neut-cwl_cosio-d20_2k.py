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
# The nuclear structure comes first, in the usual order; the magnetic moments come last, once the
# nuclear peaks are fitted.
#
# ### Scale, 2θ zero and cell

# %%
experiment.linked_structures['cosio'].scale.free = True
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
project.display.pattern('d20')

# %% [markdown]
# ### Background
#
# With the peaks in place, the sixteen background points follow the level between them.

# %%
for point in experiment.background:
    point.intensity.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('d20')

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
project.display.pattern('d20')

# %% [markdown]
# ### Peak asymmetry
#
# The low-angle peaks lean towards low angle. One FCJ term is freed; the other follows it by the
# project's constraint.

# %%
experiment.peak.asym_fcj_1.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('d20')

# %% [markdown]
# ### Atom positions
#
# Co1 sits on a centre of symmetry and the other sites on the mirror plane, so only their free
# coordinates are fitted. The displacements stay at their room-temperature values.

# %%
for site in structure.atom_sites:
    for coordinate in (site.fract_x, site.fract_y, site.fract_z):
        coordinate.free = not coordinate.symmetry_constrained

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('d20')

# %% [markdown]
# ### Magnetic moments
#
# With the nuclear peaks fitted, the moments fit the magnetic peaks. The magnetic space group lets
# Co1 point in any direction and Co2 only along b.

# %%
structure.atom_site_moment['Co1'].crystalaxis_x.free = True
structure.atom_site_moment['Co1'].crystalaxis_y.free = True
structure.atom_site_moment['Co1'].crystalaxis_z.free = True
structure.atom_site_moment['Co2'].crystalaxis_y.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('d20')

# %% [markdown]
# ### Magnetic form factor
#
# Last, the j2 term of the Co²⁺ form factor, which changes how the magnetic intensities fall with
# angle. It moves together with the moments, so it comes after them.

# %%
structure.magnetic_form_factor['Co'].j2_coefficient.free = True

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
