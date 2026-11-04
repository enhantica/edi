# pd-neut-cwl_cosio-d20_start-4 — provenance

crysta fitting case `cosio-d20-s4` under the CLI project id rule.

Copied **byte-identical** from crysta `origin/main` at `973b34bd92f01ba77f89b049a3e7e74d252b9db3`, path
`tests/fitting/cosio-d20-s4/` — the `project/` tree and `expected.json`, nothing else.

| object | git id at the source |
| --- | --- |
| `tests/fitting/cosio-d20-s4` (tree) | `5f47f4c7cd902b5ed81cec1c048bf58efb900da9` |
| `tests/fitting/cosio-d20-s4/project` (tree) | `9908c949a3b9ce5ea6a1d0c1066296f48402d131` |
| `tests/fitting/cosio-d20-s4/expected.json` (blob) | `c18f266723033765e0890515f8b00ef595595be4` |

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
new content ids are `tests/fitting/cosio-d20-s4` (tree) `6f1cec02b860ea573f055c0e2deea6d5be87d15a` and `tests/fitting/cosio-d20-s4/project` (tree)
`9a4a504394d525c0fd78eff1548eddc7cda3a876`; `expected.json` did not change.
