# pd-neut-tof_si-sepd_start-2 — provenance

crysta fitting case `si-sepd-s2` under the CLI project id rule.

Copied **byte-identical** from crysta `origin/main` at `973b34bd92f01ba77f89b049a3e7e74d252b9db3`, path
`tests/fitting/si-sepd-s2/` — the `project/` tree and `expected.json`, nothing else.

| object | git id at the source |
| --- | --- |
| `tests/fitting/si-sepd-s2` (tree) | `f72bdb449ba3b05041b60b3b61cfc34a580f6d73` |
| `tests/fitting/si-sepd-s2/project` (tree) | `a453375780f0138cef36570f984f8fc591f81e20` |
| `tests/fitting/si-sepd-s2/expected.json` (blob) | `3e3576d2d3bb25d5793090b5e5ff7766e3cdde0d` |

**One declared change since the copy.** `project/analysis/analysis.edi` gains one line,
`_minimizer.chi_square_tolerance 1e-4`. crysta's corpus manifest pinned `si-sepd-s2` under
`--chi-square-tolerance 1e-4`, and made the tolerance a project setting. Every other file,
and `expected.json`, is still byte-identical to the source, except the regression pins re-taken below.

The expected values keep the `kind` their source gave them: crysta-produced fit outputs are
**regression pins** — they gate drift, not correctness — and only values marked `reference` come
from outside every engine under test. The source case's own `PROVENANCE.md` in crysta says which
is which and why.

**Minimizer declared.** diffraction-lib's
`_minimizer.type "lmfit (leastsq)"` became `_minimizer.type crysta` here and in the crysta source case
in the same change, because edi supports only crysta and warns on any other value. The tolerance line above remains the only other difference from the source, whose new
content ids are `tests/fitting/si-sepd-s2` (tree) `a56117862c0f80fe6437ebdb28fcddc0c3bf767f` and `tests/fitting/si-sepd-s2/project` (tree)
`f2e32a4a61ea291e75f052d439ce547ebd6c9ef2`; `expected.json` did not change.

## Pins re-taken with crysta build-3fcc7925

crysta build-3fcc7925 adds the tails of time-of-flight reflections centred just outside the measured range, and
resumes a descent whose final polish shows it had not converged. Both move this fit, so its regression pins were
re-taken from `python -m edi fit` with that build. Reference values are unchanged.

| run | quantity | before | after |
| --- | --- | --- | --- |
| ladder | `reduced_chi_square` | 3.611120606 | 3.610947358 |
| ladder | `rwp` | 0.06941177283 | 0.06941010775 |
| fast-descent | `reduced_chi_square` | 3.611114586 | 3.610941859 |
| fast-descent | `rwp` | 0.06941171497 | 0.06941005489 |
