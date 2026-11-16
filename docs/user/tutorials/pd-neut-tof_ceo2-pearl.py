"""Calibration fit: CeO₂, PEARL."""
# %% [markdown]
# # Calibration fit: CeO₂, PEARL
#
# Fit the CeO₂ standard to time-of-flight neutron powder data from PEARL at ISIS: the calibration
# and the profile, with a polynomial background.
#
# It builds the catalogue case `pd-neut-tof_ceo2-pearl` step by step: the same project the command
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
project = edi.Project(name='pd-neut-tof_ceo2-pearl')

# %% [markdown]
# ## Define the structure
#
# Load the structure from EasyDiffraction's collection. Its CIF gives the space group, the cell and
# the atom sites.

# %%
path = edi.download_data('pd-neut-tof_ceo2-pearl-ceo2', destination='data')
project.structures.add_from_cif_path(path)
structure = project.structures['ceo2']

# %%
project.display.structure('ceo2')

# %% [markdown]
# ## Define the experiment
#
# Create the experiment from the measured data in EasyDiffraction's collection, then describe the
# instrument, the peak profile, the background and the structure it links.

# %%
data_path = edi.download_data('pd-neut-tof_ceo2-pearl-pearl-data', destination='data')
project.experiments.add_from_data_path(
    name='pearl',
    data_path=data_path,
    sample_form='powder',
    beam_mode='time-of-flight',
    radiation_probe='neutron',
    scattering_type='bragg',
)
experiment = project.experiments['pearl']
experiment.neutron_scattering_length = 'sears1992'
experiment.peak.type = 'tof-jorgensen-von-dreele'
experiment.absorption.type = 'cylinder'
experiment.background.type = 'polynomial'
experiment.instrument.name = 'PEARL'
experiment.instrument.facility = 'ISIS'
experiment.peak.cutoff_fwhm = 8.0
experiment.peak.rise_alpha_1 = 0.3
experiment.peak.decay_beta_0 = 0.03
experiment.peak.decay_beta_1 = 0.03
experiment.peak.broad_gauss_sigma_1 = 80
experiment.peak.broad_gauss_sigma_2 = 4
experiment.peak.broad_lorentz_gamma_1 = 5
experiment.instrument.setup_twotheta_bank = 90.0
experiment.instrument.calib_d_to_tof_linear = 4680
experiment.instrument.calib_d_to_tof_quadratic = 1.7621
experiment.background_origin = 7000.0
experiment.excluded_regions.create(start=1000.1, end=2000.0)
experiment.excluded_regions.create(start=18700.0, end=20000.0)
experiment.linked_structures.create(structure_id='ceo2', scale=2000)
terms = []
for coef in (2200.0, 0, 0, 0, 0, 0):
    term = edi.PolynomialTerm()
    term.order = len(terms)
    term.coef = coef
    terms.append(term)
experiment.background_terms = terms

# %%
project.display.pattern('pearl')

# %% [markdown]
# ## Perform the analysis
#
# The fit goes in stages, freeing one group of parameters at a time.

# %% [markdown]
# ### Scale and time-of-flight calibration
#
# CeO₂ is the calibration standard, so its cell stays fixed and the DIFC terms put the peaks in
# place.

# %%
experiment.linked_structures['ceo2'].scale.free = True
experiment.instrument.calib_d_to_tof_offset.free = True
experiment.instrument.calib_d_to_tof_linear.free = True
experiment.instrument.calib_d_to_tof_quadratic.free = True

# %%
project.display.parameters.free()

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('pearl')

# %% [markdown]
# ### Background
#
# The six polynomial terms follow the level between the peaks.

# %%
for term in experiment.background_terms:
    term.coef.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('pearl')

# %% [markdown]
# ### Gaussian widths
#
# The Gaussian terms that grow with d spacing.

# %%
experiment.peak.broad_gauss_sigma_1.free = True
experiment.peak.broad_gauss_sigma_2.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('pearl')

# %% [markdown]
# ### Lorentzian width
#
# The Lorentzian term that grows with d spacing.

# %%
experiment.peak.broad_lorentz_gamma_1.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('pearl')

# %% [markdown]
# ### Rise and decay
#
# The back-to-back exponentials that shape each time-of-flight peak.

# %%
experiment.peak.rise_alpha_1.free = True
experiment.peak.decay_beta_0.free = True
experiment.peak.decay_beta_1.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('pearl')

# %% [markdown]
# ### Displacements

# %%
structure.atom_sites['Ce'].adp_iso.free = True
structure.atom_sites['O'].adp_iso.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('pearl')

# %% [markdown]
# ### Absorption
#
# Absorption weakens the intensities with time of flight, as the displacements do, so it comes
# after them, on its own.

# %%
experiment.absorption.abscor1.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('pearl')

# %%
project.display.fit.correlations()

# %%
project.display.structure('ceo2')

# %% [markdown]
# ## Report
#
# The HTML report draws the measured, calculated and difference patterns with the reflection
# positions, and lists the structures, the experiments and the fit. Open it in a browser.

# %%
project.report.save_html('pd-neut-tof_ceo2-pearl.html')

# %% [markdown]
# ## Save the project

# %%
project.save_as('pd-neut-tof_ceo2-pearl')
