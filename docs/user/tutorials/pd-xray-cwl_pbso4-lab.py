"""Rietveld fit: PbSO₄, laboratory X-ray."""
# %% [markdown]
# # Rietveld fit: PbSO₄, laboratory X-ray
#
# Fit PbSO₄ to the Rietveld round robin's laboratory X-ray pattern, with the Cu K&alpha; doublet
# and Bérar-Baldinozzi asymmetry.
#
# It builds the catalogue case `pd-xray-cwl_pbso4-lab` step by step: the same project the command
# line fits and the app's Examples open.

# %% [markdown]
# ## Import the library

# %%
import easydiffraction as edi

# %% [markdown]
# ## Define the project
#
# A new project is empty: it holds no structure and no experiment until you add them.

# %%
project = edi.Project(name='pd-xray-cwl_pbso4-lab')

# %% [markdown]
# ## Define the structure
#
# Load the structure from EasyDiffraction's collection. Its CIF gives the space group, the cell and
# the atom sites.

# %%
path = edi.download_data('pd-xray-cwl_pbso4-lab-pbso4', destination='data')
project.structures.add_from_cif_path(path)
structure = project.structures['pbso4']

# %%
project.display.structure('pbso4')

# %% [markdown]
# ## Define the experiment
#
# Create the experiment from the measured data in EasyDiffraction's collection, then describe the
# instrument, the peak profile, the background and the structure it links.

# %%
data_path = edi.download_data('pd-xray-cwl_pbso4-lab-lab-data', destination='data')
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
project.display.pattern('lab')

# %% [markdown]
# ## Perform the analysis
#
# The fit goes in stages, freeing one group of parameters at a time.

# %% [markdown]
# ### Scale and 2θ zero
#
# The 2θ zero first: freed together with the cell from the start, the two pull against each
# other and the fit cannot take a step.

# %%
lab.linked_structures['pbso4'].scale.free = True
lab.instrument.calib_twotheta_offset.free = True

# %%
project.display.parameters.free()

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('lab')

# %% [markdown]
# ### Cell

# %%
structure.cell.length_a.free = True
structure.cell.length_b.free = True
structure.cell.length_c.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('lab')

# %% [markdown]
# ### Background
#
# The six Chebyshev terms.

# %%
for term in lab.background_terms:
    term.coef.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('lab')

# %% [markdown]
# ### Peak widths

# %%
lab.peak.broad_gauss_u.free = True
lab.peak.broad_gauss_v.free = True
lab.peak.broad_gauss_w.free = True
lab.peak.mixing_eta_0.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('lab')

# %% [markdown]
# ### Peak asymmetry

# %%
lab.peak.asym_beba_a0.free = True
lab.peak.asym_beba_b0.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('lab')

# %% [markdown]
# ### Lead and sulphur positions
#
# X-rays see the heavy atoms first, so their coordinates come before the oxygens'.

# %%
for site in structure.atom_sites:
    if site.type_symbol != 'O':
        for coordinate in (site.fract_x, site.fract_y, site.fract_z):
            coordinate.free = not coordinate.symmetry_constrained

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('lab')

# %% [markdown]
# ### Oxygen positions

# %%
for site in structure.atom_sites:
    if site.type_symbol == 'O':
        for coordinate in (site.fract_x, site.fract_y, site.fract_z):
            coordinate.free = not coordinate.symmetry_constrained

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('lab')

# %% [markdown]
# ### Displacements
#
# The correlations after this stage show how far the oxygen displacements can be told apart; the
# case keeps them separate.

# %%
for site in structure.atom_sites:
    site.adp_iso.free = True

# %%
project.analysis.fit()
project.display.fit.results()

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
project.report.save_html('pd-xray-cwl_pbso4-lab.html')

# %% [markdown]
# ## Save the project

# %%
project.save_as('pd-xray-cwl_pbso4-lab')
