"""Rietveld fit: herbertsmithite, HRPT."""
# %% [markdown]
# # Rietveld fit: herbertsmithite, HRPT
#
# Fit herbertsmithite, ZnCu₃(OD)₆Cl₂, a deuterated kagome antiferromagnet, to constant-wavelength
# neutron powder data from HRPT at PSI, with a pseudo-Voigt profile and Bérar-Baldinozzi
# asymmetry.
#
# It builds the catalogue case `pd-neut-cwl_hs-hrpt` step by step: the same project the command
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
project = edi.Project(name='pd-neut-cwl_hs-hrpt')

# %% [markdown]
# ## Define the structure
#
# Load the structure from EasyDiffraction's collection. Its CIF gives the space group, the cell and
# the atom sites.

# %%
path = edi.download_data('pd-neut-cwl_hs-hrpt-hs', destination='data')
project.structures.add_from_cif_path(path)
structure = project.structures['hs']

# %%
project.display.structure('hs')

# %% [markdown]
# ## Define the experiment
#
# Create the experiment from the measured data in EasyDiffraction's collection, then describe the
# instrument, the peak profile, the background and the structure it links.

# %%
data_path = edi.download_data('pd-neut-cwl_hs-hrpt-hrpt-data', destination='data')
project.experiments.add_from_data_path(
    name='hrpt',
    data_path=data_path,
    sample_form='powder',
    beam_mode='constant wavelength',
    radiation_probe='neutron',
    scattering_type='bragg',
)
experiment = project.experiments['hrpt']
experiment.neutron_scattering_length = 'sears1992'
experiment.peak.type = 'cwl-pseudo-voigt-berar-baldinozzi'
experiment.instrument.name = 'HRPT'
experiment.instrument.facility = 'PSI'
experiment.peak.broad_gauss_u = 0.1
experiment.peak.broad_gauss_v = -0.2
experiment.peak.broad_gauss_w = 0.2
experiment.peak.mixing_eta_0 = 0.5
experiment.peak.cutoff_fwhm = 8
experiment.instrument.setup_wavelength = 1.89
experiment.linked_structures.create(structure_id='hs', scale=0.5)
experiment.background.create(position=4, intensity=460.0)
experiment.background.create(position=20, intensity=460.0)
experiment.background.create(position=40, intensity=460.0)
experiment.background.create(position=60, intensity=460.0)
experiment.background.create(position=80, intensity=460.0)
experiment.background.create(position=100, intensity=460.0)
experiment.background.create(position=120, intensity=460.0)
experiment.background.create(position=140, intensity=460.0)
experiment.background.create(position=160, intensity=460.0)
experiment.background.create(position=165, intensity=460.0)

# %%
project.display.pattern('hrpt')

# %% [markdown]
# ## Perform the analysis
#
# The fit follows diffraction-lib's four cycles for this case.

# %% [markdown]
# ### Cell, scale and 2θ zero
#
# The cell lengths, the scale and the zero shift put the peaks in place and at the right height.

# %%
structure.cell.length_a.free = True
structure.cell.length_c.free = True
experiment.linked_structures['hs'].scale.free = True
experiment.instrument.calib_twotheta_offset.free = True

# %%
project.display.parameters.free()

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('hrpt')

# %% [markdown]
# ### Background
#
# The estimated points are a starting point; fit them now that the peaks are in place.

# %%
for point in experiment.background:
    point.intensity.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('hrpt')

# %% [markdown]
# ### Peak widths
#
# The Gaussian widths and the mixing η₀, with the background staying free. diffraction-lib frees
# the Lorentzian Y where this profile has η₀.

# %%
experiment.peak.broad_gauss_u.free = True
experiment.peak.broad_gauss_v.free = True
experiment.peak.broad_gauss_w.free = True
experiment.peak.mixing_eta_0.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('hrpt')

# %% [markdown]
# ### Atom positions
#
# The coordinates the symmetry leaves free: O and H in x and z, Cl in z.

# %%
for site in structure.atom_sites:
    for coordinate in (site.fract_x, site.fract_y, site.fract_z):
        coordinate.free = not coordinate.symmetry_constrained

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('hrpt')

# %% [markdown]
# ### Displacements
#
# Every site's displacement.

# %%
for site in structure.atom_sites:
    site.adp_iso.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('hrpt')

# %% [markdown]
# ### Asymmetry
#
# Last, the four Bérar-Baldinozzi asymmetry terms.

# %%
experiment.peak.asym_beba_a0.free = True
experiment.peak.asym_beba_b0.free = True
experiment.peak.asym_beba_a1.free = True
experiment.peak.asym_beba_b1.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('hrpt')

# %%
project.display.fit.correlations()

# %%
project.display.structure('hs')

# %% [markdown]
# ## Report
#
# The HTML report draws the measured, calculated and difference patterns with the reflection
# positions, and lists the structures, the experiments and the fit. Open it in a browser.

# %%
project.report.save_html('pd-neut-cwl_hs-hrpt.html')

# %% [markdown]
# ## Save the project

# %%
project.save_as('pd-neut-cwl_hs-hrpt')
