"""Single-crystal fit: Pr₂NiO₄, 5C2."""
# %% [markdown]
# # Single-crystal fit: Pr₂NiO₄, 5C2
#
# Fit the layered nickelate Pr₂NiO₄ to constant-wavelength neutron single-crystal data from 5C2 at
# LLB, with anisotropic displacements.
#
# It builds the catalogue case `sc-neut-cwl_pr2nio4-5c2` step by step: the same project the command
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
project = edi.Project(name='sc-neut-cwl_pr2nio4-5c2')

# %% [markdown]
# ## Define the structure
#
# Load the structure from EasyDiffraction's collection. Its CIF gives the space group, the cell and
# the atom sites.

# %%
path = edi.download_data('sc-neut-cwl_pr2nio4-5c2-pr2nio4', destination='data')
project.structures.add_from_cif_path(path)
structure = project.structures['pr2nio4']

# %%
project.display.structure('pr2nio4')

# %% [markdown]
# ## Define the experiment
#
# Create the experiment from the measured data in EasyDiffraction's collection, then describe the
# instrument, the peak profile, the background and the structure it links.

# %%
data_path = edi.download_data('sc-neut-cwl_pr2nio4-5c2-llb_5c2-data', destination='data')
project.experiments.add_from_data_path(
    name='llb_5c2',
    data_path=data_path,
    sample_form='single crystal',
    beam_mode='constant wavelength',
    radiation_probe='neutron',
    scattering_type='bragg',
)
experiment = project.experiments['llb_5c2']
experiment.neutron_scattering_length = 'sears1992'
experiment.instrument.name = '5C2'
experiment.instrument.facility = 'LLB'
experiment.instrument.setup_wavelength = 0.8302
experiment.linked_structures.create(structure_id='pr2nio4', scale=4)

# %%
project.display.pattern('llb_5c2')

# %% [markdown]
# ## Perform the analysis
#
# A single crystal has no background or profile: the stages are the scale, the positions, the
# interstitial oxygen's displacement, then the displacement tensors.

# %% [markdown]
# ### Scale
#
# The scale brings the calculated intensities to the measured ones.

# %%
experiment.linked_structures['pr2nio4'].scale.free = True

# %%
project.display.parameters.free()

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('llb_5c2')

# %% [markdown]
# ### Positions
#
# The coordinates each site's symmetry leaves free.

# %%
for site in structure.atom_sites:
    for coordinate in (site.fract_x, site.fract_y, site.fract_z):
        coordinate.free = not coordinate.symmetry_constrained

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('llb_5c2')

# %% [markdown]
# ### The interstitial displacement
#
# The isotropic displacement of the interstitial oxygen Od.

# %%
structure.atom_sites['Od'].adp_iso.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('llb_5c2')

# %% [markdown]
# ### Anisotropic displacements
#
# Last, the tensors, each with the components its site symmetry leaves free.

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
project.display.pattern('llb_5c2')

# %%
project.display.fit.correlations()

# %%
project.display.structure('pr2nio4')

# %% [markdown]
# ## Report
#
# The HTML report draws the measured, calculated and difference patterns with the reflection
# positions, and lists the structures, the experiments and the fit. Open it in a browser.

# %%
project.report.save_html('sc-neut-cwl_pr2nio4-5c2.html')

# %% [markdown]
# ## Save the project

# %%
project.save_as('sc-neut-cwl_pr2nio4-5c2')
