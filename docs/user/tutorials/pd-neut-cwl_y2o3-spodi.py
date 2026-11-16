"""Rietveld fit: Y₂O₃, SPODI."""
# %% [markdown]
# # Rietveld fit: Y₂O₃, SPODI
#
# Fit cubic Y₂O₃ to constant-wavelength neutron powder data from SPODI at FRM II, with anisotropic
# displacement tensors whose components the site symmetry ties together.
#
# It builds the catalogue case `pd-neut-cwl_y2o3-spodi` step by step: the same project the command
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
project = edi.Project(name='pd-neut-cwl_y2o3-spodi')

# %% [markdown]
# ## Define the structure
#
# Load the structure from EasyDiffraction's collection. Its CIF gives the space group, the cell and
# the atom sites.

# %%
path = edi.download_data('pd-neut-cwl_y2o3-spodi-y2o3', destination='data')
project.structures.add_from_cif_path(path)
structure = project.structures['y2o3']

# %%
project.display.structure('y2o3')

# %% [markdown]
# ## Define the experiment
#
# Create the experiment from the measured data in EasyDiffraction's collection, then describe the
# instrument, the peak profile, the background and the structure it links.

# %%
data_path = edi.download_data('pd-neut-cwl_y2o3-spodi-spodi-data', destination='data')
project.experiments.add_from_data_path(
    name='spodi',
    data_path=data_path,
    sample_form='powder',
    beam_mode='constant wavelength',
    radiation_probe='neutron',
    scattering_type='bragg',
)
experiment = project.experiments['spodi']
experiment.neutron_scattering_length = 'sears1992'
experiment.peak.type = 'cwl-tch-pseudo-voigt'
experiment.instrument.name = 'SPODI'
experiment.instrument.facility = 'FRM II'
experiment.peak.broad_gauss_u = 0.04
experiment.peak.broad_gauss_v = -0.07
experiment.peak.broad_gauss_w = 0.1
experiment.instrument.setup_wavelength = 1.54822
experiment.excluded_regions.create(start=0, end=12)
experiment.excluded_regions.create(start=137.5, end=180)
experiment.linked_structures.create(structure_id='y2o3', scale=0.1)
experiment.background.create(position=12.5856, intensity=6400.0)
experiment.background.create(position=19.4181, intensity=6400.0)
experiment.background.create(position=21.8751, intensity=6400.0)
experiment.background.create(position=27.8998, intensity=6400.0)
experiment.background.create(position=32.9147, intensity=6400.0)
experiment.background.create(position=39.1152, intensity=6400.0)
experiment.background.create(position=45.712, intensity=6400.0)
experiment.background.create(position=51.9387, intensity=6400.0)
experiment.background.create(position=60.558, intensity=6400.0)
experiment.background.create(position=68.1982, intensity=6400.0)
experiment.background.create(position=81.3276, intensity=6400.0)
experiment.background.create(position=88.7996, intensity=6400.0)
experiment.background.create(position=94.3171, intensity=6400.0)
experiment.background.create(position=98.1541, intensity=6400.0)
experiment.background.create(position=100.9813, intensity=6400.0)
experiment.background.create(position=104.3134, intensity=6400.0)
experiment.background.create(position=108.7225, intensity=6400.0)
experiment.background.create(position=116.0673, intensity=6400.0)
experiment.background.create(position=121.4862, intensity=6400.0)
experiment.background.create(position=131.2805, intensity=6400.0)
experiment.background.create(position=135.7928, intensity=6400.0)

# %% [markdown]
# ## Estimate the background
#
# Start the background from an automatic estimate. The default method, arPLS, fits a smooth curve
# under the pattern that ignores the peaks, and places 21 points along it.

# %%
experiment.background.auto_estimate(n_points=21)

# %%
project.display.pattern('spodi')

# %% [markdown]
# ## Perform the analysis
#
# The fit goes in stages, freeing one group of parameters at a time.

# %% [markdown]
# ### Scale, 2θ zero and cell
#
# The scale, the zero shift and the cell length put the peaks in place and at the right height.

# %%
experiment.linked_structures['y2o3'].scale.free = True
experiment.instrument.calib_twotheta_offset.free = True
structure.cell.length_a.free = True

# %%
project.display.parameters.free()

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('spodi')

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
project.display.pattern('spodi')

# %% [markdown]
# ### Peak widths

# %%
experiment.peak.broad_gauss_u.free = True
experiment.peak.broad_gauss_v.free = True
experiment.peak.broad_gauss_w.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('spodi')

# %% [markdown]
# ### Atom positions
#
# Y1's x and O1's three coordinates are the ones the symmetry leaves free.

# %%
for site in structure.atom_sites:
    for coordinate in (site.fract_x, site.fract_y, site.fract_z):
        coordinate.free = not coordinate.symmetry_constrained

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('spodi')

# %% [markdown]
# ### Anisotropic displacements
#
# Last, the displacement tensors, each with only the components its site symmetry leaves free.

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
project.display.pattern('spodi')

# %%
project.display.fit.correlations()

# %%
project.display.structure('y2o3')

# %% [markdown]
# ## Report
#
# The HTML report draws the measured, calculated and difference patterns with the reflection
# positions, and lists the structures, the experiments and the fit. Open it in a browser.

# %%
project.report.save_html('pd-neut-cwl_y2o3-spodi.html')

# %% [markdown]
# ## Save the project

# %%
project.save_as('pd-neut-cwl_y2o3-spodi')
