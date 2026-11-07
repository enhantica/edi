"""Two-phase neutron refinement at 3 K."""

# %% [markdown]
# # Two-phase neutron refinement: YAlO₃ and Al₂O₃ at 3 K
#
# Refine both phases against the same constant-wavelength SPODI pattern.
# The starting model carries a shared peak profile, refined background points
# and a fixed absorption correction. See the supplied project provenance
# for the FullProf starting values and comparison.

# %%
import edi

project = edi.Project.load('../cli/pd-neut-cwl_yap-spodi_3k/project')
print('Phases:', ', '.join(structure.name for structure in project.structures))

# %% [markdown]
# ## Fit the pattern
#
# Inspect both phases and their reflection markers in the report. Use the
# difference plot to see where the fitted pattern still deviates from the data.

# %%
result = project.analysis.fit()
print(f'Rwp: {100 * result.rwp:.2f}%')
print(f'Reduced chi-square: {result.reduced_chi_square:.3f}')

# %% [markdown]
# ## Save the result and an interactive report

# %%
project.save_as('yap-spodi-refined')
project.report.save_html('yap-spodi-refinement.html', offline=True)
