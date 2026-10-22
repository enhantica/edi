# FullProf authoring record

FullProf fp2k 8.40 (Feb2026, ILL) was run at authoring time: 2026-10-22T22:11:09.226467+00:00.
Tests read these committed outputs and never invoke fp2k.

Start: `docs/user/cli/pd-xray-cwl_lam7o3-p021/project`. `reference.json` binds every input and output byte.
No fitted values seed the start, and no parameters are fixed or released in stages.
Input triples retain positive sigma; excluded and sigma-zero points are omitted.
The range remains the background domain. FullProf Ins=10 reads six header lines.

Reproduce with `python tests/fixtures/example_catalogue/run_fullprof.py --case pd-xray-cwl_lam7o3-p021 --cycles 1000 --epsilon 0.1 --executable /path/to/fp2k --logs /persistent/logs`.
The executable receives the PCR basename and blank responses on standard input.
A terminal EOF after completed output is not a numerical failure. Logs are retained.

`fit.pcr` uses Pcr=2. `fit.new` is the independent fitted model.
Its fixed twin zeros every value/code field in that emitted file.
Finite output: True. Converged: True.
Fitting cycle budget: 1000; shift tolerance epsilon: 0.1.
The output parameter table and its code-index mapping are retained.
Rwp uses all-point least-squares factors, pooled with observed weighted sums.
The scan rows claim only their single template fit.

The explicit type-2 dispersion records use Sasaki (1989), KEK Report 88-14.
The independent table brackets and their source digest are frozen in
`tests/fixtures/example_catalogue/synchrotron-dispersion.json`; the receipt binds that file.
Interpolation is linear in photon energy at the committed 0.207109 A wavelength.
FullProf retains its normal form factors; only Dfp and Dfpp are supplied.
[FullProf manual, line 12, ITY=2](https://www.ill.eu/sites/fullprof/downloads/Docs/FullProf_Manual.pdf)
documents the lower-case symbols and the synchrotron correction route.
[Sasaki tables](https://www2.kek.jp/imss/pf/tools/sasaki/scatfac/scatfac.html).

The archived `strict-shift-attempt` used epsilon 0.001 and 1000 cycles
from the same start but did not converge. The primary reference uses
the established epsilon 0.1; no fitted result seeds another fit.
