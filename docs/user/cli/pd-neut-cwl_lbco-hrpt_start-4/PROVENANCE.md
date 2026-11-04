# pd-neut-cwl_lbco-hrpt_start-4 — provenance

crysta fitting case `lbco-hrpt-s4` under the CLI project id rule.

Copied **byte-identical** from crysta `origin/main` at `973b34bd92f01ba77f89b049a3e7e74d252b9db3`, path
`tests/fitting/lbco-hrpt-s4/` — the `project/` tree and `expected.json`, nothing else.

| object | git id at the source |
| --- | --- |
| `tests/fitting/lbco-hrpt-s4` (tree) | `a6c1dfe105a6f53a4951916aefd525be2bf0837a` |
| `tests/fitting/lbco-hrpt-s4/project` (tree) | `6b2f38daf8efdcccc79488d694e94fd9e84068be` |
| `tests/fitting/lbco-hrpt-s4/expected.json` (blob) | `b72cce960a0e49bdf80b1c715f08de366bfae447` |

The expected values keep the `kind` their source gave them: crysta-produced fit outputs are
**regression pins** — they gate drift, not correctness — and only values marked `reference` come
from outside every engine under test. The source case's own `PROVENANCE.md` in crysta says which
is which and why.

**Minimizer declared.** diffraction-lib's
`_minimizer.type "lmfit (leastsq)"` became `_minimizer.type crysta` here and in the crysta source case
in the same change, because edi supports only crysta and warns on any other value. The copy stays byte-identical to its source, whose
new content ids are `tests/fitting/lbco-hrpt-s4` (tree) `13faadd66ec255fa30ebb611dcb63546720bf905` and `tests/fitting/lbco-hrpt-s4/project` (tree)
`25f762a7cf74aaecd5aa912b0fa963364e9020cd`; `expected.json` did not change.

**Re-pinned 2026-11-04.** The project declares the Shift/s.u. stop rule (`_minimizer.stop_rule shift_su`, 0.1; the χ²
change still ends a fit when it passes first), as every example does. Pins retaken with `python -m edi fit --report
machine` linked against crysta `609586d9`, `OMP_NUM_THREADS=1`: ladder reduced_chi_square 1.297269332 → 1.297275389;
ladder iterations 9 → 7; ladder rwp 0.07229128414 → 0.07229145291; fast-descent rwp 0.07229128412 → 0.07229128849;
fast-descent-linear-snap reduced_chi_square 1.297269339 → 1.297270929; fast-descent-linear-snap iterations 7 → 6;
fast-descent-linear-snap rwp 0.07229128433 → 0.07229132862; fast-descent-guarded-linear-snap reduced_chi_square
1.297269339 → 1.297270929; fast-descent-guarded-linear-snap iterations 7 → 6; fast-descent-guarded-linear-snap rwp
0.07229128433 → 0.07229132862.
