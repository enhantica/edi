"""Fit La0.5Ba0.5CoO3 measured on HRPT, building the structure by hand."""
# %% [markdown]
# # La₀.₅Ba₀.₅CoO₃ on HRPT
#
# This tutorial fits the cubic perovskite La₀.₅Ba₀.₅CoO₃ to constant-wavelength neutron powder data
# measured on HRPT at PSI. It builds the structure by hand, loads the measured pattern from
# EasyDiffraction's collection, describes the experiment, links the two and fits them, showing the
# pattern and the parameters after each step. The other tutorials load their structures from a CIF.

# %% [markdown]
# ## Import the library

# %%
import easydiffraction as edi

# %% [markdown]
# ## Define the project
#
# A new project is empty: it holds no structure and no experiment until you add them.

# %%
project = edi.Project(name='lbco_hrpt')

# %% [markdown]
# ## Define the structure
#
# La and Ba share the corner site of the cubic cell, Co sits at its centre and O on the face
# centres, in space group P m -3 m. Every atom starts with an isotropic displacement of 0.5 Å².

# %%
project.structures.create(name='lbco')
structure = project.structures['lbco']
structure.space_group.name_h_m = 'P m -3 m'
structure.cell.length_a = 3.88

# %%
structure.atom_sites.create(
    id='La', type_symbol='La', fract_x=0, fract_y=0, fract_z=0, wyckoff_letter='a',
    occupancy=0.5, adp_iso=0.5,
)
structure.atom_sites.create(
    id='Ba', type_symbol='Ba', fract_x=0, fract_y=0, fract_z=0, wyckoff_letter='a',
    occupancy=0.5, adp_iso=0.5,
)
structure.atom_sites.create(
    id='Co', type_symbol='Co', fract_x=0.5, fract_y=0.5, fract_z=0.5, wyckoff_letter='b',
    adp_iso=0.5,
)
structure.atom_sites.create(
    id='O', type_symbol='O', fract_x=0, fract_y=0.5, fract_z=0.5, wyckoff_letter='c',
    adp_iso=0.5,
)

# %%
project.display.structure('lbco')

# %% [markdown]
# ## Define the experiment
#
# The measured pattern comes from EasyDiffraction's collection: 2θ, the counts and their standard
# uncertainties.

# %%
data_path = edi.download_data('pd-neut-cwl_lbco-hrpt-hrpt-data', destination='data')
project.experiments.add_from_data_path(
    name='hrpt',
    data_path=data_path,
    sample_form='powder',
    beam_mode='constant wavelength',
    radiation_probe='neutron',
    scattering_type='bragg',
)
experiment = project.experiments['hrpt']

# %% [markdown]
# HRPT's wavelength is 1.494 Å. The 2θ zero starts at 0.3°: from 0 the low-angle peaks sit more
# than a peak width away and the fit settles in a wrong minimum. The profile is the
# Thompson-Cox-Hastings pseudo-Voigt, its terms to one significant figure.

# %%
experiment.instrument.setup_wavelength = 1.494
experiment.instrument.calib_twotheta_offset = 0.3
experiment.peak.broad_gauss_u = 0.08
experiment.peak.broad_gauss_v = -0.1
experiment.peak.broad_gauss_w = 0.1
experiment.peak.broad_lorentz_y = 0.08

# %% [markdown]
# A flat background of five points, and the two ends of the pattern left out of the fit.

# %%
for position in (10, 30, 50, 110, 165):
    experiment.background.create(position=position, intensity=160)
experiment.excluded_regions.create(start=0, end=5)
experiment.excluded_regions.create(start=165, end=180)

# %% [markdown]
# The experiment shows the structure it links, here `lbco` with a scale of 9.

# %%
experiment.linked_structures.create(structure_id='lbco', scale=9)

# %%
project.display.pattern('hrpt')

# %% [markdown]
# ## Perform the analysis
#
# The fit goes in stages, freeing one group of parameters at a time, so each stage starts close to
# its answer.
#
# ### Scale, 2θ zero and cell
#
# The scale sets the overall height of the pattern, and the zero shift and the cell length put the
# peaks where they are measured, so they come first.

# %%
experiment.linked_structures['lbco'].scale.free = True
experiment.instrument.calib_twotheta_offset.free = True
structure.cell.length_a.free = True

# %%
project.display.parameters.free()

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('hrpt')

# %% [markdown]
# ### Background
#
# With the peaks in place, the five background points follow the level between them.

# %%
for point in experiment.background:
    point.intensity.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('hrpt')

# %% [markdown]
# ### Peak widths
#
# The profile terms now fit the widths and shapes of the peaks.

# %%
experiment.peak.broad_gauss_u.free = True
experiment.peak.broad_gauss_v.free = True
experiment.peak.broad_gauss_w.free = True
experiment.peak.broad_lorentz_y.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('hrpt')

# %% [markdown]
# ### Displacements
#
# Every atom sits on a special position of P m -3 m, so there are no coordinates to fit. The
# displacements change the peak intensities with angle and come last.

# %%
structure.atom_sites['La'].adp_iso.free = True
structure.atom_sites['Ba'].adp_iso.free = True
structure.atom_sites['Co'].adp_iso.free = True
structure.atom_sites['O'].adp_iso.free = True

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('hrpt')

# %%
project.display.fit.correlations()

# %% [markdown]
# ### Constrain La and Ba
#
# The correlations show the displacements of La and Ba moving together almost exactly, with
# opposite signs: they share one site and scatter neutrons similarly, so the pattern cannot tell
# them apart, and their s.u. are large. Give each an alias and constrain Ba's to follow La's, then
# fit again. Ba's displacement is no longer fitted on its own.

# %%
structure.atom_sites['Ba'].adp_iso.free = False
project.analysis.aliases.create(id='biso_La', param=structure.atom_sites['La'].adp_iso)
project.analysis.aliases.create(id='biso_Ba', param=structure.atom_sites['Ba'].adp_iso)
project.analysis.constraints.create(id='biso_Ba', expression='biso_Ba = biso_La')
project.display.constraints()

# %%
project.analysis.fit()
project.display.fit.results()

# %%
project.display.pattern('hrpt')

# %%
project.display.pattern('hrpt', x_min=38, x_max=41)

# %% [markdown]
# The pair of La and Ba has gone from the correlations, and La's displacement now has a small s.u.

# %%
project.display.fit.correlations()

# %% [markdown]
# ## Save the project
#
# Save the fitted project, and its report as one HTML file that opens without a network
# connection.

# %%
project.save_as('lbco_hrpt')
project.report.save_html('lbco_hrpt-report.html', offline=True)
