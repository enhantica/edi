# `refine-cosio-d20-s1/` —  graded start, rung 1/5 of `refine-cosio-d20`

One of five graded-start variants of [`../refine-cosio-d20/`](../refine-cosio-d20/): the **same
measurement, the same model and the same free set** — every refinable `(…)` bracket of the
parent is preserved verbatim, so the variant changes *where the fit starts*, never *what it
refines*. Only declared starting values differ from the parent, plus this README and the
variant's `project.edi` metadata card (`_metadata.name`/`title` only — required by
diffraction-lib to open the directory, and never a model or start value; owner requirement,
2026-08-06). The corpus exists so that descent/minimizer questions are decided against real
projects at a stated range of start distances — runnable by **both** engines, crysta and
diffraction-lib — ( task ; the sweep that consumes it is ).

## The ladder (far → near)

| rung | start |
| --- | --- |
| `s1` | **the parent's own declared start, verbatim** (byte-identical outside this README and the `project.edi` metadata card) — scale 10, offset 0, backgrounds 0, `y` **0** (the corpus's one retained absorbing-state start) |
| `s2` | the declared start with only `y` lifted to 0.001 (the owner's floor) — the crysta  compound-cold-start class, with `y` free to move |
| `s3` | scale 2.0, offset 0.1, flat background 300, `y` 0.001 |
| `s4` | scale 1.5, offset 0.25, flat background 500, `y` 0.001 |
| `s5` | scale 1.3, offset 0.29, baseline-read backgrounds 600…250, `y` 0.001 — near-optimal on every axis the corpus grades, with `y` at the corpus-uniform floor |

**The corpus `y`-rule binds every non-`s1` rung:** `y` starts at exactly **0.001** — the owner's
uniform cold-but-nonzero floor (never 0 — crysta ) — in `s2`…`s5` alike, so the `y` descent
itself is exercised from the same cold value at every distance of the other axes.

**Deliberate deviation from the corpus naming convention, stated:** everywhere else in this
corpus `s5` is the parent's own declared start. For this project the declared start is itself
the far end — the parent README states it at reduced χ² **38189.53**, deliberately unhelpful,
with `y` declared `0.()` (zero *and* refinable — crysta 's absorbing state). Keeping
"ascending = closer" therefore places the declared start at `s1`, where it also serves as the
corpus's single retained `y = 0` variant (the absorbing state stays visible at the far end,
exactly where it is expected). The parent's `u/v/w` (0.2/−0.5/0.4) are kept in **all** rungs:
the reference does not record converged `u/v/w`, so grading them would be guessing.

**This variant is rung `s1`.**

## This start, exactly

**This variant IS the parent’s own declared start** — byte-identical apart from this README and the `project.edi` metadata card (distinct `_metadata.name`, owner requirement — metadata only, never a model or start value) — and it is the corpus’s **one retained `y = 0` variant**: `_peak.broad_lorentz_y` stays declared `0.()`, zero *and* refinable, which crysta  measures as an absorbing state (the AD Jacobian column for `y` is exactly zero there, so `y` can never leave 0). Retained deliberately — owner directive — so the absorbing state stays visible at the far end of the ladder rather than being designed away. Every other CW rung in this corpus starts `y` > 0.

The parent’s declared start, stated (the parent README’s own table): reduced χ² **38189.53** — deliberately unhelpful in four ways at once (scale 10 vs reference 1.3191, offset 0 vs 0.2878, all 14 backgrounds 0 vs 609…243, `y` 0 vs 0.0139).

## Reference

**Target: reduced χ² 4.38, with `broad_lorentz_y` 0.0139, `calib_twotheta_offset` 0.2878, `scale`
1.3191, backgrounds 609.32 … 242.99** — the owner's own **diffraction-lib (`lmfit (leastsq)` +
cryspy)** refinement of the parent directory, recorded 2026-08-05 in the parent
[`../refine-cosio-d20/README.md`](../refine-cosio-d20/README.md) (repo path
`examples/refine-cosio-d20/README.md`, whose Provenance section states the run). For context,
edi+crysta at crysta `fdf8e7b5` was measured reaching 4.4195 from the parent's declared start,
the entire gap being crysta  (`y` frozen at zero); reduced χ² across engines is otherwise
**reported, never compared**. No number in this file was produced by the code under test.

## Run

```bash
OMP_NUM_THREADS=1 pixi run python -m edi fit examples/refine-cosio-d20-s1 --verbosity full
```

`OMP_NUM_THREADS` is pinned to a single thread deliberately: crysta  is *measured*
thread-count trajectory divergence, so an unpinned run on a different core count is not
comparable point-for-point with this corpus's companion runs (the owner compares against an
independent M2 run). Pin it on every machine.
