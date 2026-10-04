# pd-neut-cwl_cosio-d20_start-1 — provenance

crysta fitting case `cosio-d20-s1` under the CLI project id rule.

Copied **byte-identical** from crysta `origin/main` at `973b34bd92f01ba77f89b049a3e7e74d252b9db3`, path
`tests/fitting/cosio-d20-s1/` — the `project/` tree and `expected.json`, nothing else.

| object | git id at the source |
| --- | --- |
| `tests/fitting/cosio-d20-s1` (tree) | `940816e8ff8a6b9bbb63f51e43683d0b2f0e12ab` |
| `tests/fitting/cosio-d20-s1/project` (tree) | `f9a9b08128982e39295d2102ddd72dff15413471` |
| `tests/fitting/cosio-d20-s1/expected.json` (blob) | `0d6cedce69f8c0920574756ea1fd105d516280bc` |

The expected values keep the `kind` their source gave them: crysta-produced fit outputs are
**regression pins** — they gate drift, not correctness — and only values marked `reference` come
from outside every engine under test. The source case's own `PROVENANCE.md` in crysta says which
is which and why.

**Re-pinned.** The CW generation limit (a reflection contributes only if centred within the axis end plus
`cutoff_fwhm` × the width there, FullProf's rule) removed near-180° reflections that painted into the high-angle
data. Every regression pin that moved was re-pinned to the value measured by
`tools/checks/cli_projects.py` (edi) on crysta `9c1caaec`: reduced χ² +0.000829 and Rwp +3.72×10⁻⁶ in every
variant. No iteration count and no `reference` value moved. The git ids in the table above are the re-pinned
source's content ids (tree and blob ids survive crysta's squash merge; the copy stays byte-identical).

**Re-pinned by (the frozen generation limit).** Each fit now fixes the CW generation limit from its starting state, so
no reflection crosses it mid-fit. The moved regression pins shifted at the 8th significant digit or beyond and were
re-pinned to their machine-record values, measured through `python -m edi` on crysta `8b95cccc`; the copy stays
byte-identical to its crysta source, whose content ids are above.

**Minimizer declared.** diffraction-lib's
`_minimizer.type "lmfit (leastsq)"` became `_minimizer.type crysta` here and in the crysta source case
in the same change, because edi supports only crysta and warns on any other value. The copy stays byte-identical to its source, whose
new content ids are `tests/fitting/cosio-d20-s1` (tree) `5358c82901000596fc2316dc75ff557578e0c593` and `tests/fitting/cosio-d20-s1/project` (tree)
`7c5e4dc75f4cb6b520390aaa777e747fada472aa`; `expected.json` did not change.
