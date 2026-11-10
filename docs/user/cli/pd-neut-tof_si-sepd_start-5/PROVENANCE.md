# pd-neut-tof_si-sepd_start-5 — provenance

crysta fitting case `si-sepd-s5` under the CLI project id rule.

Copied **byte-identical** from crysta `origin/main` at `973b34bd92f01ba77f89b049a3e7e74d252b9db3`, path
`tests/fitting/si-sepd-s5/` — the `project/` tree and `expected.json`, nothing else.

| object | git id at the source |
| --- | --- |
| `tests/fitting/si-sepd-s5` (tree) | `97046e0210dc9d0ded2d9462b7bfc1bf3786b128` |
| `tests/fitting/si-sepd-s5/project` (tree) | `ae44af83e70dd957f0e5ef7755e817f5d29b22d0` |
| `tests/fitting/si-sepd-s5/expected.json` (blob) | `f4218ce9146d05cdd3461210af2513d4ed95eb04` |

**One declared change since the copy.** `project/analysis/analysis.edi` gains one line,
`_minimizer.chi_square_tolerance 1e-4`. crysta's corpus manifest pinned `si-sepd-s5` under
`--chi-square-tolerance 1e-4`, and made the tolerance a project setting. Every other file,
and `expected.json`, is still byte-identical to the source, except the regression pins re-taken below.

The expected values keep the `kind` their source gave them: crysta-produced fit outputs are
**regression pins** — they gate drift, not correctness — and only values marked `reference` come
from outside every engine under test. The source case's own `PROVENANCE.md` in crysta says which
is which and why.

**Minimizer declared.** diffraction-lib's
`_minimizer.type "lmfit (leastsq)"` became `_minimizer.type crysta` here and in the crysta source case
in the same change, because edi supports only crysta and warns on any other value. The tolerance line above remains the only other difference from the source, whose new
content ids are `tests/fitting/si-sepd-s5` (tree) `a6bbdbbc782e07c384a4cda5299425138e62a266` and `tests/fitting/si-sepd-s5/project` (tree)
`1f0d67b8d210bf2288b7ac0454d2bcfcc10da6c4`; `expected.json` did not change.

## Pins re-taken with crysta build-3fcc7925

crysta build-3fcc7925 adds the tails of time-of-flight reflections centred just outside the measured range, and
resumes a descent whose final polish shows it had not converged. Both move this fit, so its regression pins were
re-taken from `python -m edi fit` with that build. Reference values are unchanged.

| run | quantity | before | after |
| --- | --- | --- | --- |
| ladder | `reduced_chi_square` | 3.611119184 | 3.610945792 |
| ladder | `rwp` | 0.06941175916 | 0.0694100927 |
| fast-descent | `reduced_chi_square` | 3.611119171 | 3.610945779 |
| fast-descent | `rwp` | 0.06941175903 | 0.06941009258 |
| fast-descent-linear-snap | `reduced_chi_square` | 3.611114657 | 3.61094126 |
| fast-descent-linear-snap | `rwp` | 0.06941171565 | 0.06941004914 |
| fast-descent-guarded-linear-snap | `reduced_chi_square` | 3.611114657 | 3.61094126 |
| fast-descent-guarded-linear-snap | `rwp` | 0.06941171565 | 0.06941004914 |
| multistart-prune | `reduced_chi_square` | 3.611114145 | 3.610940746 |
| multistart-prune | `rwp` | 0.06941171073 | 0.0694100442 |
