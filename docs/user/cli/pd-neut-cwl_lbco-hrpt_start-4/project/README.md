# `refine-lbco-hrpt-s4/` —  graded start, rung 4/5 of `refine-lbco-hrpt`

One of five graded-start variants of [`../refine-lbco-hrpt/`](../refine-lbco-hrpt/): the **same
measurement, the same model and the same free set** — every refinable `(…)` bracket of the
parent is preserved verbatim, so the variant changes *where the fit starts*, never *what it
refines*. Only declared starting values differ from the parent, plus this README and the
variant's `project.edi` metadata card (`_metadata.name`/`title` only — required by
diffraction-lib to open the directory, and never a model or start value; owner requirement,
2026-08-06). The corpus exists so that descent/minimizer questions are decided against real
projects at a stated range of start distances — runnable by **both** engines, crysta and
diffraction-lib — ( task ; the sweep that consumes it is ).

## The ladder (far → near)

**`y` on this ladder, stated.** The parent authors `_peak.broad_lorentz_y` at **0.083038** —
nonzero, refinable, already fitted — so crysta 's absorbing state does not arise at the
declared start, and the CW `y`-floor instruction ("as gauss `y` is not fixed yet to start from
zero…") has **no subject** here; the packet's original claim that it applied to this project is
retracted (packet fact 3, correction block). The four graded rungs `s1`…`s4` still start `y`
cold at **0.001** as a deliberate *perturbation* — the uncalibrated user's near-Gaussian guess,
held at the same cold value on every graded rung so `y` is never a confound between them, and
never exactly 0 (crysta ) — while **`s5` keeps the authored 0.083038**: the declared start
is present in the corpus *as authored* (acceptance criterion 2; the blessed-start class is what
this corpus exists to cover). The corpus's one retained `y = 0` start is `refine-cosio-d20-s1`,
not here.

| rung | start |
| --- | --- |
| `s1` | compound cold start: tutorial `u/v/w` (0.1/−0.1/0.1), `y` 0.001, scale 1.0, offset 0.0, flat background 50 |
| `s2` | the upstream tutorial's own `u/v/w` start (0.1/−0.1/0.1 — the crysta  wrong-basin profile family), `y` 0.001; everything else declared |
| `s3` | declared `u/v/w`, `y` 0.001; scale 3.0, offset 0.15, flat background 100 |
| `s4` | declared `u/v/w`, `y` 0.001; scale 5.0, offset 0.3, flat background 150 |
| `s5` | the parent's own declared start, verbatim — byte-identical outside this README and the `project.edi` metadata card |

The grading axis is stated, not implied by the numbering: `s5` is the parent's authored in-basin
start, untouched; `s4` moves the quasi-linear axes (scale/offset/background) mildly and starts
`y` cold; `s3` pushes the same quasi-linear axes further while keeping the authored Gaussian
`u/v/w`; `s2` replaces `u/v/w` with the upstream tutorial's published start, *physically
reasonable by construction* (a real tutorial shipped it) and the profile family crysta 
measured selecting a wrong basin; `s1` compounds every axis at its far value.

**This variant is rung `s4`.**

## This start, exactly

| parameter | parent start | this start | why this is a physically reasonable start |
| --- | --- | --- | --- |
| `_peak.broad_lorentz_y` | 0.083038 | 0.001 | a cold Lorentzian-share start — the uncalibrated user’s near-Gaussian guess; the same 0.001 on every graded rung so `y` is not a confound between them, and never exactly 0 (crysta ) |
| `_instrument.calib_twotheta_offset` | 0.6 | 0.3 | half the authored zero shift |
| scale (`lbco`) | 10.0 | 5.0 | ~2× below the baseline’s converged 9.136 |
| background (5 nodes) | 169.0 … 174.56 | flat 150.0 | a flat guess slightly below the measured baseline |

The Gaussian `u/v/w` stay at the authored in-basin values; only the quasi-linear axes move, mildly.

**Deviation from the parent’s declared `y`, stated:** the parent authors `_peak.broad_lorentz_y` at 0.083038 (in-basin); this rung starts it cold at **0.001** as a graded-start *perturbation* — not the CW `y`-floor rule, whose subject is a zero-and-refinable authored `y` that this project does not have (packet fact 3’s contrary claim is retracted) — held at the same value on every graded rung so `y` is never a confound between rungs, and never exactly 0 (crysta ).

## Reference

**Target: reduced χ² 1.259874, Rwp 0.071253, cell `a` 3.890802 Å, scale 9.145** — produced by
**diffraction-lib (`lmfit (leastsq)` + cryspy)**, that engine's own committed record of refining
this same measurement: entry `refine-lbco-hrpt-from-data` of
[`../refine-lbco-hrpt-baseline/baseline.json`](../refine-lbco-hrpt-baseline/baseline.json)
(repo path `examples/refine-lbco-hrpt-baseline/baseline.json`), vendored byte-identical from
upstream pin `39ada82c` with its sha256 recorded in
[`../refine-lbco-hrpt-baseline/PROVENANCE.md`](../refine-lbco-hrpt-baseline/PROVENANCE.md), at
that engine's own declared `rtol` 0.02. From the parent's declared start, edi+crysta was measured
converging to within that tolerance on the three compared outputs (cell `a` 0.000295 %, scale
0.143064 %, Rwp 1.457180 % off the baseline — the parent README's authoritative claim). Reduced
χ² is **reported, never compared across engines**: the engines weight and count differently
(edi's converged 1.2973 sits 2.97 % from the baseline's 1.259874). No number in this file was
produced by the code under test.

## Run

```bash
OMP_NUM_THREADS=1 pixi run python -m edi fit examples/refine-lbco-hrpt-s4 --verbosity full
```

`OMP_NUM_THREADS` is pinned to a single thread deliberately: crysta  is *measured*
thread-count trajectory divergence, so an unpinned run on a different core count is not
comparable point-for-point with this corpus's companion runs (the owner compares against an
independent M2 run). Pin it on every machine.
