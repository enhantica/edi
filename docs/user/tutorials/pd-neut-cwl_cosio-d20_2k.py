"""Magnetic structure fit: Co₂SiO₄ at 2.3 K, D20."""
# %% [markdown]
# # Magnetic structure fit: Co₂SiO₄ at 2.3 K, D20
#
# Fit the magnetic structure of the olivine Co₂SiO₄ to constant-wavelength neutron powder data
# from D20 at ILL, measured at 2.3 K, below its ordering temperature. The cobalt moments order with
# k = 0 in the magnetic space group Pnma.1: Co1 may point in any direction, Co2 only along b.
#
# The project is the catalogue case `pd-neut-cwl_cosio-d20_2k`: the files the command line fits
# with `python -m edi fit docs/user/cli/pd-neut-cwl_cosio-d20_2k/project` and the app opens from
# its Examples.

# %% [markdown]
# > This tutorial is not run when the documentation is built yet. It loads its project from the edi
# > repository, so it runs once a tutorial runner can provide the project elsewhere
# > (`execution-exclusions.yml`).

# %%
import edi

# %% [markdown]
# ## Load the project

# %%
project = edi.Project.load('../cli/pd-neut-cwl_cosio-d20_2k/project')
print(project.metadata.title)
print('Structures:', ', '.join(structure.name for structure in project.structures))
print('Experiments:', ', '.join(experiment.name for experiment in project.experiments))

# %% [markdown]
# ## The moments
#
# Each magnetic site has one row: its moment's components along the cell axes, in Bohr
# magnetons, and the symmetry form the site's symmetry allows. Components the form fixes at zero
# cannot be freed.

# %%
for moment in project.structures['cosio'].atom_site_moment:
    print(moment.id, moment.symmform, moment.crystalaxis_x.value, moment.crystalaxis_y.value,
          moment.crystalaxis_z.value)

# %% [markdown]
# ## Fit
#
# The four allowed components are free, with the cell, the coordinates and the profile.

# %%
result = project.analysis.fit()
print(f'{result.status.name.lower()} after {result.iterations} iterations')
print(f'reduced chi-square {result.reduced_chi_square:.3f}, Rwp {100 * result.rwp:.2f} %')

# %% [markdown]
# ## Fitted moments
#
# Co1's component along c is barely determined by powder data: its uncertainty is as large as the
# value.

# %%
for label, value in result.values.items():
    if 'crystalaxis' in label:
        print(f'{label:40} {value:8.3f} ± {result.uncertainty.get(label, 0):.2g}')

# %% [markdown]
# ## Report and save
#
# The HTML report draws the patterns, and `save_as` writes the fitted project to a folder of its
# own; the catalogue's copy stays as it was.

# %%
project.report.save_html('pd-neut-cwl_cosio-d20_2k.html')
project.save_as('pd-neut-cwl_cosio-d20_2k')
