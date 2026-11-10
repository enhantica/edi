"""Single-crystal fit: Co₂SiO₄ at three temperatures, HEiDi."""
# %% [markdown]
# # Single-crystal fit: Co₂SiO₄ at three temperatures, HEiDi
#
# Fit one Co₂SiO₄ crystal measured on HEiDi at MLZ at 300 K, 55 K and 2.5 K. Each temperature has
# its own structure and its own reflections, and the three are fitted independently: each fit sees
# only its own data and gives its own goodness of fit and uncertainties. At 2.5 K the cobalt
# moments order, and the magnetic structure is fitted too.
#
# The data are those of Sazonov et al., Acta Cryst. B 64 (2008) 661-668. The 2.5 K file has no
# usable uncertainties, so they are estimated from the 55 K data of the same crystal (see the
# case's provenance); the fitted 2.5 K uncertainties depend on that estimate.

# %% [markdown]
# ## Import the library

# %%
import easydiffraction as edi

# %% [markdown]
# ## Define the project
#
# The independent fitting mode fits each experiment on its own, against the structure it links.

# %%
project = edi.Project(name='cosio_heidi')
project.analysis.fitting_mode = 'independent'

# %% [markdown]
# ## Define the structures
#
# Load the three structures from EasyDiffraction's collection, one per temperature. Each starts
# from the published positions with a small displacement tensor on every site. The 2.5 K structure
# also carries the magnetic space group Pnma.1 and the moment directions it allows, Co1 in any
# direction and Co2 along b, with every moment at zero. The files mark what the fit frees; the fit
# below frees it in stages, so start with all of it fixed.

# %%
path = edi.download_data('sc-neut-cwl_cosio-heidi-cosio_300k', destination='data')
project.structures.add_from_cif_path(path)
path = edi.download_data('sc-neut-cwl_cosio-heidi-cosio_55k', destination='data')
project.structures.add_from_cif_path(path)
path = edi.download_data('sc-neut-cwl_cosio-heidi-cosio_2k5', destination='data')
project.structures.add_from_cif_path(path)
for parameter in project.free_parameters:
    parameter.free = False

# %%
project.display.structure('cosio_2k5')

# %% [markdown]
# ## Define the experiments
#
# Load the reflections of each temperature and link each dataset to its structure. HEiDi's
# wavelength is 0.552 Å; the extinction is FullProf's anisotropic Larson model, with its six
# coefficients starting at zero.

# %%
data_paths = {
    '300k': edi.download_data('sc-neut-cwl_cosio-heidi-heidi_300k-data', destination='data'),
    '55k': edi.download_data('sc-neut-cwl_cosio-heidi-heidi_55k-data', destination='data'),
    '2k5': edi.download_data('sc-neut-cwl_cosio-heidi-heidi_2k5-data', destination='data'),
}
for temperature, path in data_paths.items():
    project.experiments.add_from_data_path(
        name=f'heidi_{temperature}',
        data_path=path,
        sample_form='single crystal',
        beam_mode='constant wavelength',
        radiation_probe='neutron',
        scattering_type='bragg',
    )
    experiment = project.experiments[f'heidi_{temperature}']
    experiment.instrument.setup_wavelength = 0.552
    experiment.extinction.type = 'larson-anisotropic'
    experiment.linked_structures.create(structure_id=f'cosio_{temperature}', scale=10)

# %% [markdown]
# Names for the three structures and experiments.

# %%
structure_300k = project.structures['cosio_300k']
structure_55k = project.structures['cosio_55k']
structure_2k5 = project.structures['cosio_2k5']
experiment_300k = project.experiments['heidi_300k']
experiment_55k = project.experiments['heidi_55k']
experiment_2k5 = project.experiments['heidi_2k5']

# %% [markdown]
# ## Perform the analysis
#
# An experiment with nothing free is left out of a fit, so the first stages fit 300 K alone. Each
# stage frees one new group: the structure's coordinates and displacement components are the ones
# its site symmetry leaves free.
#
# The 300 K reflections against the starting model:

# %%
project.display.pattern('heidi_300k')

# %% [markdown]
# ### 300 K: scale
#
# The scale brings the calculated intensities to the measured ones.

# %%
experiment_300k.linked_structures['cosio_300k'].scale.free = True

# %%
project.display.parameters.free()

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('heidi_300k')

# %% [markdown]
# ### 300 K: coordinates

# %%
for site in structure_300k.atom_sites:
    for coordinate in (site.fract_x, site.fract_y, site.fract_z):
        coordinate.free = not coordinate.symmetry_constrained

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('heidi_300k')

# %% [markdown]
# ### 300 K: displacements

# %%
for tensor in structure_300k.atom_site_aniso:
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
project.display.pattern('heidi_300k')

# %% [markdown]
# ### 300 K: extinction
#
# Larson's anisotropic extinction, its six coefficients starting at zero.

# %%
experiment_300k.extinction.coefficient_11.free = True
experiment_300k.extinction.coefficient_22.free = True
experiment_300k.extinction.coefficient_33.free = True
experiment_300k.extinction.coefficient_12.free = True
experiment_300k.extinction.coefficient_13.free = True
experiment_300k.extinction.coefficient_23.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('heidi_300k')

# %% [markdown]
# ### 55 K: scale
#
# The 300 K parameters stay free, so the 300 K experiment is fitted again from where it ended.

# %%
experiment_55k.linked_structures['cosio_55k'].scale.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('heidi_55k')

# %% [markdown]
# ### 55 K: coordinates

# %%
for site in structure_55k.atom_sites:
    for coordinate in (site.fract_x, site.fract_y, site.fract_z):
        coordinate.free = not coordinate.symmetry_constrained

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('heidi_55k')

# %% [markdown]
# ### 55 K: extinction
#
# At 55 K the displacements are small. Freed before the extinction, they would take its place and
# Co1's tensor would stop being positive definite, so the extinction comes before them here.

# %%
experiment_55k.extinction.coefficient_11.free = True
experiment_55k.extinction.coefficient_22.free = True
experiment_55k.extinction.coefficient_33.free = True
experiment_55k.extinction.coefficient_12.free = True
experiment_55k.extinction.coefficient_13.free = True
experiment_55k.extinction.coefficient_23.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('heidi_55k')

# %% [markdown]
# ### 55 K: displacements

# %%
for tensor in structure_55k.atom_site_aniso:
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
project.display.pattern('heidi_55k')

# %% [markdown]
# ### 2.5 K: scale
#
# The nuclear structure first, with every moment still at zero, in the order 55 K needed.

# %%
experiment_2k5.linked_structures['cosio_2k5'].scale.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('heidi_2k5')

# %% [markdown]
# ### 2.5 K: coordinates

# %%
for site in structure_2k5.atom_sites:
    for coordinate in (site.fract_x, site.fract_y, site.fract_z):
        coordinate.free = not coordinate.symmetry_constrained

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('heidi_2k5')

# %% [markdown]
# ### 2.5 K: extinction

# %%
experiment_2k5.extinction.coefficient_11.free = True
experiment_2k5.extinction.coefficient_22.free = True
experiment_2k5.extinction.coefficient_33.free = True
experiment_2k5.extinction.coefficient_12.free = True
experiment_2k5.extinction.coefficient_13.free = True
experiment_2k5.extinction.coefficient_23.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('heidi_2k5')

# %% [markdown]
# ### 2.5 K: displacements

# %%
for tensor in structure_2k5.atom_site_aniso:
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

# %% [markdown]
# Some reflections stay far from their measured intensity: (1 0 0), (0 0 1) and (1 1 0) among
# them. Pnma forbids them for nuclear scattering, so with the moments at zero their calculated
# intensity is zero; at 2.5 K they are magnetic.

# %%
project.display.pattern('heidi_2k5')

# %% [markdown]
# ### 2.5 K: the magnetic moments
#
# Free the moment components the magnetic space group allows. They start at zero, where the
# magnetic intensity has no slope, so the fit starts them at 1 μB and says so.

# %%
structure_2k5.atom_site_moment['Co1'].crystalaxis_x.free = True
structure_2k5.atom_site_moment['Co1'].crystalaxis_y.free = True
structure_2k5.atom_site_moment['Co1'].crystalaxis_z.free = True
structure_2k5.atom_site_moment['Co2'].crystalaxis_y.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('heidi_2k5')

# %% [markdown]
# Sazonov et al., Acta Cryst. B 65 (2009) 664-675, Table 4, give Co1 (1.20(3), 3.64(2), 0.57(9))
# μB and Co2 3.35(2) μB along b. The fitted moments' uncertainties rest on the estimated 2.5 K
# uncertainties.

# %%
project.display.structure('cosio_2k5')

# %% [markdown]
# ## Save the project

# %%
project.save_as('sc-neut-cwl_cosio-heidi')
project.report.save_html('sc-neut-cwl_cosio-heidi.html')
