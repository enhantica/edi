# Catalogue acceptance references

`catalogue-selection.json` transcribes the owner's chosen cases and order. It is
independent of the registry, metadata generator, app bundle and documentation.
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
