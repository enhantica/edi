# Native conditioning and physical uncertainty parity

The scientific captures and their parameter/pattern tolerances stay unchanged.
Uncertainty parity uses a bound derived from the native final fit, before the web
implementation. No browser result or measured browser gap is an input.
The minimum conformance bounds remain relative `5e-9` and absolute `5e-10`.
The parameter/pattern comparison remains relative `1e-9`, absolute `1e-11`,
which also satisfies the machine-report value bound `5e-9`.

## Reference and reproduction

`capture.cpp` links only the pre-web native SDK `c22d1ae3`. It runs each original
input, records the covariance, then evaluates the final public residual's
weighted Jacobian in the same free-column order. It accumulates the Gram matrix
in extended precision. The generator checks the original native capture's fit
statistics and uniquely matches every saved positive uncertainty to the native
value and covariance diagonal under the old conformance bounds. It does not
regenerate the scientific capture. The sidecar records the genuine SDK identity,
executable/capture hashes and a digest of the entire scientific reference.

Build this directory with `find_package(crysta)` resolving the pre-web SDK,
then run `native_conditioning <original-project>` into a raw JSON file.
Run the generator from the repository root with its Python environment:

```
PYTHONPATH=. python tests/fixtures/web_parallel/conditioning/generate.py \
  <lbco-or-ncaf> <raw-json> <native-executable> <sdk-manifest>
```

The generator normalizes the native Gram matrix and inverts it independently
with partial pivoting at 80 decimal digits. It refuses a nonpositive Gram matrix
or a spectrum at the engine's relative `1e-15` pseudoinverse cutoff. Sidecars
contain all free columns, even if a column has no saved bracketed operand.
Only bound quantities for actually saved uncertainties affect comparison.

## Derivation for an ADR

Let `m` be the native number of data points, `p` the number of free columns,
`G = JᵀWJ`, `D = diag(sqrt(Gᵢᵢ))`, `A = D⁻¹GD⁻¹`, and `B = A⁻¹`.
This is the covariance solver's column scaling. A positive diagonal and stable
full rank are preconditions; a rank-cutoff ambiguity has no finite bound here.
The physical covariance is `χ²ᵣ D⁻¹ B D⁻¹`.

Use binary64 unit roundoff `u = 2⁻⁵³` and `γ(k) = ku/(1-ku)`.
The classical dot-product bound gives an absolute error at most `γ(m)` in
each entry of a Gram matrix whose weighted columns have unit norm. Four
additional operations cover the diagonal normalization. The covariance
acceptance model adds `γ(p)` for the backward-stable inverse computation.
For two independently rounded backends, the spectral perturbation budget is

```
δ = 2p [γ(m + 4) + γ(p)]
h = δ ||B||∞
```

The factor `p` bounds spectral norm by the maximum entry error; the factor two
accounts for both native and web rounding. These fixed counts come from the
native matrix dimensions and the stated arithmetic model, never an observed
gap. The inverse term is a backward-error acceptance model, not a proof that
every library/transcendental evaluation is correctly rounded. Values and
patterns remain independently gated. An implementation error exceeding the
resulting bound is a defect; it cannot enlarge this budget.

For symmetric positive definite `A`, the resolvent identity yields

```
|ΔBᵢᵢ| ≤ δ ||B eᵢ||₂² / (1-h)
qᵢ = δ ||B eᵢ||₂² / [Bᵢᵢ (1-h)]
```

This follows by bounding the central inverse in
`ΔB = -B ΔA (I + B ΔA)⁻¹ B`; physical column units cancel in
`|ΔCᵢᵢ|/Cᵢᵢ`. Since uncertainty is `sqrt(Cᵢᵢ)`, its maximum relative change,
including either sign of the perturbation, is

```
τᵢ = 1 - sqrt(1-qᵢ) = qᵢ / [1 + sqrt(1-qᵢ)]
physical_boundᵢ = max(5e-10, 5e-9 σᵢ, τᵢ σᵢ)
```

Refuse `h >= 1` or `qᵢ >= 1`; never cap or replace an unbounded quantity.
The comparator also checks dimensions, finite positive matrix quantities,
the inverse residual under the binary64 matrix-product rounding bound,
reference identity, and complete unique saved-operand bindings. Changed values,
pattern numbers, uncertainty presence, empty brackets, malformed tokens,
inventory and fixed states retain their existing refusals.

This is a worst-case covariance-roundoff bound. It can be substantially looser
than the measured cross-platform error of an ill-conditioned fit; it does not
assert additional statistically significant uncertainty digits. The closed-form
two-by-two controls independently exercise the diagonal derivative, both signs
of the square-root bound, physical unit conversion, and refusal outside it.

The dot-product model and `γ(k)` are described by Nicholas Higham,
[Numerical Stability of Algorithms at Extreme Scale and Low Precisions](https://eprints.maths.manchester.ac.uk/2833/1/paper.pdf),
sections 1 and 2.1. The covariance-diagonal and square-root propagation above
are the explicit derivation used by this gate.
