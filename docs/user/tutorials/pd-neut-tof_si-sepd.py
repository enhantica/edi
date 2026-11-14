"""Rietveld fit: Si, SEPD."""
# %% [markdown]
# # Rietveld fit: Si, SEPD
#
# Fit silicon to time-of-flight neutron powder data from SEPD at Argonne, with the Jorgensen-Von
# Dreele profile.
#
# It builds the catalogue case `pd-neut-tof_si-sepd` step by step: the same project the command
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
project = edi.Project(name='pd-neut-tof_si-sepd')

# %% [markdown]
# ## Define the structure
#
# Load the structure from EasyDiffraction's collection. Its CIF gives the space group, the cell and
# the atom sites.

# %%
path = edi.download_data('pd-neut-tof_si-sepd-si', destination='data')
project.structures.add_from_cif_path(path)
structure = project.structures['si']

# %%
project.display.structure('si')

# %% [markdown]
# ## Define the experiment
#
# Create the experiment from a file of measured data: `add_from_data_path` reads its time-of-
# flight, intensity and uncertainty columns. Here the file is SEPD's pattern from EasyDiffraction's
# collection; a file of your own on disk works the same way. Then describe the instrument, the peak
# profile, the background and the structure it links.

# %%
data_path = edi.download_data('pd-neut-tof_si-sepd-sepd-data', destination='data')
project.experiments.add_from_data_path(
    name='sepd',
    data_path=data_path,
    sample_form='powder',
    beam_mode='time-of-flight',
    radiation_probe='neutron',
    scattering_type='bragg',
)
experiment = project.experiments['sepd']
experiment.neutron_scattering_length = 'sears1992'
experiment.peak.type = 'tof-jorgensen-von-dreele'
experiment.absorption.type = 'none'
experiment.instrument.name = 'SEPD'
experiment.instrument.facility = 'Argonne'
experiment.peak.cutoff_fwhm = 8.2
experiment.peak.rise_alpha_1 = 0.5971
experiment.peak.decay_beta_0 = 0.04
experiment.peak.decay_beta_1 = 0.01
experiment.peak.broad_gauss_sigma_0 = 3
experiment.peak.broad_gauss_sigma_1 = 30
experiment.peak.broad_lorentz_gamma_1 = 3
experiment.instrument.setup_twotheta_bank = 144.845
experiment.instrument.calib_d_to_tof_linear = 7476.91
experiment.instrument.calib_d_to_tof_quadratic = -1.54
experiment.linked_structures.create(structure_id='si', scale=600)
experiment.background.create(position=2000, intensity=120.0)
experiment.background.create(position=9035, intensity=120.0)
experiment.background.create(position=9335, intensity=120.0)
experiment.background.create(position=11915, intensity=120.0)
experiment.background.create(position=12315, intensity=120.0)
experiment.background.create(position=12695, intensity=120.0)
experiment.background.create(position=13745, intensity=120.0)
experiment.background.create(position=14410, intensity=120.0)
experiment.background.create(position=14875, intensity=120.0)
experiment.background.create(position=15660, intensity=120.0)
experiment.background.create(position=23075, intensity=120.0)
experiment.background.create(position=23515, intensity=120.0)
experiment.background.create(position=28100, intensity=120.0)
experiment.background.create(position=29995, intensity=120.0)

# %% [markdown]
# ## Estimate the background
#
# Start the background from an automatic estimate. The default method, arPLS, fits a smooth curve
# under the pattern that ignores the peaks, and places 14 points along it.

# %%
experiment.background.auto_estimate(n_points=14)

# %%
project.display.pattern('sepd')

# %% [markdown]
# ## Perform the analysis
#
# The fit follows diffraction-lib's four cycles for this case, then frees the background once more
# so it ends with the case's free set.

# %% [markdown]
# ### Cell, scale and time-of-flight calibration

# %%
structure.cell.length_a.free = True
experiment.linked_structures['si'].scale.free = True
experiment.instrument.calib_d_to_tof_offset.free = True

# %%
project.display.parameters.free()

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('sepd')

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
project.display.pattern('sepd')

# %% [markdown]
# ### Gaussian widths
#
# The background stays free while the widths join. diffraction-lib fixes it for this step and
# leaves it fixed; here the fit reaches the same result with it free, as every other case does.
# The Gaussian terms come first.

# %%
experiment.peak.broad_gauss_sigma_0.free = True
experiment.peak.broad_gauss_sigma_1.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('sepd')

# %% [markdown]
# ### Lorentzian width
#
# Then the Lorentzian term.

# %%
experiment.peak.broad_lorentz_gamma_1.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('sepd')

# %% [markdown]
# ### Displacement

# %%
structure.atom_sites['Si'].adp_iso.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('sepd')

# %% [markdown]
# ### Peak decay
#
# The back-to-back exponential decay terms β₀ and β₁.

# %%
experiment.peak.decay_beta_0.free = True
experiment.peak.decay_beta_1.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('sepd')

# %%
project.display.fit.correlations()

# %%
project.display.structure('si')

# %% [markdown]
# ## Report
#
# The HTML report draws the measured, calculated and difference patterns with the reflection
# positions, and lists the structures, the experiments and the fit. Open it in a browser.

# %%
project.report.save_html('pd-neut-tof_si-sepd.html')

# %% [markdown]
# ## Save the project

# %%
project.save_as('pd-neut-tof_si-sepd')
