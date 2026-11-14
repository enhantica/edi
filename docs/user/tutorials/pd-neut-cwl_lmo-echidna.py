"""Rietveld fit: LiNiO₂, ECHIDNA."""
# %% [markdown]
# # Rietveld fit: LiNiO₂, ECHIDNA
#
# Fit the layered oxide LiNiO₂ to constant-wavelength neutron powder data from ECHIDNA at ANSTO.
# Li and Ni mix between two sites, held to full occupancy by constraints, and the profile has
# Finger-Cox-Jephcoat asymmetry.
#
# It builds the catalogue case `pd-neut-cwl_lmo-echidna` step by step: the same project the command
# line fits and the app's Examples open. Li and Ni share their sites through five relations
# (displacements and occupancies).

# %% [markdown]
# ## Import the library

# %%
import easydiffraction as edi

# %% [markdown]
# ## Define the project
#
# A new project is empty: it holds no structure and no experiment until you add them.

# %%
project = edi.Project(name='pd-neut-cwl_lmo-echidna')

# %% [markdown]
# ## Define the structure
#
# Load the structure from EasyDiffraction's collection. Its CIF gives the space group, the cell and
# the atom sites.

# %%
path = edi.download_data('pd-neut-cwl_lmo-echidna-lmo', destination='data')
project.structures.add_from_cif_path(path)
structure = project.structures['lmo']

# %%
project.display.structure('lmo')

# %% [markdown]
# ## Define the experiment
#
# Create the experiment from the measured data in EasyDiffraction's collection, then describe the
# instrument, the peak profile, the background and the structure it links.

# %%
data_path = edi.download_data('pd-neut-cwl_lmo-echidna-echidna-data', destination='data')
project.experiments.add_from_data_path(
    name='echidna',
    data_path=data_path,
    sample_form='powder',
    beam_mode='constant wavelength',
    radiation_probe='neutron',
    scattering_type='bragg',
)
experiment = project.experiments['echidna']
experiment.neutron_scattering_length = 'sears1992'
experiment.peak.type = 'cwl-tch-pseudo-voigt-fcj'
experiment.absorption.type = 'cylinder-hewat'
experiment.instrument.name = 'ECHIDNA'
experiment.instrument.facility = 'ANSTO'
experiment.peak.broad_gauss_u = 0.1
experiment.peak.broad_gauss_v = -0.3
experiment.peak.broad_gauss_w = 0.4
experiment.peak.broad_lorentz_y = 0.1
experiment.peak.asym_fcj_1 = 0.08
experiment.peak.asym_fcj_2 = 0.08
experiment.peak.cutoff_fwhm = 12
experiment.instrument.setup_wavelength = 1.6215
experiment.instrument.calib_sample_displacement = 0
experiment.instrument.calib_sample_transparency = 0
experiment.absorption.mu_r = 0.3
experiment.excluded_regions.create(start=0, end=12)
experiment.excluded_regions.create(start=162, end=180)
experiment.linked_structures.create(structure_id='lmo', scale=10)
experiment.background.create(position=12, intensity=550.0)
experiment.background.create(position=30, intensity=550.0)
experiment.background.create(position=50, intensity=550.0)
experiment.background.create(position=70, intensity=550.0)
experiment.background.create(position=90, intensity=550.0)
experiment.background.create(position=110, intensity=550.0)
experiment.background.create(position=130, intensity=550.0)
experiment.background.create(position=150, intensity=550.0)
experiment.background.create(position=162, intensity=550.0)

# %% [markdown]
# The constraints the fit keeps, each between two named parameters (aliases).

# %%
project.analysis.aliases.create(id='biso_Li1', param=structure.atom_sites['Li1'].adp_iso)
project.analysis.aliases.create(id='biso_Li2', param=structure.atom_sites['Li2'].adp_iso)
project.analysis.aliases.create(id='biso_Ni1', param=structure.atom_sites['Ni1'].adp_iso)
project.analysis.aliases.create(id='biso_Ni2', param=structure.atom_sites['Ni2'].adp_iso)
project.analysis.aliases.create(id='occ_Li1', param=structure.atom_sites['Li1'].occupancy)
project.analysis.aliases.create(id='occ_Li2', param=structure.atom_sites['Li2'].occupancy)
project.analysis.aliases.create(id='occ_Ni1', param=structure.atom_sites['Ni1'].occupancy)
project.analysis.aliases.create(id='occ_Ni2', param=structure.atom_sites['Ni2'].occupancy)
project.analysis.constraints.create(id='1', expression='biso_Ni1 = biso_Li1')
project.analysis.constraints.create(id='2', expression='biso_Li2 = biso_Ni2')
project.analysis.constraints.create(id='3', expression='occ_Ni1 = 1 - occ_Li1')
project.analysis.constraints.create(id='4', expression='occ_Li2 = 1 - occ_Li1')
project.analysis.constraints.create(id='5', expression='occ_Ni2 = occ_Li1')

# %%
project.display.constraints()

# %%
project.display.pattern('echidna')

# %% [markdown]
# ## Perform the analysis
#
# The fit goes in stages, freeing one group of parameters at a time.

# %% [markdown]
# ### Scale, 2θ zero and cell
#
# The scale, the zero shift and the two cell lengths put the peaks in place and at the right
# height.

# %%
experiment.linked_structures['lmo'].scale.free = True
experiment.instrument.calib_twotheta_offset.free = True
structure.cell.length_a.free = True
structure.cell.length_c.free = True

# %%
project.display.parameters.free()

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('echidna')

# %% [markdown]
# ### Sample displacement and transparency
#
# The sample sits a little off the diffractometer axis and the beam goes into it; both shift the
# peaks with angle, unlike the zero.

# %%
experiment.instrument.calib_sample_displacement.free = True
experiment.instrument.calib_sample_transparency.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('echidna')

# %% [markdown]
# ### Background
#
# The nine background points follow the level between the peaks.

# %%
for point in experiment.background:
    point.intensity.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('echidna')

# %% [markdown]
# ### Peak widths

# %%
experiment.peak.broad_gauss_u.free = True
experiment.peak.broad_gauss_v.free = True
experiment.peak.broad_gauss_w.free = True
experiment.peak.broad_lorentz_y.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('echidna')

# %% [markdown]
# ### Oxygen position
#
# O's height along c is the only coordinate the symmetry leaves free.

# %%
structure.atom_sites['O'].fract_z.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('echidna')

# %% [markdown]
# ### Displacements
#
# Li1's, Ni2's and O's; Ni1 and Li2 follow by the relations.

# %%
structure.atom_sites['Li1'].adp_iso.free = True
structure.atom_sites['Ni2'].adp_iso.free = True
structure.atom_sites['O'].adp_iso.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('echidna')

# %% [markdown]
# ### Li/Ni mixing
#
# Last, Li1's occupancy, which sets how much Ni sits on the Li site; it moves with the
# displacements, so it comes after them.

# %%
structure.atom_sites['Li1'].occupancy.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('echidna')

# %%
project.display.fit.correlations()

# %%
project.display.structure('lmo')

# %% [markdown]
# ## Report
#
# The HTML report draws the measured, calculated and difference patterns with the reflection
# positions, and lists the structures, the experiments and the fit. Open it in a browser.

# %%
project.report.save_html('pd-neut-cwl_lmo-echidna.html')

# %% [markdown]
# ## Save the project

# %%
project.save_as('pd-neut-cwl_lmo-echidna')
