"""Rietveld fit: CeCoAl₃, POLARIS."""
# %% [markdown]
# # Rietveld fit: CeCoAl₃, POLARIS
#
# Fit CeCoAl₃ to time-of-flight neutron powder data from POLARIS at ISIS: structure and profile,
# with a 24-term Chebyshev background.
#
# It builds the catalogue case `pd-neut-tof_cecoal-polaris` step by step: the same project the
# command line fits and the app's Examples open.

# %% [markdown]
# ## Import the library

# %%
import easydiffraction as edi

# %% [markdown]
# ## Define the project
#
# A new project is empty: it holds no structure and no experiment until you add them.

# %%
project = edi.Project(name='pd-neut-tof_cecoal-polaris')

# %% [markdown]
# ## Define the structure
#
# Load the structure from EasyDiffraction's collection. Its CIF gives the space group, the cell and
# the atom sites.

# %%
path = edi.download_data('pd-neut-tof_cecoal-polaris-cecoal', destination='data')
project.structures.add_from_cif_path(path)
structure = project.structures['cecoal']

# %%
project.display.structure('cecoal')

# %% [markdown]
# ## Define the experiment
#
# Create the experiment from the measured data in EasyDiffraction's collection, then describe the
# instrument, the peak profile, the background and the structure it links.

# %%
data_path = edi.download_data('pd-neut-tof_cecoal-polaris-polaris-data', destination='data')
project.experiments.add_from_data_path(
    name='polaris',
    data_path=data_path,
    sample_form='powder',
    beam_mode='time-of-flight',
    radiation_probe='neutron',
    scattering_type='bragg',
)
experiment = project.experiments['polaris']
experiment.neutron_scattering_length = 'sears1992'
experiment.peak.type = 'tof-jorgensen-von-dreele'
experiment.absorption.type = 'cylinder'
experiment.background.type = 'chebyshev'
experiment.instrument.name = 'POLARIS'
experiment.instrument.facility = 'ISIS'
experiment.peak.cutoff_fwhm = 4.2
experiment.peak.rise_alpha_1 = 0.2971
experiment.peak.decay_beta_0 = 0.043085
experiment.peak.decay_beta_1 = 0.002867
experiment.peak.broad_gauss_sigma_1 = 40
experiment.peak.broad_lorentz_gamma_1 = 5
experiment.instrument.setup_twotheta_bank = 145.0
experiment.instrument.calib_d_to_tof_linear = 6176.03076
experiment.instrument.calib_d_to_tof_quadratic = -1.92194
experiment.background_x_min = 3001.5891
experiment.background_x_max = 19004.6582
experiment.excluded_regions.create(start=2000.1, end=3000.0)
experiment.excluded_regions.create(start=19000.0, end=20000.0)
experiment.linked_structures.create(structure_id='cecoal', scale=20000)
terms = []
for coef in (25000.0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0):
    term = edi.PolynomialTerm()
    term.order = len(terms)
    term.coef = coef
    terms.append(term)
experiment.background_terms = terms

# %%
project.display.pattern('polaris')

# %% [markdown]
# ## Perform the analysis
#
# The fit goes in stages, freeing one group of parameters at a time.

# %% [markdown]
# ### Scale, time-of-flight calibration and cell
#
# The scale, the DIFC offset and its quadratic term, and the three cell lengths put the peaks in
# place and at the right height.

# %%
experiment.linked_structures['cecoal'].scale.free = True
experiment.instrument.calib_d_to_tof_offset.free = True
experiment.instrument.calib_d_to_tof_quadratic.free = True
structure.cell.length_a.free = True
structure.cell.length_b.free = True
structure.cell.length_c.free = True

# %%
project.display.parameters.free()

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('polaris')

# %% [markdown]
# ### Background
#
# The first twelve polynomial terms (orders 0 to 11) follow the level between the peaks; the
# higher ones stay at zero.

# %%
for term in list(experiment.background_terms)[:12]:
    term.coef.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('polaris')

# %% [markdown]
# ### Peak widths

# %%
experiment.peak.broad_gauss_sigma_1.free = True
experiment.peak.broad_lorentz_gamma_1.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('polaris')

# %% [markdown]
# ### Atom positions
#
# The coordinates the symmetry leaves free.

# %%
for site in structure.atom_sites:
    for coordinate in (site.fract_x, site.fract_y, site.fract_z):
        coordinate.free = not coordinate.symmetry_constrained

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('polaris')

# %% [markdown]
# ### Displacements

# %%
for site in structure.atom_sites:
    site.adp_iso.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('polaris')

# %% [markdown]
# ### Absorption
#
# Absorption weakens the intensities with time of flight, as the displacements do with angle, so
# it comes after them, on its own.

# %%
experiment.absorption.abscor1.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('polaris')

# %% [markdown]
# ### Al3 occupancy
#
# Last, Al3's occupancy, which moves with its displacement.

# %%
structure.atom_sites['Al3'].occupancy.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('polaris')

# %%
project.display.fit.correlations()

# %%
project.display.structure('cecoal')

# %% [markdown]
# ## Report
#
# The HTML report draws the measured, calculated and difference patterns with the reflection
# positions, and lists the structures, the experiments and the fit. Open it in a browser.

# %%
project.report.save_html('pd-neut-tof_cecoal-polaris.html')

# %% [markdown]
# ## Save the project

# %%
project.save_as('pd-neut-tof_cecoal-polaris')
