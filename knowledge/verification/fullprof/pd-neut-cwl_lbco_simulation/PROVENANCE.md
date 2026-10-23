# FullProf authoring record

FullProf fp2k 8.40 (Feb2026, ILL) was run at authoring time on 22 October 2026.
Tests read these committed outputs and never invoke fp2k.

Start: `docs/user/cli/pd-neut-cwl_lbco_simulation/project`. `reference.json` binds every input and output byte.
No fitted values seed the start, and no parameters are fixed or released in stages.
Input triples retain positive sigma; excluded and sigma-zero points are omitted.
The range remains the background domain. FullProf Ins=10 reads six header lines.

Reproduce with `python tests/fixtures/example_catalogue/run_fullprof.py --case pd-neut-cwl_lbco_simulation --executable /path/to/fp2k --logs /persistent/logs`.
The executable receives the PCR basename and blank responses on standard input.
A terminal EOF after completed output is not a numerical failure. Logs are retained.
