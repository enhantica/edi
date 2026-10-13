# `pd-xray-cwl_lif_doublet-absorption-polarization` -- FullProf verification project

**Authored**, not inherited: the input of diffraction-lib's `pd-xray-cwl_lif` set `lif_doublet_unpolarized` (pin `0d9f10e4`, its `.dat` byte-identical, the `.pcr` vendored in `pd-xray-cwl_lif_doublet/`) with three values changed on the powder line: `Cthm` 0.8, `muR` 0.9 and `Rpolarz` 0.5, and the title and file-name comment lines. It combines the Cu Kα doublet (`Lambda1 = 1.540560`, `Lambda2 = 1.544400`, `Ratio = 0.5`), the monochromator polarization and the cylinder absorption in one pattern, the data of the CLI project `pd-xray-cwl_lif_single`. No verification page reads it.

Every parameter is fixed (a forward calculation: the `.pcr` declares zero free parameters). For characteristic radiation (`Ilo = 0`) FullProf multiplies the Lorentz factor by `1 + Cthm cos²(2θ)` and does not read `Rpolarz` (manual section 3.4); edi's equivalent is `K = 0.5`, `2θ_m = acos(√0.8)` at twice the `.pcr` scale. FullProf rewrote the `.pcr` after the run (its chi-square comment, and `2nd-muR` set to `muR`); the committed `.pcr` is the rewritten one, the input of the committed outputs.

**FullProf version.** FullProf.2k **8.40** (Feb2026-ILL JRC), run once on 2026-10-13: `printf 'lif_doublet_absorption_polarized\n\n' | fp2k`. The run reaches FullProf's normal end; the executable then aborts on end of input at its "another problem?" prompt, as the committed `author-run/fp2k.log` shows. Result line: `=> Rp:  99.5     Rwp:  99.6     Rexp:    5.25 Chi2:  360.` — the "observed" data are a dummy pattern, so only the calculated profile is a reference.

## Occupancy convention

As `pd-xray-cwl_lif_single`: `F m -3 m`, Li1 (4a) and F1 (4b), `.pcr` Occ 0.02083 = 4 / 192, site occupancy 1 (k = 1).

## Files (sha256)

- `lif_doublet_absorption_polarized.bac` `20c658b6127310533a5fb83b92262fd431d75496aac202c4fb35b96cc96395bb`
- `lif_doublet_absorption_polarized.dat` `06ba190e26656de021c199beef857cdf61acf5e05ca62564cb325d40d9628cae`
- `lif_doublet_absorption_polarized.pcr` `eba311d13d95dbbf18fe44867f392a7b24c52b5868af6d724f8cfda5c5a35084`
- `lif_doublet_absorption_polarized.prf` `5c53788b3377533d6b18e5876d59b740b2f13a747a5c1197ceb3b29a1860fa90`
- `lif_doublet_absorption_polarized.sum` `3dbd8eee3b63177c1314689df329691072dc2ee9689d1949d54ee47758f194e0`
