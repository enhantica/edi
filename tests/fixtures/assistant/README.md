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
positive project is frozen separately below. The scripting exercise's CIF, neutron data and instrument file are
retained as its inputs. The data-only extraction is fixture acquisition, not a production GPX reader or a
native-export sandbox.

Formula sources are GSAS-II's `getCWsig`, `getCWgam`, `getgamFW` and `getBackground`, plus its source data reader
and displacement factor in `GSASIIstrMath`. In particular `chebyschev` is a power basis while `chebyschev-1` is
the Chebyshev basis; Gaussian variance in centidegrees squared is distinct from a TCH Gaussian FWHM squared.
The nontrivial witnesses below freeze these conventions before converter implementation.

`reference/positive-gsas/` contains a new project created and calculated by unchanged GSAS-II source at
`c67a261f771a71461f6080a77efd91ab265abdf2`. `PROVENANCE.json` records input/output hashes, native kernel
provenance and units. `generate_positive_gsas.py` runs explicitly in that upstream runtime; ordinary edi tests
consume the frozen data offline. Its default output directory is the committed fixture directory, so pass a
private `--output-dir` when verifying regeneration.

This one-phase neutron project retains nonzero instrument widths, FCJ asymmetry, isotropic size and microstrain,
nonuniform isotropic displacement and nonunit O3 site occupancy. It declares a three-term `chebyschev-1`
background. The generated source is a new case; the unsupported tutorial is untouched. The source/pattern JSON
contains every measured point and its GSAS-II-calculated signal, plus the instrument, sample and phase terms
needed to detect unsupported input. Two fresh native generations produced identical scientific JSON excluding
the GPX hash, and identical mapping-witness JSON. GPX saved timestamps are not a scientific oracle.

`mapping-witnesses.json` freezes actual positive weights and reciprocal-square-root sigmas, Uiso and
`Biso = 8*pi^2*Uiso`, GSAS-II Gaussian variance and Lorentzian FWHM at two nontrivial angles, and three declared
background bases. Gaussian FWHM squared in degrees is `8*ln(2)*variance/10000`; Lorentz FWHM in degrees is
`gamma/100`. Fixed isotropic size/microstrain terms remain explicit: their centidegree Lorentz contributions are
`1.8*wavelength/(pi*size*cos(theta))` and `0.018*microstrain*tan(theta)/pi`. They cannot be silently dropped from
the forward-pattern comparison. These are independent GSAS-II/physical witnesses, not edi regression pins.

A production-supported bundle, faithful conversion/forward-pattern comparison, and native exporter invocation
under enforced hostile-input isolation remain open. Trusted generation does not complete native GPX acceptance.

The existing independent FullProf source family is
`knowledge/fitting/fullprof/pd-neut-cwl_cosio-d20_biso-tied/`. Its committed `PROVENANCE.md` supplies source
hashes, site/general multiplicities and the unequal-start shared-codeword shift example. Its existing scientific
bounds are unchanged. `reference/fullprof-affine/` now retains a concrete unequal-start source and real FullProf
8.40 output: only Co1's initial Biso changes from `0.98759` to `0.01000` in the existing `full-fit.inp`; both
sites retain codeword `181`. The native `.new` values `0.16557` and `1.14316` preserve the initial difference
`0.97759`, rather than forcing absolute equality. Its provenance records all input/output hashes and the exact
executable. `affine.dat` is the existing `cosio.dat` named in that provenance, not an additional data copy.
The persistent native run reached `Normal end`; the final interactive stdin EOF returns exit 24 as already
documented for this binary. FullProf conversion gates and positive/refused source cases remain a separate unit.

The offline desktop protocol gates use independently authored event/control fixtures based on the accepted
interface and the official [Responses function-call protocol](https://developers.openai.com/api/docs/guides/function-calling),
[subscription inference requirements](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference)
and [sign-in requirements](https://developers.openai.com/siwc/token-sharing-open-source/sign-in).
They do not authenticate an account, verify entitlement, or replace the required live walkthroughs. Native OIDC,
credential and provider-wire tests remain open until their deterministic transport seams are available.
