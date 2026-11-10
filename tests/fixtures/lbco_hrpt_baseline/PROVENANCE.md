# diffraction-lib tutorial baseline — provenance ()

`baseline.json` is the **frozen engine-parity input** consumed at run time by
[`examples/fit_lbco_hrpt.py`](../fit_lbco_hrpt.py) (key `refine-lbco-hrpt-from-data`). It is
diffraction-lib's committed record of **its own** tutorial refinements, carrying that engine's own
declared tolerance (`rtol` 0.02) — the *engine parity* target, never a reference standard and never
an experimental-correctness claim.

- **Upstream:** <https://github.com/easyscience/diffraction-lib>, path
  `tests/tutorials/baseline.json`.
- **Pin:** commit **`39ada82c`** (branch `fullprof-occupancy-notation`,
  [PR #218](https://github.com/easyscience/diffraction-lib/pull/218)) — the same single pin the CW
  verification corpus uses (`knowledge/verification/fullprof/PROVENANCE.md`, ).
- **Byte identity:** this file is the exact upstream blob — `git show
  39ada82c:tests/tutorials/baseline.json`, git blob `0a4313f6243a09c4930aa85f0e184be87eab0adf`,
  sha256 `28ab42c846538dbc6d6d6947df03fa09f9b78587eee60e9773b409d85e67a183`. The whole file is
  vendored rather than the one key so the identity claim stays checkable against the upstream blob
  hash; nothing in it was produced or modified by edi or crysta.
- **Why vendored:** `knowledge/libraries/diffraction-lib/` is a git-ignored study clone
  (`.gitignore`, `knowledge/libraries/README.md`), so a runnable example cannot depend on it — a
  clean checkout would not have the file ( review-1 B1). The tracked measurement the example
  refines (`knowledge/verification/fullprof/pd-neut-cwl_lbco_basic/lbco.dat`) was already vendored
  by  under the same pin; the FullProf files beside it are **fitless by contract** ()
  and supply measurement/background inputs only, never a refined-value oracle.
- **Licence:** diffraction-lib is BSD-3-Clause; the licence copy is carried at
  [`tests/fixtures/diffraction-lib-LICENSE`](../diffraction-lib-LICENSE).
