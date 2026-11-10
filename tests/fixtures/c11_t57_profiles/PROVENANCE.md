#  independent profile references

`generate.py` reads diffraction-lib commit
`0d9f10e412a0cd08d4dd0af95845dd9bb597dcdf`; `manifest.json` names every original
FullProf file and its SHA-256. They are copied from committed git objects,
byte-identically. No gate runs FullProf. The `.edi` models are **authored
transcriptions** of the upstream pages' fixed parameters, not upstream files.

- `fcj/reference.tsv`: upstream's FullProf LaB6 FCJ PRF minus its BAC, using
  upstream's verification loader and its refined values, including S_L=D_L=0.08.
- `tof/reference.tsv`: upstream's FullProf Fe PRF minus its BAC; all parameters
  including scale remain at the upstream page's FullProf values.
- `beba/reference.tsv`: **cryspy 0.12.1**, executing the upstream PbSO4 page
  through its first unfitted `calculate()` only. Its FullProf files are a
  divergence record, never this comparison's numerical expectation. The loader
  supplies the grid, and cryspy supplies every expected intensity.

Reproduction uses diffraction-lib's locked Python environment and `generate.py
/path/to/diffraction-lib`. Neither crysta nor edi is imported by the generator.
The edi fixture subset is copied from this generator's `model.edi` and
`reference.tsv` outputs plus its manifest, for binding round-trip checks.

The native comparison bounds are declared **before implementation**: 1% relative
whole-vector L2 for fixed-parameter profiles; 0.5% relative column L2 for FCJ
central differences at steps 1e-5 and 5e-6. These are acceptance bounds, not
measured agreement claims or fitted tolerances. The new-kernel-off controls
must exceed the same bound. The BeBa zero limit requires exact equality.

Accident paths: a recognized token with no kernel; a selector ignored in favor of
parameter presence; asymmetric terms dropped; FullProf used as BeBa's oracle;
either FCJ derivative column dropped; profiles changed on save. The native and
edi hidden gates cover these seams. Numerical mutation controls cannot execute
past the named missing-capability guards until the kernels are implemented;
that later execution is required before claiming the escapes closed.

The 2026-09-26 owner direction supersedes the original BeBa page expectation:
all comparisons use AsyLim=180. `manifest.json` retains original upstream
`files` and separately records `comparison_files`, the authored FullProf
regeneration in crysta's `beba/fullprof180/` fixture. The source PCR changes
only AsyLim from 160 to 180; no gate runs fp2k. The BeBa page compares FullProf
only after a fit or through issue 166's map inferred from calculated output.
