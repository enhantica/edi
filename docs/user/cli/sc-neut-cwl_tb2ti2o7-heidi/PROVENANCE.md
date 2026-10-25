# sc-neut-cwl_tb2ti2o7-heidi — provenance

Fit the pyrochlore Tb₂Ti₂O₇ to constant-wavelength neutron single-crystal data from HEiDi at MLZ, with anisotropic displacements and Becker-Coppens extinction.

## Sources

- **Model:** diffraction-lib (develop `cb2cda7be6117199be8f8cac0a666a7bccd32d90`)'s verification page `sc-neut-cwl_tbti_anisotropic-adp` (FullProf `tbti.pcr`): the Fd-3m structure, its sites and the wavelength 0.793 Å. The tutorial `refine-tbti-heidi` fits the same data.
- **Data:** `data/tbti-heidi.xye`, dataset `meas-tbti-heidi` of the repository `easyscience/diffraction` at commit `3ec801667904578ea39f1a4f4aa941866543a669` (path `data/measured/tbti-heidi.xye`), licence BSD-3-Clause. The project embeds its 220 reflections unchanged (h, k, l, F², su). Its sha256 is `70f85294f87d9c658dd25f45f3162ac3cd567bc47e4291314cba1c19a2c02fe1`.

## Start

Built by `tools/cli_projects/build_sc_projects.py`: Uani on every site from an isotropic-equivalent 0.0026 Å², tied by site symmetry; O1 x moved off its refined value; isotropic Becker-Coppens extinction, mixed, with the crystal radius 3 mm, the domain radius free from 25 μm and the mosaic spread free from 0 (the owner, 2026-10-23); the scale 4. Free: the scale, O1 x, the eight independent tensor components, the domain radius and the mosaic spread (12 parameters).

## Differences from the source

- The tutorial refines isotropic displacements, occupancies and the radius first and the anisotropic tensors after; here the tensors are free from the start and the occupancies are fixed.
- The tutorial frees its one radius, crystal and domain at once, at a fixed mosaic spread; here the crystal radius describes the crystal (3 mm) and the domain radius and mosaic spread are free.

## Result from this start (local diagnostic)

From this start edi converges in 12 iterations to reduced χ² 1.33 over the 220 reflections (R(F²) 2.42 %), with the scale 5.899(35), the domain radius 3.0(18) μm and the mosaic spread 2732(93) rad⁻¹. FullProf 8.40 from the same start has no Becker-Coppens model and fits its own empirical extinction instead: 15 cycles to χ² 1.41, RF2w 2.98 %, the scale 6.00(4). The models differ, so its values are a comparison, not a reference.
