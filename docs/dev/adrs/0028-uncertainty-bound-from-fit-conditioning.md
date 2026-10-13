# ADR-0028 — Uncertainty bound from the fit's conditioning

- **Status:** Accepted
- **Date:** 2026-10-10
- **Implementation:** ✅ Implemented — the browser checks compare web and native uncertainties with this bound
- **Priority:** Medium

## Context

The browser checks compare a web fit with a native capture of the same fit. Values and pattern numbers match within
relative 1e-9, and fitted uncertainties used the machine-report bound, relative 5e-9 with an absolute floor of 5e-10.
An uncertainty comes from the inverse of the fit's normal matrix, so rounding differences between two builds (the
web build sums in a different order and uses different maths functions) are amplified by the fit's conditioning. On
an ill-conditioned fit a correct web build can miss a fixed bound that ignores this.

## Decision

1. Uncertainty parity uses a bound derived from the native fit alone, before any web result exists. No browser
   result or measured gap is an input.
2. The derivation is in [`tests/fixtures/web_parallel/conditioning/README.md`](https://github.com/enhantica/edi/blob/main/tests/fixtures/web_parallel/conditioning/README.md).
   In short: with the native Gram matrix `G = JᵀWJ` scaled to unit diagonal (`A`, inverse `B`), `m` data points and
   `p` free columns, two binary64 builds perturb `A` by at most `δ = 2p [γ(m + 4) + γ(p)]`, `γ(k) = ku/(1-ku)`,
   `u = 2⁻⁵³`. With `h = δ‖B‖∞`, the covariance diagonal moves by at most `qᵢ = δ‖Beᵢ‖₂² / [Bᵢᵢ(1-h)]` relatively,
   and uncertainty `σᵢ` by `τᵢ = 1 - sqrt(1-qᵢ)`.
3. The bound for each saved uncertainty is `max(5e-10, 5e-9 σᵢ, τᵢ σᵢ)`. `h ≥ 1` or `qᵢ ≥ 1` refuses; nothing is
   capped.
4. Values, pattern numbers and every other refusal keep their bounds. A gap above the derived bound is a defect to
   fix, never a reason to widen it.

## Consequences

The bound follows each fit: well-conditioned fits keep the old bound, ill-conditioned ones get the room their
conditioning allows. It is a worst-case roundoff bound and can be much looser than the real difference; it does not
claim more significant digits. Each check fixture carries a native conditioning capture, regenerated with the
fixture.

## Alternatives considered

| Alternative | Verdict |
|---|---|
| Keep relative 5e-9 for uncertainties | Rejected: correct builds of ill-conditioned fits fail it |
| Widen the bound to the measured web gap | Rejected: a bound read from the result under test proves nothing |
| Make the web covariance bit-identical to native | Rejected: needs the same summation order and maths library in every build |
