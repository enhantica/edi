# `refine-si-sepd-s5/` —  graded start, rung 5/5 of `refine-si-sepd`

One of five graded-start variants of [`../refine-si-sepd/`](../refine-si-sepd/): the **same
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
| `s1` | scale 10, offset 0, σ₀ 0.3 / σ₁ 2.0, γ₁ 0.1, β₀ 0.01 / β₁ 0.003 |
| `s2` | scale 30, offset 0, σ₀ 0.5 / σ₁ 5.0, γ₁ 0.3, β₀ 0.02 / β₁ 0.005 |
| `s3` | scale 100, offset 0, σ₀ 1.0 / σ₁ 10.0, γ₁ 1.0; β as declared |
| `s4` | scale 100, offset 0; profile as declared |
| `s5` | the parent's own declared start, verbatim |

The grading axis: `s5` is the committed start (profile already near the FullProf converged
values, scale 600 vs FullProf's 388.85, backgrounds zero-started and refinable); `s4` moves only
the quasi-linear axes (scale ~4× low, offset to the ignorant 0); `s3` adds a ~3× broadening
underestimate; `s2` and `s1` push scale, Gaussian/Lorentzian widths and the decay constants
progressively further below plausible calibration — sharp-peak optimism, the common first guess
of an uncalibrated setup. Backgrounds stay at the parent's own zero start in every rung (a zero
background start is fine — owner directive) and the refinable cell `a` is never perturbed
(coordinates and cells are outside the corpus's perturbation bound).

**This variant is rung `s5`.**

## This start, exactly

**This variant IS the parent’s own declared start** — byte-identical apart from this README and the `project.edi` metadata card (distinct `_metadata.name`, owner requirement — metadata only, never a model or start value). That start, stated rather than assumed (the committed experiment carries a populated `intensity_calc`, i.e. a fitted state; no committed record states its χ²ᵣ): read off the file, the profile sits near FullProf’s converged values (σ₀ 3.0148 vs 3.5544, σ₁ 33.3451 vs 33.0419, γ₁ 2.5489 vs 2.5430, β₀ 0.0408 vs 0.04221), the scale 600 sits ~1.5× above FullProf’s 388.85, the offset −10.0 near FullProf’s −9.18766, and all 14 refinable backgrounds start at zero. A moderately near start; measuring its χ²ᵣ is ’s job, not this file’s.

## Reference

**Target (FullProf.2k Version 8.40, its own converged refinement of this same SEPD silicon
measurement): χ² 2.66, Rwp 5.98 (not background-corrected; conventional Rietveld Rwp 11.6)**,
with zero −9.18766, Dtt1 7476.91016, Dtt2 −1.54, α₀ 0 / α₁ 0.5971, β₀ 0.042210 / β₁ 0.009460,
σ₀ 3.5544 / σ₁ 33.0419 / σ₂ 0, γ₁ 2.5430, scale 388.8488 (in FullProf's own scale/`Occ`
convention — see the provenance note below; never compared 1:1 with this project's scale).
Source: the committed matched FullProf pair
[`arg_si.sum`](../../knowledge/verification/fullprof/pd-neut-tof_si_jorgensen-von-dreele/arg_si.sum)
(repo path `knowledge/verification/fullprof/pd-neut-tof_si_jorgensen-von-dreele/arg_si.sum`,
beside its `arg_si.pcr` and `arg_si.prf`), FullProf's output **never produced or modified by edi
or crysta**, byte-identical from upstream (easyscience/diffraction-lib) commit `39ada82c` as
recorded in `knowledge/verification/fullprof/PROVENANCE.md`, and
regenerable with the hub's `fullprof-fp2k` skill. That the pair refines *this* measurement was
verified by inspection: identical bank geometry (2θ 144.845, Dtt1 7476.91, Dtt2 −1.54, α₁
0.5971) and an identical measured intensity/σ sequence on the same 2000 + 5·k µs grid. FullProf's
χ² is FullProf-weighted — an **independent engine's anchor** for this measurement and profile
family, not a value edi+crysta must equal; what edi+crysta attain from each rung is exactly what
the  sweep measures. No number in this file was produced by the code under test.

## Run

```bash
OMP_NUM_THREADS=1 pixi run python -m edi fit examples/refine-si-sepd-s5 --verbosity full
```

`OMP_NUM_THREADS` is pinned to a single thread deliberately: crysta  is *measured*
thread-count trajectory divergence, so an unpinned run on a different core count is not
comparable point-for-point with this corpus's companion runs (the owner compares against an
independent M2 run). Pin it on every machine.
