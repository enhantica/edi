# pd-neut-cwl_lbco-hrpt_start-2 — provenance

crysta fitting case `lbco-hrpt-s2` under the CLI project id rule.

Copied **byte-identical** from crysta `origin/main` at `973b34bd92f01ba77f89b049a3e7e74d252b9db3`, path
`tests/fitting/lbco-hrpt-s2/` — the `project/` tree and `expected.json`, nothing else.

| object | git id at the source |
| --- | --- |
| `tests/fitting/lbco-hrpt-s2` (tree) | `9c40772553a0eae04100defa68729c8810a096cf` |
| `tests/fitting/lbco-hrpt-s2/project` (tree) | `03e1976b1f863c5e794151126dee1d88becea417` |
| `tests/fitting/lbco-hrpt-s2/expected.json` (blob) | `2fc9ce556b77191b24fa4fd7d244b37da0de9544` |

The expected values keep the `kind` their source gave them: crysta-produced fit outputs are
**regression pins** — they gate drift, not correctness — and only values marked `reference` come
from outside every engine under test. The source case's own `PROVENANCE.md` in crysta says which
is which and why.

**Minimizer declared.** diffraction-lib's
`_minimizer.type "lmfit (leastsq)"` became `_minimizer.type crysta` here and in the crysta source case
in the same change, because edi supports only crysta and warns on any other value. The copy stays byte-identical to its source, whose
new content ids are `tests/fitting/lbco-hrpt-s2` (tree) `d1f917b20f59c16c3a64bd197f7e1a703f9dc917` and `tests/fitting/lbco-hrpt-s2/project` (tree)
`9fcf6c3d746af234c6313bde16d71f265791342b`; `expected.json` did not change.

**Extended by (preferred orientation).** The experiment gains a `_preferred_orientation` row with
`march_r` free; the crysta source case was extended in the same change and the copy stays
byte-identical to it: `tests/fitting/lbco-hrpt-s2` (tree) `9f91f204eaeb797d38ddc8d983e75413c91ff874`,
`tests/fitting/lbco-hrpt-s2/project` (tree) `cbf9437b249ba6faf6c1b4c74120f4a8ce057d16`,
`tests/fitting/lbco-hrpt-s2/expected.json` (blob) `b6c38be0073674fe0e142a59293d3c28fac277f1`. The
re-minted regression pins and why r is weakly determined on this cubic case are in the source case's
own `PROVENANCE.md`.
