# sc-neut-cwl_pr2nio4-5c2 — provenance

Fit the layered nickelate Pr₂NiO₄ to constant-wavelength neutron single-crystal data from 5C2 at LLB, with anisotropic displacements.

## Sources

- **Model:** FullProf Suite's example `prnio.pcr` (Pr₂NiO₄+δ, SXTAL), as diffraction-lib (develop `cb2cda7be6117199be8f8cac0a666a7bccd32d90`) reads it on its verification page `sc-neut-cwl_pr2nio4_basic`: the Fmmm structure, its sites, occupancies and the wavelength 0.8302 Å.
- **Data:** `data/prnio.int`, the reflections of FullProf Suite's example `prnio.int` as diffraction-lib (develop `cb2cda7be6117199be8f8cac0a666a7bccd32d90`) commits them (`docs/docs/verification/fullprof/sc-neut-cwl_pr2nio4_basic/prnio.int`, licence BSD-3-Clause). The project embeds its reflections unchanged (h, k, l, F², su). Its sha256 is `f88f9d39b820852d6ccd589d822eca864db4fb59af82bd7506ffe730ebd24735`.

## Start

Built by `tools/cli_projects/build_sc_projects.py`: Bani on every site but Od, every independent component from 0 (with B12 on O1, whose site allows it), and Biso 0 on Od, all free (the owner, 2026-10-23); the free coordinates moved off their refined values (Pr z 0.362, O2 z 0.176, Od 0.075, 0.075, 0.175); no extinction (type None); the scale 4. Free: the scale, 17 displacement components and the free coordinates (23 parameters).

## Differences from the source

- FullProf's example refines anisotropic β tensors with its empirical extinction model left at zero; here the tensors are Bani, which is the same model in Å², and there is no extinction.

## Result from this start (local diagnostic)

From this start edi converges in 11 iterations to reduced χ² 9.75 over the 198 reflections, with the scale 4.022(28). FullProf 8.40 from the same start, with β tensors, converges in 14 cycles to χ² 9.69 and the scale 4.022(28) on this occupancy scale; all 23 values agree within 0.01 of edi's s.u.
