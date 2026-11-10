"""Rietveld fit: Si, SEPD."""
# %% [markdown]
# # Rietveld fit: Si, SEPD
#
# Fit silicon to time-of-flight neutron powder data from SEPD at Argonne, with the Jorgensen-Von
# Dreele profile.
#
# The project is the catalogue case `pd-neut-tof_si-sepd`, the one the command line and the app's
# Examples open.

# %%
import easydiffraction as edi

# %% [markdown]
# ## Load the project

# %%
project_path = edi.download_data('pd-neut-tof_si-sepd', destination='data')
project = edi.Project.load(project_path)
structure = project.structures['si']
experiment = project.experiments['sepd']

# %% [markdown]
# The project marks what its fit frees. The fit below frees it in stages, so start with all of it
# fixed.

# %%
for parameter in project.free_parameters:
    parameter.free = False

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
# ## Save the project

# %%
project.save_as('pd-neut-tof_si-sepd')
project.report.save_html('pd-neut-tof_si-sepd.html')

# %% [markdown]
# ## Your own measured data
#
# Measured data can also come from a file on your own disk. `add_from_data_path` reads a file of
# time-of-flight, intensity and uncertainty columns into a new experiment, here in a project of its
# own; the experiment then needs its instrument, profile and linked structure, as above. The file
# here is SEPD's pattern from the collection, saved to disk first.

# %%
data_path = edi.download_data('pd-neut-tof_si-sepd-sepd-data', destination='data')
own = edi.Project(name='own_sepd')
own.experiments.add_from_data_path(
    name='mine',
    data_path=data_path,
    sample_form='powder',
    beam_mode='time-of-flight',
    radiation_probe='neutron',
)
own.display.pattern('mine')
