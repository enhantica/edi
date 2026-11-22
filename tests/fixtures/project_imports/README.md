# Project import inputs

`cryspy-pbso4.rcif` is the unchanged PbSO4 functional-test file from cryspy.
The adjacent JSON records its snapshot, Git blob and SHA-256. Regenerate the copy
and licence with `python generate_cryspy_reference.py /path/to/libraries`.

The import checks read the source cell, sites, instrument and measurements with
Gemmi. They stop before cryspy's ragged calculated-output loop; the frozen input
file itself is unchanged.

`metadata.gsas.json` is an authored GSAS-II text-bundle input. Its nonzero values
exercise parameter metadata through import and native save/reopen. It is not a
calculated-profile reference.
