# Measured single-crystal fits

These fitting references are separate from `../fullprof`, the unchanged
fixed verification inputs. `generate_page_fits.py` copies those PCRs, sets
Pcr=2 and Mat=1, allows 50 cycles with Eps=0.001, and frees scale. The
extinction case also frees FullProf's empirical Ext1. Its input data bytes
are unchanged. Each case ran FullProf 8.40 once, on 2026-10-22. The original
PCR, fitted NEW, OUT, SUM and INT are retained. `fullprof.json` identifies
the binary, input and output hashes. Tests never run FullProf.

The five pages at diffraction-lib
`cb2cda7be6117199be8f8cac0a666a7bccd32d90` free only scale, except the
extinction page, which frees scale and radius with mosaicity fixed at 35000.
No page frees coordinates or ADPs. `page-contract.json` records the source
paths, hashes and free assignments. The pages fit synthetic FullProf F²;
these twins fit the measured INT observations as requested. The fixed PCR
structure is retained, including its printed precision. Initial scales
equal the pages' initial scales.

| Project | Fitted scale ± s.u. | FullProf χ²/N | Free set |
| --- | ---: | ---: | --- |
| sc-neut-cwl_pr2nio4-5c2_basic | 4.0089931 ± 0.013560562 | 10.75 | scale |
| sc-neut-cwl_tb2ti2o7-heidi_basic | 3.2802625 ± 0.053695116 | 84.80 | scale |
| sc-neut-cwl_tb2ti2o7-heidi_anisotropic-adp | 4.5774188 ± 0.036426339 | 20.93 | scale |
| sc-neut-cwl_tb2ti2o7-heidi_isotropic-extinction | 3.4961121 ± 0.10108743 | 81.94 | scale, empirical Ext1 |
| sc-neut-tof_taurine-unknown_basic | 2.6886642 ± 0.025837142 | 24.28 | scale |

Values above are transcribed from each OUT's final parameter list and NEW's
chi-square header. The scale-only objectives are strictly convex quadratics
with nonzero intensity vectors: each has one identifiable parameter. For
the empirical extinction fit, Ext1=0.64837033 ± 0.28055459 and the OUT reports
a scale–Ext1 correlation of 83%. It converged with finite uncertainties,
but Ext1 is weakly constrained. This does not measure the conditioning of
a Becker–Coppens radius/mosaicity fit.

**The extinction fit is diagnostic, not a parameter-equivalent oracle.**
The page itself says its Becker–Coppens model differs from FullProf's.
FullProf model 1 has no radius or mosaicity parameter. No mapping or radius
s.u. is invented. The candidate project frees radius and keeps mosaicity
fixed, exactly as the page does. Its common scale/chi-square comparison may
fail because the models differ. `comparable_parameters=false` preserves
this limitation; a passing common-quantity comparison would still not
establish the missing radius-within-s.u. requirement. The page never frees
radius and mosaicity together, so the reported near-degeneracy in the app's
different fitting example does not alter this page's free set.

The taurine verification source names no instrument. `unknown` is explicit;
the separate SENJU tutorial is not evidence that these INT bytes are SENJU
data. Replace this label only when the dataset's provenance establishes it.

FullProf selects 171 of taurine's 286 observations using its existing
I>3σ rule. The candidate project contains that exact selected subset for
the FullProf comparison. The original INT and the older all-observation
reader/weighted-fit gates retain every observation. The other cases use
all their observations (198 for Pr and 220 for each Tb case).

FullProf's reported statistic is sum(r²)/N. `fullprof.json` also contains
sum(r²) recomputed from the printed F² table and original INT uncertainties,
and the explicit N−p conversion for `reduced_chi_square`. No crysta or edi
output supplies these values. The expected scale bound is one FullProf
s.u. plus half a printed SUM digit; chi-square bounds are 0.06 absolute
and 0.2% relative, admitting FullProf's printed precision and the existing
forward-model numerical budget. A model discrepancy is never absorbed
by enlarging these bounds.

Reproduce only when intentionally replacing references:

```sh
python tests/fixtures/single_crystal/generate_page_fits.py \
  --fp2k /path/to/fullprof/fp2k --run-dir /persistent/new-directory \
  --upstream /path/to/diffraction-lib
```

The generator sends `basename`, a blank response and `n` to fp2k, and
requires exit zero plus convergence. `--reuse-output` re-extracts retained
outputs without executing fp2k. Existing outputs refuse an implicit rerun.
