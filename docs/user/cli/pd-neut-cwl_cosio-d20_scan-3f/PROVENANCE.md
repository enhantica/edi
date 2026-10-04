# pd-neut-cwl_cosio-d20_scan-3f — provenance

crysta fitting case `cosio-d20-scan-3f` under the CLI project id rule.

Copied **byte-identical** from crysta `origin/main` at `973b34bd92f01ba77f89b049a3e7e74d252b9db3`, path
`tests/fitting/cosio-d20-scan-3f/` — the `project/` tree and `expected.json`, nothing else.

| object | git id at the source |
| --- | --- |
| `tests/fitting/cosio-d20-scan-3f` (tree) | `11d4e8d0978cac371b11fd740914550de88c1e43` |
| `tests/fitting/cosio-d20-scan-3f/project` (tree) | `954556e9183643f1fd74d2c78ab02c13f74e195c` |
| `tests/fitting/cosio-d20-scan-3f/expected.json` (blob) | `626ef8abd5c00bb12c05bbb18361aea4598a17d7` |

**Extended.** `project/analysis/analysis.edi` declares two more minimization conditions,
`_minimizer.descent fast_descent` and `_minimizer.chi_square_tolerance 1e-4`, so the project
exercises a sequential fit under a non-default descent and tolerance. The three per-file reduced
chi-squares were re-pinned, and three per-file iteration counts added, from `python -m edi fit` of
this project on edi the declared-descent implementation linked against crysta
`e31cba10244e7c26f058e9a829638c0231420126`. They are **regression pins** (the 52.3 K value is
unchanged at its 1e-6 bound). `n_free` stays the independent reference it was. Under the engine
defaults (`ladder`, 1e-6) the same project reproduces the pins it carried before the extension:
4.783623, 4.381669 and 3.887557, at 5, 8 and 16 iterations.

The expected values keep the `kind` their source gave them: crysta-produced fit outputs are
**regression pins** — they gate drift, not correctness — and only values marked `reference` come
from outside every engine under test. The source case's own `PROVENANCE.md` in crysta says which
is which and why.

**Re-pinned.** The CW generation limit (FullProf's rule: a reflection contributes only if centred within the axis
end plus `cutoff_fwhm` × the width there) moved this project's regression pins: 52.345 K 4.783623 → 4.784745,
299.394 K 4.381672 → 4.382172, 497.379 K 3.887563 → 3.887746 at 10 iterations (was 11), measured by
`tools/checks/cli_projects.py` on crysta `9c1caaec`.

**Re-pinned again by (the frozen generation limit).** Each fit now fixes the CW generation limit from its starting
state, so no reflection crosses it mid-fit. The 497.379 K file, the one whose widths moved the old limit across a
reflection during its fit, went 3.887746 → 3.887590 at 10 iterations, measured by
`tools/checks/cli_projects.py` on crysta `adb3b700`. The other two files did not move.
The 299.394 K pin moved at the 8th significant digit with it (4.382171604 → 4.382171634) and was
re-pinned to its record value.
