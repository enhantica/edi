# Deferred YAP comparison

The constant-wavelength profile task owns the original Npr=5 YAP CLI project,
its verification page and the agreement gates preserved in
`py/yap_agreement.py`. The preserved module has no test-file prefix, so the complete test inventory
does not collect it. No assertions or tolerances were removed
from the three preserved functions; none is skipped or marked as expected failure.

Restore these functions to the system tier, their fit-site declaration and
runtime rows when that task activates them. The reference parser, digest /
occupancy checks and YAlO3-only calculation remain active. FullProf is never
run by a test.


# Deferred scan scale checks

`py/scan_scale.py` preserves the 100000-file optimizer run and its four checks
for memory growth, per-file timing, read-ahead and virtualized lists. It has no
test-file prefix and is outside the declared quick/full group paths. There are
no skip or expected-failure markers. Restore it to a scheduled nightly tier
when that runner is available; its assertions and numerical limits are unchanged.

Temporarily disabled since 2026-10-08, pending a scheduled nightly tier
with a hosted-runner budget.

The active module retains its 162-file worker checks, 20-file lazy-read checks
and chart thinning. The latter uses a separately prepared CSV projection and
does not run the 100000-file optimizer.
