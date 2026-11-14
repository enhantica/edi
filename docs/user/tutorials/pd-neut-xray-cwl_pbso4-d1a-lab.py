"""Joint fit: PbSO₄, neutron and X-ray."""
# %% [markdown]
# # Joint fit: PbSO₄, neutron and X-ray
#
# Fit PbSO₄ to two patterns at once, the Rietveld round robin's neutron pattern from D1A at ILL
# and its laboratory X-ray pattern: one structure, two experiments.
#
# It builds the catalogue case `pd-neut-xray-cwl_pbso4-d1a-lab` step by step: the same project the
# command line fits and the app's Examples open.

# %% [markdown]
# ## Import the library

# %%
import easydiffraction as edi

# %% [markdown]
# ## Define the project
#
# A new project is empty: it holds no structure and no experiment until you add them. The joint
# fitting mode fits every experiment at once, against one set of structures.

# %%
project = edi.Project(name='pd-neut-xray-cwl_pbso4-d1a-lab')
project.analysis.fitting_mode = 'joint'

# %% [markdown]
# ## Define the structure
#
# Load the structure from EasyDiffraction's collection. Its CIF gives the space group, the cell and
# the atom sites.

# %%
path = edi.download_data('pd-neut-xray-cwl_pbso4-d1a-lab-pbso4', destination='data')
project.structures.add_from_cif_path(path)
structure = project.structures['pbso4']

# %%
project.display.structure('pbso4')

# %% [markdown]
# ## Define the experiments
#
# Create the two experiments from their measured data in EasyDiffraction's collection, then
# describe each one's instrument, peak profile, background and the structures it links.

# %%
data_path = edi.download_data('pd-neut-xray-cwl_pbso4-d1a-lab-d1a-data', destination='data')
project.experiments.add_from_data_path(
    name='d1a',
    data_path=data_path,
    sample_form='powder',
    beam_mode='constant wavelength',
    radiation_probe='neutron',
    scattering_type='bragg',
)
d1a = project.experiments['d1a']
d1a.neutron_scattering_length = 'sears1992'
d1a.peak.type = 'cwl-pseudo-voigt-berar-baldinozzi'
d1a.instrument.name = 'D1A'
d1a.instrument.facility = 'ILL'
d1a.peak.broad_gauss_u = 0.2
d1a.peak.broad_gauss_v = -0.5
d1a.peak.broad_gauss_w = 0.4
d1a.peak.mixing_eta_0 = 0.5
d1a.peak.cutoff_fwhm = 30
d1a.instrument.setup_wavelength = 1.91
d1a.linked_structures.create(structure_id='pbso4', scale=1.5)
d1a.background.create(position=11, intensity=200.0)
d1a.background.create(position=15, intensity=200.0)
d1a.background.create(position=20, intensity=200.0)
d1a.background.create(position=30, intensity=200.0)
d1a.background.create(position=50, intensity=200.0)
d1a.background.create(position=70, intensity=200.0)
d1a.background.create(position=120, intensity=200.0)
d1a.background.create(position=153, intensity=200.0)

# %%
data_path = edi.download_data('pd-neut-xray-cwl_pbso4-d1a-lab-lab-data', destination='data')
project.experiments.add_from_data_path(
    name='lab',
    data_path=data_path,
    sample_form='powder',
    beam_mode='constant wavelength',
    radiation_probe='xray',
    scattering_type='bragg',
)
lab = project.experiments['lab']
lab.xray_form_factor = 'it1992'
lab.xray_dispersion = 'sasaki1989'
lab.peak.type = 'cwl-pseudo-voigt-berar-baldinozzi'
lab.background.type = 'chebyshev'
lab.peak.broad_gauss_u = 0.02
lab.peak.broad_gauss_v = -0.02
lab.peak.broad_gauss_w = 0.008
lab.peak.mixing_eta_0 = 0.5
lab.peak.asym_beba_limit = 160
lab.peak.cutoff_fwhm = 48
lab.instrument.setup_wavelength = 1.54056
lab.instrument.setup_wavelength_2 = 1.5444
lab.instrument.setup_wavelength_2_to_1_ratio = 0.5
lab.instrument.setup_polarization_coefficient = 0.5
lab.instrument.setup_monochromator_twotheta = 26.5650511771
lab.background_x_min = 15
lab.background_x_max = 160
lab.excluded_regions.create(start=0, end=15)
lab.excluded_regions.create(start=160, end=180)
lab.linked_structures.create(structure_id='pbso4', scale=0.001)
terms = []
for coef in (140.0, 0, 0, 0, 0, 0):
    term = edi.PolynomialTerm()
    term.order = len(terms)
    term.coef = coef
    terms.append(term)
lab.background_terms = terms

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
# The D1A pattern's four Bérar-Baldinozzi terms.

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
# ## Report
#
# The HTML report draws the measured, calculated and difference patterns with the reflection
# positions, and lists the structures, the experiments and the fit. Open it in a browser.

# %%
project.report.save_html('pd-neut-xray-cwl_pbso4-d1a-lab.html')

# %% [markdown]
# ## Save the project

# %%
project.save_as('pd-neut-xray-cwl_pbso4-d1a-lab')
