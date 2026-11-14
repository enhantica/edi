"""Single-crystal fit: taurine, SENJU."""
# %% [markdown]
# # Single-crystal fit: taurine, SENJU
#
# Fit the amino-sulfonic acid taurine to six time-of-flight neutron single-crystal datasets from
# SENJU at J-PARC together, each reflection measured at its own wavelength.
#
# It builds the catalogue case `sc-neut-tof_taurine-senju` step by step: the same project the
# command line fits and the app's Examples open. Banks 2 to 6 share bank 1's three extinction
# terms.

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
project = edi.Project(name='sc-neut-tof_taurine-senju')
project.analysis.fitting_mode = 'joint'

# %% [markdown]
# ## Define the structure
#
# Load the structure from EasyDiffraction's collection. Its CIF gives the space group, the cell and
# the atom sites.

# %%
path = edi.download_data('sc-neut-tof_taurine-senju-taurine', destination='data')
project.structures.add_from_cif_path(path)
structure = project.structures['taurine']

# %%
project.display.structure('taurine')

# %% [markdown]
# ## Define the experiments
#
# Create the six experiments from their measured data in EasyDiffraction's collection, then
# describe each one's instrument, peak profile, background and the structures it links.

# %%
data_path = edi.download_data('sc-neut-tof_taurine-senju-senju_1-data', destination='data')
project.experiments.add_from_data_path(
    name='senju_1',
    data_path=data_path,
    sample_form='single crystal',
    beam_mode='time-of-flight',
    radiation_probe='neutron',
    scattering_type='bragg',
)
senju_1 = project.experiments['senju_1']
senju_1.neutron_scattering_length = 'sears1992'
senju_1.extinction.type = 'larson-anisotropic'
senju_1.instrument.name = 'SENJU'
senju_1.instrument.facility = 'J-PARC'
senju_1.linked_structures.create(structure_id='taurine', scale=2.762)

# %%
data_path = edi.download_data('sc-neut-tof_taurine-senju-senju_2-data', destination='data')
project.experiments.add_from_data_path(
    name='senju_2',
    data_path=data_path,
    sample_form='single crystal',
    beam_mode='time-of-flight',
    radiation_probe='neutron',
    scattering_type='bragg',
)
senju_2 = project.experiments['senju_2']
senju_2.neutron_scattering_length = 'sears1992'
senju_2.extinction.type = 'larson-anisotropic'
senju_2.instrument.name = 'SENJU'
senju_2.instrument.facility = 'J-PARC'
senju_2.linked_structures.create(structure_id='taurine', scale=3.829)

# %%
data_path = edi.download_data('sc-neut-tof_taurine-senju-senju_3-data', destination='data')
project.experiments.add_from_data_path(
    name='senju_3',
    data_path=data_path,
    sample_form='single crystal',
    beam_mode='time-of-flight',
    radiation_probe='neutron',
    scattering_type='bragg',
)
senju_3 = project.experiments['senju_3']
senju_3.neutron_scattering_length = 'sears1992'
senju_3.extinction.type = 'larson-anisotropic'
senju_3.instrument.name = 'SENJU'
senju_3.instrument.facility = 'J-PARC'
senju_3.linked_structures.create(structure_id='taurine', scale=3.211)

# %%
data_path = edi.download_data('sc-neut-tof_taurine-senju-senju_4-data', destination='data')
project.experiments.add_from_data_path(
    name='senju_4',
    data_path=data_path,
    sample_form='single crystal',
    beam_mode='time-of-flight',
    radiation_probe='neutron',
    scattering_type='bragg',
)
senju_4 = project.experiments['senju_4']
senju_4.neutron_scattering_length = 'sears1992'
senju_4.extinction.type = 'larson-anisotropic'
senju_4.instrument.name = 'SENJU'
senju_4.instrument.facility = 'J-PARC'
senju_4.linked_structures.create(structure_id='taurine', scale=2.809)

# %%
data_path = edi.download_data('sc-neut-tof_taurine-senju-senju_5-data', destination='data')
project.experiments.add_from_data_path(
    name='senju_5',
    data_path=data_path,
    sample_form='single crystal',
    beam_mode='time-of-flight',
    radiation_probe='neutron',
    scattering_type='bragg',
)
senju_5 = project.experiments['senju_5']
senju_5.neutron_scattering_length = 'sears1992'
senju_5.extinction.type = 'larson-anisotropic'
senju_5.instrument.name = 'SENJU'
senju_5.instrument.facility = 'J-PARC'
senju_5.linked_structures.create(structure_id='taurine', scale=2.739)

# %%
data_path = edi.download_data('sc-neut-tof_taurine-senju-senju_6-data', destination='data')
project.experiments.add_from_data_path(
    name='senju_6',
    data_path=data_path,
    sample_form='single crystal',
    beam_mode='time-of-flight',
    radiation_probe='neutron',
    scattering_type='bragg',
)
senju_6 = project.experiments['senju_6']
senju_6.neutron_scattering_length = 'sears1992'
senju_6.extinction.type = 'larson-anisotropic'
senju_6.instrument.name = 'SENJU'
senju_6.instrument.facility = 'J-PARC'
senju_6.linked_structures.create(structure_id='taurine', scale=2.936)

# %% [markdown]
# The constraints the fit keeps, each between two named parameters (aliases).

# %%
project.analysis.aliases.create(id='x11_1', param=senju_1.extinction.coefficient_11)
project.analysis.aliases.create(id='x22_1', param=senju_1.extinction.coefficient_22)
project.analysis.aliases.create(id='x33_1', param=senju_1.extinction.coefficient_33)
project.analysis.aliases.create(id='x11_2', param=senju_2.extinction.coefficient_11)
project.analysis.aliases.create(id='x22_2', param=senju_2.extinction.coefficient_22)
project.analysis.aliases.create(id='x33_2', param=senju_2.extinction.coefficient_33)
project.analysis.aliases.create(id='x11_3', param=senju_3.extinction.coefficient_11)
project.analysis.aliases.create(id='x22_3', param=senju_3.extinction.coefficient_22)
project.analysis.aliases.create(id='x33_3', param=senju_3.extinction.coefficient_33)
project.analysis.aliases.create(id='x11_4', param=senju_4.extinction.coefficient_11)
project.analysis.aliases.create(id='x22_4', param=senju_4.extinction.coefficient_22)
project.analysis.aliases.create(id='x33_4', param=senju_4.extinction.coefficient_33)
project.analysis.aliases.create(id='x11_5', param=senju_5.extinction.coefficient_11)
project.analysis.aliases.create(id='x22_5', param=senju_5.extinction.coefficient_22)
project.analysis.aliases.create(id='x33_5', param=senju_5.extinction.coefficient_33)
project.analysis.aliases.create(id='x11_6', param=senju_6.extinction.coefficient_11)
project.analysis.aliases.create(id='x22_6', param=senju_6.extinction.coefficient_22)
project.analysis.aliases.create(id='x33_6', param=senju_6.extinction.coefficient_33)
project.analysis.constraints.create(id='x11_2', expression='x11_2 = x11_1')
project.analysis.constraints.create(id='x22_2', expression='x22_2 = x22_1')
project.analysis.constraints.create(id='x33_2', expression='x33_2 = x33_1')
project.analysis.constraints.create(id='x11_3', expression='x11_3 = x11_1')
project.analysis.constraints.create(id='x22_3', expression='x22_3 = x22_1')
project.analysis.constraints.create(id='x33_3', expression='x33_3 = x33_1')
project.analysis.constraints.create(id='x11_4', expression='x11_4 = x11_1')
project.analysis.constraints.create(id='x22_4', expression='x22_4 = x22_1')
project.analysis.constraints.create(id='x33_4', expression='x33_4 = x33_1')
project.analysis.constraints.create(id='x11_5', expression='x11_5 = x11_1')
project.analysis.constraints.create(id='x22_5', expression='x22_5 = x22_1')
project.analysis.constraints.create(id='x33_5', expression='x33_5 = x33_1')
project.analysis.constraints.create(id='x11_6', expression='x11_6 = x11_1')
project.analysis.constraints.create(id='x22_6', expression='x22_6 = x22_1')
project.analysis.constraints.create(id='x33_6', expression='x33_6 = x33_1')

# %%
project.display.constraints()

# %%
project.display.pattern('senju_1')

# %% [markdown]
# ## Perform the analysis
#
# The fit follows diffraction-lib's change of model for this case: isotropic displacements first,
# then anisotropic tensors. diffraction-lib does not fit the positions, which this case does, so
# they get a stage of their own.

# %% [markdown]
# ### Scales, every site isotropic
#
# Each bank's scale, with every site's displacement isotropic for now.

# %%
for site in structure.atom_sites:
    site.adp_type = 'Biso'
for experiment in project.experiments:
    experiment.linked_structures['taurine'].scale.free = True

# %%
project.display.parameters.free()

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('senju_1')

# %% [markdown]
# ### Isotropic displacements
#
# Every site's isotropic displacement.

# %%
for site in structure.atom_sites:
    site.adp_iso.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('senju_1')

# %% [markdown]
# ### Extinction
#
# Bank 1's three extinction terms, which the other banks share.

# %%
senju_1.extinction.coefficient_11.free = True
senju_1.extinction.coefficient_22.free = True
senju_1.extinction.coefficient_33.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('senju_1')

# %% [markdown]
# ### Positions
#
# All fourteen sites' coordinates.

# %%
for site in structure.atom_sites:
    site.fract_x.free = True
    site.fract_y.free = True
    site.fract_z.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('senju_1')

# %% [markdown]
# ### Anisotropic displacements
#
# Back to anisotropic displacements (edi converts the values), with every tensor component free.

# %%
for site in structure.atom_sites:
    site.adp_type = 'beta'
for tensor in structure.atom_site_aniso:
    tensor.adp_11.free = True
    tensor.adp_22.free = True
    tensor.adp_33.free = True
    tensor.adp_12.free = True
    tensor.adp_13.free = True
    tensor.adp_23.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('senju_1')

# %%
project.display.fit.correlations()

# %%
project.display.structure('taurine')

# %% [markdown]
# ## Report
#
# The HTML report draws the measured, calculated and difference patterns with the reflection
# positions, and lists the structures, the experiments and the fit. Open it in a browser.

# %%
project.report.save_html('sc-neut-tof_taurine-senju.html')

# %% [markdown]
# ## Save the project

# %%
project.save_as('sc-neut-tof_taurine-senju')
