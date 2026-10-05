# BEER independent reference

Source tutorial: diffraction-lib commit 0d9f10e412a0cd08d4dd0af95845dd9bb597dcdf,
`docs/docs/tutorials/calibrate-beer-ess.py`. Default calculator CrySPY 0.12.1;
library version 0.19.1, lmfit 1.3.4. `reference.json` records all versions,
commands, source archive URL/ref/digests, input/output digests, fitted values,
standard uncertainties and both fit-quality conventions.

The authoring run executed the tutorial's two joint fits once each. The first
fit auto-saved before the extractor failed on a string-valued space-group
parameter. Recovery loaded that saved result, including Edi rounding and
reversed bank order, and executed only the second fit. No completed fit was
repeated. This capture variation is explicit in reference.json; it is not a
fresh unmodified notebook output. The data archive was downloaded once;
rendering calls were omitted. No environment was created in either product.

The static raw Edi inputs and outputs are independent reference artifacts.
`capture_beer.py` freezes them; `generate_beer.py` transcribes the initial and
second-stage inputs into the current schema. The four optional zero-valued
size/strain descriptors absent from crysta's dictionary are omitted; their
zero contribution, every free profile field, cutoff, offset, both phases,
measured points and uncertainties, backgrounds, exclusions, joint weights
and cross-bank constraints are preserved. The original raw artifacts stay
unchanged.

Parameter comparisons use exactly one external standard uncertainty; no
parameters are excluded. The first fit includes forty background intensities;
the second fixes them and fits fourteen other parameters. Rwp has no reported
uncertainty, so the comparison allows five percent relative for independent
optimizer termination. The library's reported Rwp includes excluded rows with
zero calculation; `active_rwp` is separately derived by capture_beer.py only
from saved rows with calc_status=incl, matching the engine's fit-window metric.

Canonical project id: pd-neut-tof_ferrite-austenite-beer_joint. The CLI and
verification page use these committed measured inputs and independent values.
