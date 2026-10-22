# pd-neut-cwl_lbco-hrpt_calculation — provenance

A calculated constant-wavelength neutron pattern of La0.5Ba0.5CoO3, with no measured data: the model and an instrument
are enough for edi to calculate the pattern, and changing a value shows its effect at once.

The structure is diffraction-lib's dataset `struct-lbco` (`structures/lbco.cif` in the data repository
`easyscience/diffraction` at commit `3ec801667904578ea39f1a4f4aa941866543a669`, BSD-3-Clause, sha256
`a8a8970e26c4a932098d73502f720bc2092ea6585bc527c5c35c531a8b05d9ae`): Pm-3m, a = 3.88 Å, La and Ba sharing the
origin at half occupancy, Biso 0.5 on every site. The instrument, profile, background, range (10 to 160° in steps of
0.05°) and scale are those of diffraction-lib's tutorial `simulate-lbco-cwl` (develop `cb2cda7b`). The project is the
tutorial's state before it changes the cell, the O displacement and the Lorentzian width to show their effect; those
changes are left to the user.

`project/` is built by `tools/cli_projects/build_catalogue_projects.py`.
