# Independent assistant references

These are upstream inputs and external calculated data frozen before edi's converter exists. They do not
establish live provider access or a working native GPX import.

`reference/downloads.json` records each acquired URL, byte count and SHA-256. `upstream-revisions.json` records
the resolved GSAS-II and tutorial repository heads. The `.txt` source copies preserve the downloaded Python
bytes without making foreign source part of edi's Python test/runtime code. GSAS-II's licence is retained in
`reference/GSASII-LICENSE`.

This product includes software produced by UChicago Argonne, LLC under Contract No. DE-AC02-06CH11357 with the
Department of Energy.

The original [CIF tutorial project](https://advancedphotonsource.github.io/GSAS-II-tutorials/CIFtutorial/data/)
is `NXPbSO4.gpx`. The independent source is a GSAS-II saved project, not an edi conversion. Its neutron
histogram contains measured two-theta, intensity, weight, calculated intensity, background and residual arrays.
`extract_gsas_reference.py` extracts them with `pickletools` opcode inspection: globals and reductions become
inert records, and no function or class named by the file is called. It accepts only the frozen file hash.
Run it with edi's pinned Python to regenerate `reference/gsas-tutorial-data.json`.

The saved calculated array is a forward-pattern witness for that exact upstream model. The source has nonzero
histogram strain, nonzero sample displacement and another X-ray histogram. It is an explicit unsupported case
until those fields are mapped; clearing them would invalidate the saved pattern. A simpler GSAS-II-produced
positive project, its independently calculated pattern and the supported bundle remain required before converter
implementation. The scripting exercise's CIF, neutron data and instrument file are retained as inputs for that
work. The data-only extraction is fixture acquisition, not a production GPX reader or a native-export sandbox.

Formula sources are GSAS-II's `getCWsig`, `getCWgam`, `getgamFW` and `getBackground`, plus its source data reader
and displacement factor in `GSASIIstrMath`. In particular `chebyschev` is a power basis while `chebyschev-1` is
the Chebyshev basis; Gaussian variance in centidegrees squared is distinct from a TCH Gaussian FWHM squared.
Nontrivial numeric witnesses and supported-background mappings remain an open reference unit.

The existing independent FullProf source family is
`knowledge/fitting/fullprof/pd-neut-cwl_cosio-d20_biso-tied/`. Its committed `PROVENANCE.md` supplies source
hashes, site/general multiplicities and the unequal-start shared-codeword shift example. Its existing scientific
bounds are unchanged. FullProf conversion gates and positive/refused source cases remain a separate unit.

The offline desktop protocol gates use independently authored event/control fixtures based on the accepted
interface and the official [Responses function-call protocol](https://developers.openai.com/api/docs/guides/function-calling),
[subscription inference requirements](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference)
and [sign-in requirements](https://developers.openai.com/siwc/token-sharing-open-source/sign-in).
They do not authenticate an account, verify entitlement, or replace the required live walkthroughs. Native OIDC,
credential and provider-wire tests remain open until their deterministic transport seams are available.
