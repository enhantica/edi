# Independent reference and regression pins

`beer-fullprof.json` is parsed by `generate_beer_reference.py` from the unchanged
owner FullProf summary committed in edi at
`knowledge/fitting/fullprof/pd-neut-tof_duplex-beer_pseudo-voigt/duplex_mode6-IRF.sum`.
The JSON carries the SHA-256 of that original summary. No FullProf executable runs
in the gates, and no engine output supplied the expected fitted values or their
standard uncertainties. The original summary remains in its existing home.

`profiles.py` supplies normalized analytical Gaussian, Lorentzian and linear-mix
profiles with the Caglioti width, and an isolated cubic reflection with the Sears
sodium neutron scattering length. These are correctness references.

`tch-regression-Linux.json` records edi calculation bytes at its merged
`7a8eabf53084332a10b90991907d2040e5365b6a`, linked to the qualified diagnostic
SDK at crysta `b9f2267451adf1896463c706a87fea20790d28ac`. The latter differs from
the merged engine baseline only in tests and fixtures. The visible generator
`capture_tch.py` refuses another edi source or an unproven linked engine.
This is a regression pin, not an independent correctness claim.
The recorded Linux platform retains exact byte comparison. Other CI platforms use
these unchanged pre-change samples with the published ADR-0057 bound:
`abs(actual - expected) <= max(5e-9 * abs(expected), 5e-10)` at every sample.
The sample population and finite-value requirement remain exact. The platform
branch is exercised explicitly; no platform is skipped and no post-change capture
is substituted. `regression_comparison.py` is the visible comparison reader.

`admission.py` declares the profile-owned slot groups independently of the
engine. Each forbidden item and declaration spelling receives its own case, so a
first refusal cannot hide another item. The import coefficients `.23` and `.0031`,
and the switch slots' nonzero values, are supplied inputs and round-trip invariants.
The held-view witnesses exercise value, free-state and uncertainty writes through
previously fetched handles independently.

`generate_admission_inputs.py` supplies the native input vehicles from the same
analytical project declaration as `profiles.py`. It captures no engine output.
The native cases first accept a valid TCH input, then exercise public calculate,
fit, free-set and save admission after a raw token/block mismatch. Peak-specific
refusal is required; an unrelated exception cannot satisfy the gate.
