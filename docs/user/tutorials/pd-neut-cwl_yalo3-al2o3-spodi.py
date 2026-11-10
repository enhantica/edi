"""Two-phase fit: YAlO₃ and Al₂O₃, SPODI."""
# %% [markdown]
# # Two-phase fit: YAlO₃ and Al₂O₃, SPODI
#
# Fit two phases, YAlO₃ and corundum Al₂O₃, in one constant-wavelength neutron pattern from SPODI
# at FRM II, measured at 3 K, with a shared Bérar-Baldinozzi profile and cylinder absorption.
#
# The project is the catalogue case `pd-neut-cwl_yalo3-al2o3-spodi`, the one the command line and
# the app's Examples open.

# %%
import easydiffraction as edi

# %% [markdown]
# ## Load the project

# %%
project_path = edi.download_data('pd-neut-cwl_yalo3-al2o3-spodi', destination='data')
project = edi.Project.load(project_path)
yalo3 = project.structures['YAlO3']
alumina = project.structures['Al2O3']
experiment = project.experiments['spodi']

# %% [markdown]
# The project marks what its fit frees. The fit below frees it in stages, so start with all of it
# fixed.

# %%
for parameter in project.free_parameters:
    parameter.free = False

# %%
project.display.pattern('spodi')

# %% [markdown]
# ## Perform the analysis
#
# The fit follows diffraction-lib's three cycles for this case (its YAP tutorial). diffraction-lib
# frees the Lorentzian Y and two asymmetry terms where this profile has the mixing η₀ and four.

# %% [markdown]
# ### Cells, scales and 2θ zero
#
# Both phases' cells and scales, and the zero shift, put the peaks of both phases in place.

# %%
yalo3.cell.length_a.free = True
yalo3.cell.length_b.free = True
yalo3.cell.length_c.free = True
alumina.cell.length_a.free = True
alumina.cell.length_c.free = True
experiment.linked_structures['YAlO3'].scale.free = True
experiment.linked_structures['Al2O3'].scale.free = True
experiment.instrument.calib_twotheta_offset.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('spodi')

# %% [markdown]
# ### Background

# %%
for point in experiment.background:
    point.intensity.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('spodi')

# %% [markdown]
# ### Peak widths
#
# The Gaussian widths and the mixing η₀.

# %%
experiment.peak.broad_gauss_u.free = True
experiment.peak.broad_gauss_v.free = True
experiment.peak.broad_gauss_w.free = True
experiment.peak.mixing_eta_0.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('spodi')

# %% [markdown]
# ### Asymmetry
#
# The four Bérar-Baldinozzi asymmetry terms.

# %%
experiment.peak.asym_beba_a0.free = True
experiment.peak.asym_beba_b0.free = True
experiment.peak.asym_beba_a1.free = True
experiment.peak.asym_beba_b1.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('spodi')

# %% [markdown]
# ### Atom positions
#
# The coordinates the symmetry leaves free in both phases.

# %%
yalo3.atom_sites['Y'].fract_x.free = True
yalo3.atom_sites['Y'].fract_y.free = True
yalo3.atom_sites['O1'].fract_x.free = True
yalo3.atom_sites['O1'].fract_y.free = True
yalo3.atom_sites['O2'].fract_x.free = True
yalo3.atom_sites['O2'].fract_y.free = True
yalo3.atom_sites['O2'].fract_z.free = True
alumina.atom_sites['Al1'].fract_z.free = True
alumina.atom_sites['O1'].fract_x.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('spodi')

# %% [markdown]
# ### Displacements
#
# Every site's displacement in both phases.

# %%
for structure in (yalo3, alumina):
    for site in structure.atom_sites:
        site.adp_iso.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('spodi')

# %%
project.display.fit.correlations()

# %%
project.display.structure('YAlO3')

# %%
project.display.structure('Al2O3')

# %% [markdown]
# ## Save the project

# %%
project.save_as('pd-neut-cwl_yalo3-al2o3-spodi')
project.report.save_html('pd-neut-cwl_yalo3-al2o3-spodi.html')
