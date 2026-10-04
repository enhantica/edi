# FullProf fitting projects

The **fitting** home: FullProf projects with some parameters free and `Pcr = 2`, each committed at its
converged state with the run that reached it (`full-fit.out`, its exact input `full-fit.inp`); a project whose
occupancies did not change keeps its source bytes. The layout, the naming rule, the occupancy
convention and the matched-pair rule are stated once, in
[`knowledge/verification/fullprof/PROVENANCE.md`](../../verification/fullprof/PROVENANCE.md); each folder's
own `PROVENANCE.md` records its origin, its occupancy table, its old and new scale, and its evidence
block. Every project here has a verification twin under the same id in the verification home.

| id | what it fits | origin |
| --- | --- | --- |
| `pd-neut-cwl_lab6-11b-echidna_tch-fcj` | LaB6 (11B), TCH (x) FCJ, CW | owner-authored fit (edi #74) |
| `pd-neut-cwl_yap-spodi_3k` | YAlO3 + Al2O3, two phases, CW | owner-supplied (first proposed as edi PR #75) |
| `pd-neut-tof_cecoal-polaris_chebyshev` | CeCoAl3, Chebyshev background, TOF | FullProf `Examples/` |
| `pd-neut-tof_ceo2-pearl_polynomial` | CeO2, polynomial background, TOF, data as plain X-Y-sigma | FullProf `Examples/` |
| `pd-neut-tof_si-sepd_ikeda-carpenter` | Si, Ikeda-Carpenter (x) pseudo-Voigt, TOF | built from FullProf `Examples/arg_si` |
