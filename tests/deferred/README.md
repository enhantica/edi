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
