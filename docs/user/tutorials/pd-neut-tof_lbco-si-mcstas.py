"""Two-phase fit: La₀.₅Ba₀.₅CoO₃ and Si, McStas."""
# %% [markdown]
# # Two-phase fit: La₀.₅Ba₀.₅CoO₃ and Si, McStas
#
# Fit two phases, La₀.₅Ba₀.₅CoO₃ and silicon, to a time-of-flight pattern simulated with McStas.
#
# It builds the catalogue case `pd-neut-tof_lbco-si-mcstas` step by step: the same project the
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
project = edi.Project(name='pd-neut-tof_lbco-si-mcstas')

# %% [markdown]
# ## Define the structures
#
# Load the two structures from EasyDiffraction's collection. Each CIF gives its space group, cell
# and atom sites.

# %%
path = edi.download_data('pd-neut-tof_lbco-si-mcstas-lbco', destination='data')
project.structures.add_from_cif_path(path)
path = edi.download_data('pd-neut-tof_lbco-si-mcstas-si', destination='data')
project.structures.add_from_cif_path(path)
lbco = project.structures['lbco']
si = project.structures['si']

# %%
project.display.structure('lbco')

# %% [markdown]
# ## Define the experiment
#
# Create the experiment from the measured data in EasyDiffraction's collection, then describe the
# instrument, the peak profile, the background and the structure it links.

# %%
data_path = edi.download_data('pd-neut-tof_lbco-si-mcstas-mcstas-data', destination='data')
project.experiments.add_from_data_path(
    name='mcstas',
    data_path=data_path,
    sample_form='powder',
    beam_mode='time-of-flight',
    radiation_probe='neutron',
    scattering_type='bragg',
)
experiment = project.experiments['mcstas']
experiment.neutron_scattering_length = 'sears1992'
experiment.peak.type = 'tof-jorgensen'
experiment.instrument.name = 'McStas'
experiment.peak.broad_gauss_sigma_0 = 50000
experiment.peak.broad_gauss_sigma_1 = -50000
experiment.peak.broad_gauss_sigma_2 = 20000
experiment.peak.rise_alpha_1 = 0.01
experiment.peak.decay_beta_0 = 0.006
experiment.peak.decay_beta_1 = 0.004
experiment.peak.cutoff_fwhm = 30
experiment.instrument.setup_twotheta_bank = 94.90931761529106
experiment.instrument.calib_d_to_tof_linear = 58724.76869981215
experiment.excluded_regions.create(start=0, end=40000)
experiment.excluded_regions.create(start=108000, end=200000)
experiment.linked_structures.create(structure_id='lbco', scale=4)
experiment.linked_structures.create(structure_id='si', scale=0.2)
experiment.background.create(position=45000, intensity=0.23)
experiment.background.create(position=50000, intensity=0.23)
experiment.background.create(position=55000, intensity=0.23)
experiment.background.create(position=65000, intensity=0.23)
experiment.background.create(position=70000, intensity=0.23)
experiment.background.create(position=75000, intensity=0.23)
experiment.background.create(position=80000, intensity=0.23)
experiment.background.create(position=85000, intensity=0.23)
experiment.background.create(position=90000, intensity=0.23)
experiment.background.create(position=95000, intensity=0.23)
experiment.background.create(position=100000, intensity=0.23)
experiment.background.create(position=105000, intensity=0.23)
experiment.background.create(position=110000, intensity=0.23)

# %%
project.display.pattern('mcstas')

# %% [markdown]
# ## Perform the analysis
#
# The fit goes in stages, freeing one group of parameters at a time.

# %% [markdown]
# ### Scales and cells
#
# Both phases' scales and cells put the peaks in place and at the right height; the DIFC stays
# fixed, as in diffraction-lib's tutorial.

# %%
experiment.linked_structures['lbco'].scale.free = True
experiment.linked_structures['si'].scale.free = True
lbco.cell.length_a.free = True
si.cell.length_a.free = True

# %%
project.display.parameters.free()

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('mcstas')

# %% [markdown]
# ### Background

# %%
for point in experiment.background:
    point.intensity.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('mcstas')

# %% [markdown]
# ### Peak widths

# %%
experiment.peak.broad_gauss_sigma_0.free = True
experiment.peak.broad_gauss_sigma_1.free = True
experiment.peak.broad_gauss_sigma_2.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('mcstas')

# %% [markdown]
# ### Rise and decay

# %%
experiment.peak.rise_alpha_1.free = True
experiment.peak.decay_beta_0.free = True
experiment.peak.decay_beta_1.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('mcstas')

# %% [markdown]
# ### Displacements
#
# Co's and O's; La's, Ba's and Si's stay fixed, as the case's project keeps them.

# %%
lbco.atom_sites['Co'].adp_iso.free = True
lbco.atom_sites['O'].adp_iso.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('mcstas')

# %%
project.display.fit.correlations()

# %%
project.display.structure('lbco')

# %%
project.display.structure('si')

# %% [markdown]
# ## Report
#
# The HTML report draws the measured, calculated and difference patterns with the reflection
# positions, and lists the structures, the experiments and the fit. Open it in a browser.

# %%
project.report.save_html('pd-neut-tof_lbco-si-mcstas.html')

# %% [markdown]
# ## Save the project

# %%
project.save_as('pd-neut-tof_lbco-si-mcstas')
