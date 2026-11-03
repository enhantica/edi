# pd-neut-tof_ncaf-wish-2bank_start-3 — provenance

crysta fitting case `ncaf-wish-2bank-s3` under the CLI project id rule.

Copied **byte-identical** from crysta `origin/main` at `973b34bd92f01ba77f89b049a3e7e74d252b9db3`, path
`tests/fitting/ncaf-wish-2bank-s3/` — the `project/` tree and `expected.json`, nothing else.

| object | git id at the source |
| --- | --- |
| `tests/fitting/ncaf-wish-2bank-s3` (tree) | `d03de17833aace7dd6a3a129d0ac0fdd9964211e` |
| `tests/fitting/ncaf-wish-2bank-s3/project` (tree) | `b3b2f079ad096b1869870e7192031d151d6263fe` |
| `tests/fitting/ncaf-wish-2bank-s3/expected.json` (blob) | `1de8ff7784d549e092d7f2643243935596269ca0` |

**One declared change since the copy.** `project/analysis/analysis.edi` gains one line,
`_minimizer.chi_square_tolerance 1e-4`. crysta's corpus manifest pinned `ncaf-wish-2bank-s3` under
`--chi-square-tolerance 1e-4`, and made the tolerance a project setting. Every other file,
and `expected.json`, is still byte-identical to the source, except the regression pins re-taken below.

The expected values keep the `kind` their source gave them: crysta-produced fit outputs are
**regression pins** — they gate drift, not correctness — and only values marked `reference` come
from outside every engine under test. The source case's own `PROVENANCE.md` in crysta says which
is which and why.

**Minimizer declared.** diffraction-lib's
`_minimizer.type "lmfit (leastsq)"` became `_minimizer.type crysta` here and in the crysta source case
in the same change, because edi supports only crysta and warns on any other value. The tolerance line above remains the only other difference from the source, whose new
content ids are `tests/fitting/ncaf-wish-2bank-s3` (tree) `14ac76932ab6034726611a6afe54a6b29e28bb18` and `tests/fitting/ncaf-wish-2bank-s3/project` (tree)
`82cad6508c2ec6761a3150768b46ace4ecc51634`; `expected.json` did not change.

**Excluded rows rewritten ([ADR-0044](../../../dev/adrs/0044-pattern-charts-and-excluded-regions.md)).** Each excluded `_data` row now has the d-spacing computed from the
file's own instrument, written like the file's other d values, and `.` for `intensity_calc` and `intensity_bkg`
instead of `0.`. Included rows are unchanged, and the recorded hashes of these files moved with them.

## Pins re-taken with crysta build-3fcc7925

crysta build-3fcc7925 adds the tails of time-of-flight reflections centred just outside the measured range, and
resumes a descent whose final polish shows it had not converged. Both move this fit, so its regression pins were
re-taken from `python -m edi fit` with that build. Reference values are unchanged.

| run | quantity | before | after |
| --- | --- | --- | --- |
| ladder | `reduced_chi_square` | 15.69263995 | 15.69270178 |
| ladder | `rwp` | 0.08189529811 | 0.08189545944 |
| fast-descent-linear-snap | `reduced_chi_square` | 15.69263662 | 15.69269845 |
| fast-descent-linear-snap | `rwp` | 0.08189528941 | 0.08189545075 |
