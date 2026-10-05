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
The renamed TCH and FCJ gates compare against it only on its recorded platform.
A different platform needs its own pre-change capture; absence fails closed.
