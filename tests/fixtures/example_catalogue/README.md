# Catalogue acceptance references

`catalogue-selection.json` transcribes the owner's chosen cases and order. It is
independent of the registry, metadata generator, app bundle and documentation.
`freeze_comparison_bounds.py` captures the explicitly named pre-disposition commit
into `comparison-bounds.json`. These are tolerance-policy retention pins: every
other bound stays exact when the six decided LATP values become
labelled regression pins. FullProf still supplies the correctness values.
The three single-crystal cases freeze their first committed comparison bounds
at `fe080a38`, separately from the older powder disposition. Their values are
checked against the F-squared FullProf reports and independent beta/occupancy
unit conversions; Tb's different extinction model supplies regression pins.
`capture_retention.py` freezes the original project and expected-result bytes;
`retained-projects.json` is checked without needing historical Git objects in CI.

`agreement-factors.json` is a closed-form witness for
`tools/comparison/fit_quality.py`. Its testable interface is
`agreement_factors(banks, n_free)`, returning the named `r_p`, `r_wp`, `r_exp`,
`reduced_chi_square` and `n_points` fields. Each bank supplies observed and
calculated intensities, sigma, and an included-point mask. Pool the sums before
computing a factor. Count the shared free parameters once. Reject non-finite
included values, non-positive included sigma, unequal arrays, no observations,
and a free count that leaves no degrees of freedom. Excluded points contribute
neither residual nor point count. These are the comparison page's formulas,
with a public, small arithmetic seam so the production calculation is exercised.

`fullprof_inputs.py` converts a committed example to FullProf's documented PCR
records. `run_fullprof.py` is an authoring command, never executed by a test.
It preserves the start and free set. Sigma-zero and excluded observations are
omitted from the input triples, retaining every background anchor. Ins=10's six
header records are present. The original range remains the Chebyshev domain.
FullProf's fitted `.new` is projected to a calculation with all codes zero.
Output presence alone is not success: non-finite output, missing convergence,
and any failed start-pattern agreement leave the case open.

The diffraction-lib comparison records use
`knowledge/comparison/<case>/diffraction-lib/reference.json`: `program`,
`model_compatible`, and a nonempty `reason` for incompatible models. The LBCO
simulation witness also pins `start.npz` in `artifacts_sha256`; that array file
contains `x` and `calculated`. It is calculated once by diffraction-lib at the
committed simulation model. BeBa rows name their TCH-versus-mixing-eta mismatch;
they cannot present their minima as agreement on one common model.

`finalize_fullprof.py --logs <authoring-log-directory>` commits the actual
convergence and finite-output evidence, parameter table, code-index mapping,
all-point least-squares Rwp and fitted-twin digests. Repeat `--logs` for separate
authoring batches. Missing convergence keeps the minimum gate open. A finite
last cycle alone does not establish convergence.

The authoring runner accepts `--cycles N` to increase the computational budget from
the default 200 cycles without changing the start, free flags or convergence settings.
The receipt reads that budget from the actual PCR input. A fresh run always starts
from the committed project; no previous `.new` seeds a fitting run.

The synchrotron LaM7O3 reference supplies explicit type-2 anomalous corrections.
`freeze_dispersion.py --table /path/to/cctbx/reference/sasaki/fpwide.tbl` freezes
the original Sasaki (1989), KEK Report 88-14 table brackets and their source hash.
The independent input checks reconstruct energy-linear interpolation at 0.207109 A;
FullProf receives lower-case species, Dfp, Dfpp and ITY=2 as its manual specifies.
No crysta dispersion function supplies these reference values. Other references
keep their established FullProf table settings.

`--epsilon` records an explicit FullProf shift tolerance when diagnosing a reference.
The LaM7O3 tighter-tolerance attempt is retained under `strict-shift-attempt` in both
reference homes; it exhausted its budget and is not the converged minimum reference.
The primary run retains the established epsilon 0.1, with all starts and free flags unchanged.

`continue_synchrotron.py --executable /path/to/fp2k --logs /persistent/logs` checks
one separate FullProf self-continuation. Its receipt explicitly labels staging,
binds the source `.new`, and keeps all thirty-nine free parameters. The emitted
three-column cycle field cannot represent 1000 (`***`), so the diagnostic writes
a valid 200-cycle field before running. Its outputs and fixed twin live under
`continuation`; they do not replace the primary reference from the committed start.
