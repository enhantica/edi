"""Calculation without data: La₀.₅Ba₀.₅CoO₃, HRPT."""
# %% [markdown]
# # Calculation without data: La₀.₅Ba₀.₅CoO₃, HRPT
#
# Calculate a constant-wavelength neutron pattern of the cubic perovskite La₀.₅Ba₀.₅CoO₃ without
# any measured data. The structure, the HRPT instrument, the peak profile and the background are in
# the project, and edi calculates the pattern over the project's 2θ range.
#
# It builds the catalogue case `pd-neut-cwl_lbco_simulation` step by step: the same project the
# command line calculates and the app's Examples open.

# %% [markdown]
# ## Import the library

# %%
import easydiffraction as edi

# %% [markdown]
# ## Define the project
#
# A new project is empty: it holds no structure and no experiment until you add them.

# %%
project = edi.Project(name='pd-neut-cwl_lbco_simulation')

# %% [markdown]
# ## Define the structure
#
# Load the structure from EasyDiffraction's collection. Its CIF gives the space group, the cell and
# the atom sites.

# %%
path = edi.download_data('pd-neut-cwl_lbco_simulation-lbco', destination='data')
project.structures.add_from_cif_path(path)
structure = project.structures['lbco']

# %%
project.display.structure('lbco')

# %% [markdown]
# ## Define the experiment
#
# Create the experiment, then describe the instrument, the peak profile, the range to calculate and
# the structure it links. It has no measured data; the calculation gives the pattern.

# %%
project.experiments.create(
    name='hrpt',
    sample_form='powder',
    beam_mode='constant wavelength',
    radiation_probe='neutron',
    scattering_type='bragg',
)
experiment = project.experiments['hrpt']
experiment.peak.type = 'cwl-tch-pseudo-voigt'
experiment.instrument.name = 'HRPT'
experiment.instrument.facility = 'PSI'
experiment.instrument.setup_wavelength = 1.494
experiment.peak.broad_gauss_u = 0.1
experiment.peak.broad_gauss_v = -0.1
experiment.peak.broad_gauss_w = 0.1
experiment.peak.broad_lorentz_y = 0.1
experiment.peak.cutoff_fwhm = 30
experiment.data_range.two_theta_min = 10
experiment.data_range.two_theta_max = 160
experiment.data_range.two_theta_inc = 0.05
experiment.linked_structures.create(structure_id='lbco', scale=10.0)
experiment.background.create(position=10, intensity=20)
experiment.background.create(position=160, intensity=20)

# %% [markdown]
# ## Perform the calculation
#
# There is nothing to fit: edi calculates the pattern from the model as it is.

# %%
project.calculate()
pattern = project.experiments[0].data
print(len(pattern.intensity_calc), 'points, highest', round(max(pattern.intensity_calc), 1))

# %% [markdown]
# ## Report
#
# The HTML report draws the measured, calculated and difference patterns with the reflection
# positions, and lists the structure and the fit. Open it in a browser.

# %%
project.report.save_html('pd-neut-cwl_lbco_simulation.html')

# %% [markdown]
# ## Save the project
#
# `save_as` writes the project to a folder of its own.

# %%
project.save_as('pd-neut-cwl_lbco_simulation')
