"""Fit Co2SiO4 measured on D20, with its structure and data from the collection."""
# %% [markdown]
# # Co₂SiO₄ on D20
#
# This tutorial fits the olivine Co₂SiO₄ to constant-wavelength neutron powder data measured on
# D20 at the ILL. Its structure and its measured pattern come from EasyDiffraction's collection;
# the tutorial describes the experiment, links the two and fits the coordinates, the
# displacements and the oxygen occupancies.

# %% [markdown]
# ## Import the library

# %%
import easydiffraction as edi

# %% [markdown]
# ## Define the project

# %%
project = edi.Project(name='cosio_d20')

# %% [markdown]
# ## Define the structure
#
# Load the structure from the collection. The CIF gives the space group P n m a, the cell and the
# six sites, and marks the cell, coordinates, displacements and oxygen occupancies to fit. The fit
# below frees them in stages, so start with all of them fixed.

# %%
structure_path = edi.download_data('pd-neut-cwl_cosio-d20-cosio', destination='data')
project.structures.add_from_cif_path(structure_path)
structure = project.structures['cosio']
for parameter in project.free_parameters:
    parameter.free = False

# %%
project.display.structure('cosio')

# %% [markdown]
# ## Define the experiment
#
# The measured pattern also comes from the collection.

# %%
data_path = edi.download_data('pd-neut-cwl_cosio-d20-d20-data', destination='data')
project.experiments.add_from_data_path(
    name='d20',
    data_path=data_path,
    sample_form='powder',
    beam_mode='constant wavelength',
    radiation_probe='neutron',
    scattering_type='bragg',
)
experiment = project.experiments['d20']

# %% [markdown]
# D20's wavelength is 1.87 Å. The profile is the Thompson-Cox-Hastings pseudo-Voigt, and a flat
# background runs through fourteen points.

# %%
experiment.instrument.setup_wavelength = 1.87
experiment.instrument.calib_twotheta_offset = 0
experiment.peak.broad_gauss_u = 0.2
experiment.peak.broad_gauss_v = -0.5
experiment.peak.broad_gauss_w = 0.4
experiment.peak.broad_lorentz_y = 0.01
for position in (8, 9, 10, 11, 12, 15, 25, 30, 50, 70, 90, 110, 130, 150):
    experiment.background.create(position=position, intensity=340)
experiment.linked_structures.create(structure_id='cosio', scale=1)

# %%
project.display.pattern('d20')

# %% [markdown]
# ## Perform the analysis
#
# The fit goes in stages, freeing one group of parameters at a time.
#
# ### Scale, 2θ zero and cell
#
# The scale sets the overall height of the pattern, and the zero shift and the three cell lengths
# put the peaks where they are measured.

# %%
experiment.linked_structures['cosio'].scale.free = True
experiment.instrument.calib_twotheta_offset.free = True
structure.cell.length_a.free = True
structure.cell.length_b.free = True
structure.cell.length_c.free = True

# %%
project.display.parameters.free()

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('d20')

# %% [markdown]
# ### Background
#
# With the peaks in place, the fourteen background points follow the level between them.

# %%
for point in experiment.background:
    point.intensity.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('d20')

# %% [markdown]
# ### Peak widths
#
# The profile terms now fit the widths and shapes of the peaks. diffraction-lib's tutorial also
# fits a peak asymmetry; this case's profile has none.

# %%
experiment.peak.broad_gauss_u.free = True
experiment.peak.broad_gauss_v.free = True
experiment.peak.broad_gauss_w.free = True
experiment.peak.broad_lorentz_y.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('d20')

# %% [markdown]
# ### Atom positions
#
# The peak intensities now depend mostly on where the atoms are. Co1 sits on a centre of
# symmetry and the other sites on the mirror plane, so only their free coordinates are fitted.

# %%
for site in structure.atom_sites:
    for coordinate in (site.fract_x, site.fract_y, site.fract_z):
        coordinate.free = not coordinate.symmetry_constrained

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('d20')

# %% [markdown]
# ### Displacements
#
# The displacements change the intensities more at high angle.

# %%
for site in structure.atom_sites:
    site.adp_iso.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('d20')

# %%
project.display.fit.correlations()

# %% [markdown]
# ### Constrain the two Co sites
#
# The correlations show no strong pair for the two Co sites, yet the fit gives them very different
# displacements, Co1's even negative, which no atom can have: both are Co and scatter alike, so
# the pattern cannot tell their thermal motions apart. Give each an alias and constrain Co2's to
# follow Co1's, starting again from 0.5 Å², then fit again; the shared displacement is positive and
# its s.u. smaller than either had alone.

# %%
structure.atom_sites['Co2'].adp_iso.free = False
structure.atom_sites['Co1'].adp_iso = 0.5
project.analysis.aliases.create(id='biso_Co1', param=structure.atom_sites['Co1'].adp_iso)
project.analysis.aliases.create(id='biso_Co2', param=structure.atom_sites['Co2'].adp_iso)
project.analysis.constraints.create(id='biso_Co2', expression='biso_Co2 = biso_Co1')
project.display.constraints()

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('d20')

# %% [markdown]
# ### Oxygen occupancies
#
# Last, the oxygen occupancies, which change the intensities as the displacements do.

# %%
structure.atom_sites['O1'].occupancy.free = True
structure.atom_sites['O2'].occupancy.free = True
structure.atom_sites['O3'].occupancy.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('d20')

# %%
project.display.pattern('d20', x_min=40, x_max=60)

# %%
project.display.fit.correlations()

# %%
project.display.structure('cosio')

# %% [markdown]
# ## Save the project

# %%
project.save_as('cosio_d20')
