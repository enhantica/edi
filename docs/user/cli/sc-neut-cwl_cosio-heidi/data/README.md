# Co₂SiO₄ on HEiDi: the reflection files

One Co₂SiO₄ crystal measured on HEiDi (MLZ) at λ = 0.552 Å, from the supplementary files of Sazonov et al., Acta
Cryst. B 64 (2008) 661–668. Each file is a CIF `_refln` loop with h, k, l, FullProf's F²calc, F²meas, σ(F²meas) and
the observed status.

| File | Temperature | Reflections | σ |
| --- | --- | --- | --- |
| `heidi_300k.hkl` | 300 K | 1624 | as published |
| `heidi_55k.hkl` | 55 K | 1465 | as published |
| `heidi_2k5.hkl` | 2.5 K | 1424 | **estimated** |

**The 2.5 K uncertainties are estimated.** The published 2.5 K file holds 2θ in its σ column, so its σ are estimated
from the 55 K data of the same crystal, instrument and setting: a reflection measured at 55 K takes the 55 K relative
error, never below the 55 K absolute σ, and one measured at or below zero there takes that absolute σ; one measured only at 300 K takes the 300 K values the same way; any other,
mostly the magnetic reflections, takes the larger of F² times the median relative error of the 25 reflections of
nearest intensity and their median σ. F²meas and F²calc are as published. `tools/data/estimate_cosio_heidi_su.py`
writes the file, and `PROVENANCE.md` gives the details and checksums.
