"""Joint fit: PbSO₄, neutron and X-ray."""
# %% [markdown]
# # Joint fit: PbSO₄, neutron and X-ray
#
# Fit PbSO₄ to two patterns at once, the Rietveld round robin's neutron pattern from D1A at ILL
# and its laboratory X-ray pattern: one structure, two experiments.
#
# The project is the catalogue case `pd-neut-xray-cwl_pbso4-d1a-lab`, the one the command line and
# the app's Examples open.

# %%
import easydiffraction as edi

# %% [markdown]
# ## Load the project

# %%
project_path = edi.download_data('pd-neut-xray-cwl_pbso4-d1a-lab', destination='data')
project = edi.Project.load(project_path)
structure = project.structures['pbso4']
d1a = project.experiments['d1a']
lab = project.experiments['lab']

# %% [markdown]
# The project marks what its fit frees. The fit below frees it in stages, so start with all of it
# fixed.

# %%
for parameter in project.free_parameters:
    parameter.free = False

# %%
project.display.pattern('d1a')

# %% [markdown]
# ## Perform the analysis
#
# Both patterns fit together. diffraction-lib's tutorial of this case frees everything at once,
# and also the D1A wavelength, which this case keeps fixed.

# %% [markdown]
# ### Scales, 2θ zeros and cell

# %%
d1a.linked_structures['pbso4'].scale.free = True
lab.linked_structures['pbso4'].scale.free = True
d1a.instrument.calib_twotheta_offset.free = True
lab.instrument.calib_twotheta_offset.free = True
structure.cell.length_a.free = True
structure.cell.length_b.free = True
structure.cell.length_c.free = True

# %%
project.display.parameters.free()

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('d1a')

# %%
project.display.pattern('lab')

# %% [markdown]
# ### Backgrounds
#
# D1A's points and the laboratory pattern's Chebyshev terms.

# %%
for point in d1a.background:
    point.intensity.free = True
for term in lab.background_terms:
    term.coef.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('d1a')

# %%
project.display.pattern('lab')

# %% [markdown]
# ### Peak widths

# %%
d1a.peak.broad_gauss_u.free = True
d1a.peak.broad_gauss_v.free = True
d1a.peak.broad_gauss_w.free = True
d1a.peak.mixing_eta_0.free = True
lab.peak.broad_gauss_u.free = True
lab.peak.broad_gauss_v.free = True
lab.peak.broad_gauss_w.free = True
lab.peak.mixing_eta_0.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('d1a')

# %%
project.display.pattern('lab')

# %% [markdown]
# ### Peak asymmetry, D1A
#
# The D1A pattern's four Bérar–Baldinozzi terms.

# %%
d1a.peak.asym_beba_a0.free = True
d1a.peak.asym_beba_b0.free = True
d1a.peak.asym_beba_a1.free = True
d1a.peak.asym_beba_b1.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('d1a')

# %%
project.display.pattern('lab')

# %% [markdown]
# ### Peak asymmetry, laboratory
#
# The laboratory pattern's first-order terms.

# %%
lab.peak.asym_beba_a0.free = True
lab.peak.asym_beba_b0.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('d1a')

# %%
project.display.pattern('lab')

# %% [markdown]
# ### Atom positions
#
# The neutron and X-ray patterns together see the oxygen as well as the lead, so all free
# coordinates fit at once.

# %%
for site in structure.atom_sites:
    for coordinate in (site.fract_x, site.fract_y, site.fract_z):
        coordinate.free = not coordinate.symmetry_constrained

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('d1a')

# %%
project.display.pattern('lab')

# %% [markdown]
# ### Displacements

# %%
for site in structure.atom_sites:
    site.adp_iso.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('d1a')

# %%
project.display.pattern('lab')

# %%
project.display.fit.correlations()

# %%
project.display.structure('pbso4')

# %% [markdown]
# ## Save the project

# %%
project.save_as('pd-neut-xray-cwl_pbso4-d1a-lab')
project.report.save_html('pd-neut-xray-cwl_pbso4-d1a-lab.html')
