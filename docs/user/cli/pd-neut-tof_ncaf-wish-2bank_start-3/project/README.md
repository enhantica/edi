# `refine-ncaf-wish-2bank-s3/` —  graded start, rung 3/5 of `refine-ncaf-wish-2bank`

One of five graded-start variants of [`../refine-ncaf-wish-2bank/`](../refine-ncaf-wish-2bank/): the **same
measurement, the same model and the same free set** — every refinable `(…)` bracket of the
parent is preserved verbatim, so the variant changes *where the fit starts*, never *what it
refines*. Only declared starting values differ from the parent, plus this README and the
variant's `project.edi` metadata card (`_metadata.name`/`title` only — required by
diffraction-lib to open the directory, and never a model or start value; owner requirement,
2026-08-06). The corpus exists so that descent/minimizer questions are decided against real
projects at a stated range of start distances — runnable by **both** engines, crysta and
diffraction-lib — ( task ; the sweep that consumes it is ).

## The ladder (far → near)

| rung | start (per bank: wish_4_7 / wish_5_6) |
| --- | --- |
| `s1` | scale 4/8, offset 0, σ₂ 1.5/1.5, α₁ 0.3, β₀ 0.003/0.003, β₁ 0.003/0.003 |
| `s2` | scale 10/20, offset 0, σ₂ 3./3., α₁ 0.2, β₁ 0.005/0.005 |
| `s3` | scale 18/39, offset 0, σ₂ 6./5. |
| `s4` | scale 18/39, offset 0 |
| `s5` | the parent's own declared start, verbatim |

**Why the far rungs overestimate α₁ instead of underestimating it:** both banks fix a negative
`rise_alpha_0` (−0.0115 / −0.0094), and crysta's always-on domain limit requires the rise rate
`α(d) = α₀ + α₁/d` to be positive over each bank's whole painted window — a constraint on the
*pair*, measured refusing α₁ 0.02 and 0.05 at the `wish_4_7` window edge d ≈ 5.36 Å before the
fit began. An underestimated α₁ below ≈ 0.06 is therefore not a far start, it is a refusal;
the farthest *admissible* misjudgment of the rise rate is upward.

The grading axis: `s5` is the committed start (α/β/σ₂/offset near the values FullProf's
single-bank reference converged to where comparable; backgrounds pre-set and **fixed**, so they
are part of the model and never touched); `s4` halves the scales and zeroes the offsets (the
ignorant default); `s3` adds a ~3× Gaussian-broadening underestimate; `s2` and `s1` push scale,
broadening, rise and decay constants progressively below plausible — an uncalibrated user's
sharp-peak guess. The refinable per-atom `b_iso` values are never perturbed (ADPs are outside
the corpus's stated perturbation bound: scale, zero/offset, background intensities and
profile-broadening terms only).

**This variant is rung `s3`.**

## This start, exactly

| parameter | parent start | this start | why this is a physically reasonable start |
| --- | --- | --- | --- |
| `_peak.broad_gauss_sigma_2` (both banks) | 18. / 15.5 | 6. / 5. | ~3× Gaussian-broadening underestimate; α/β stay declared |
| `_instrument.calib_d_to_tof_offset` (both banks) | −15. / −13.5 | 0. | the ignorant default |
| scale (`ncaf`, both banks) | 37. / 78. | 18. / 39. | half the declared scales |

## Reference

**NOT PINNED to a joint-fit value — deliberately, and here is why.** No committed record of a
converged **joint two-bank** refinement of this project exists in edi or its vendored
references at the time of writing (). What exists, resolves, and is independent:
FullProf's committed **single-bank** NCAF reference
[`tmpl_one_bank.sum`](../../knowledge/verification/fullprof/pd-neut-tof_ncaf_jorgensen-von-dreele/tmpl_one_bank.sum)
(repo path `knowledge/verification/fullprof/pd-neut-tof_ncaf_jorgensen-von-dreele/tmpl_one_bank.sum`,
beside its `tmpl_one_bank.pcr` and `tmpl_one_bank.prf`; FullProf.2k Version 8.40, byte-identical
from upstream (easyscience/diffraction-lib) commit `39ada82c` as recorded in
`knowledge/verification/fullprof/PROVENANCE.md`): χ² 15.2, zero −13.88128, Dtt1 20773.12305,
σ₂ 15.6959, α₀ −0.009276 / α₁ 0.109622, β₀ 0.006705 / β₁ 0.009708, scale 36.17374 — for **one
bank** (2θ 152.827°) of this instrument/material family. It anchors the single-bank physics but
neither this project's joint free set nor its per-bank data windows, so quoting it as this
project's target would assert something it does not say. Producing a joint-fit reference is its
own measurement and belongs to the  sweep; writing a number here without running it would
launder a guess into an anchor (the exact failure the withdrawn  `104.19` cost a cycle to
undo). Until  pins one, comparisons over this project's five rungs are **relative** —
same project, same free set, graded starts — which is sufficient for what the corpus decides.
No number in this file was produced by the code under test.

## Run

```bash
OMP_NUM_THREADS=1 pixi run python -m edi fit examples/refine-ncaf-wish-2bank-s3 --verbosity full
```

`OMP_NUM_THREADS` is pinned to a single thread deliberately: crysta  is *measured*
thread-count trajectory divergence, so an unpinned run on a different core count is not
comparable point-for-point with this corpus's companion runs (the owner compares against an
independent M2 run). Pin it on every machine.
