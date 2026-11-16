"""Single-crystal fit: Tb₂Ti₂O₇, HEiDi."""
# %% [markdown]
# # Single-crystal fit: Tb₂Ti₂O₇, HEiDi
#
# Fit the pyrochlore Tb₂Ti₂O₇ to constant-wavelength neutron single-crystal data from HEiDi at
# MLZ, with anisotropic displacements and Becker-Coppens extinction.
#
# It builds the catalogue case `sc-neut-cwl_tb2ti2o7-heidi` step by step: the same project the
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
project = edi.Project(name='sc-neut-cwl_tb2ti2o7-heidi')

# %% [markdown]
# ## Define the structure
#
# Load the structure from EasyDiffraction's collection. Its CIF gives the space group, the cell and
# the atom sites.

# %%
path = edi.download_data('sc-neut-cwl_tb2ti2o7-heidi-tb2ti2o7', destination='data')
project.structures.add_from_cif_path(path)
structure = project.structures['tb2ti2o7']

# %%
project.display.structure('tb2ti2o7')

# %% [markdown]
# ## Define the experiment
#
# Create the experiment from the measured data in EasyDiffraction's collection, then describe the
# instrument, the peak profile, the background and the structure it links.

# %%
data_path = edi.download_data('sc-neut-cwl_tb2ti2o7-heidi-heidi-data', destination='data')
project.experiments.add_from_data_path(
    name='heidi',
    data_path=data_path,
    sample_form='single crystal',
    beam_mode='constant wavelength',
    radiation_probe='neutron',
    scattering_type='bragg',
)
experiment = project.experiments['heidi']
experiment.neutron_scattering_length = 'sears1992'
experiment.extinction.type = 'becker-coppens-mixed'
experiment.instrument.name = 'HEiDi'
experiment.instrument.facility = 'MLZ (FRM II)'
experiment.instrument.setup_wavelength = 0.793
experiment.extinction.domain_radius = 25
experiment.extinction.crystal_radius = 3
experiment.linked_structures.create(structure_id='tb2ti2o7', scale=4)

# %%
project.display.pattern('heidi')

# %% [markdown]
# ## Perform the analysis
#
# One new group per fit: the scale, O1's position, the displacement tensors, then the extinction.
# diffraction-lib also fits occupancies and isotropic displacements, which this case keeps fixed.

# %% [markdown]
# ### Scale
#
# The scale brings the calculated intensities to the measured ones.

# %%
experiment.linked_structures['tb2ti2o7'].scale.free = True

# %%
project.display.parameters.free()

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('heidi')

# %% [markdown]
# ### O1's position
#
# The one coordinate the symmetry leaves free.

# %%
structure.atom_sites['O1'].fract_x.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('heidi')

# %% [markdown]
# ### Anisotropic displacements

# %%
for tensor in structure.atom_site_aniso:
    for component in (
        tensor.adp_11,
        tensor.adp_22,
        tensor.adp_33,
        tensor.adp_12,
        tensor.adp_13,
        tensor.adp_23,
    ):
        component.free = not component.symmetry_constrained

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('heidi')

# %% [markdown]
# ### Extinction
#
# The domain radius and the mosaic spread.

# %%
experiment.extinction.domain_radius.free = True
experiment.extinction.mosaic_spread.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('heidi')

# %%
project.display.fit.correlations()

# %%
project.display.structure('tb2ti2o7')

# %% [markdown]
# ## Report
#
# The HTML report draws the measured, calculated and difference patterns with the reflection
# positions, and lists the structures, the experiments and the fit. Open it in a browser.

# %%
project.report.save_html('sc-neut-cwl_tb2ti2o7-heidi.html')

# %% [markdown]
# ## Save the project

# %%
project.save_as('sc-neut-cwl_tb2ti2o7-heidi')
