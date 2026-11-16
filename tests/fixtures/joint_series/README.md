# Joint series references

The small routing series has three points and two experiments. Its cell lengths and scales are authored in
`cases.py`; forward calculation creates observations from those inputs. Recovering those inputs is a round-trip
invariant, not an external intensity reference. Its experiment order differs from the data filenames' order, and
`0007` and `07` are distinct point keys. No fitted output supplies an expected value.

The ratio witness has two identical phases, so their occupied unit-cell masses and volumes cancel. For leader
scales `u=2`, `v=1` and member scales `t=3`, `t*v/u`, the second fraction is `v/(u+v)`. Uncertainty only in `t`
contributes zero variance. With `sigma(u)=0.04`, `sigma(v)=0.03`, `rho=0.5`, the quotient gradient is `(-1/9,2/9)`.
This is the Hill–Howard equation composed with the declared relation, using ordinary covariance propagation.

The moment witness uses the direct-axis unit vectors, Cartesian x along a and z along c*, polar angle from +z,
and azimuth from +x. Its monoclinic cell, signed components and supplied full covariance are authored inputs.
Central differences of that closed form provide the independent uncertainty reference.

The engine fixture copies `project` and `expected.json` from edi's
`docs/user/cli/pd-neut-tof_ncaf-wish-5bank_start-fullprof` at `7ed17b57213c4c8fbb1595a94b55794c64ec5fce`.
Only the project description changes the old fit verb to “fit”; the numeric inputs are unchanged.
That case's PROVENANCE identifies FullProf 8.40's converged five-bank input and saved run. The generator copies the
measured observations into one point with two banks for the PR gate and one hundred with five banks for the slow gate.
Only `kind: reference` atomic values from that file are correctness references. Engine regression pins in the same
file are retained for source fidelity and are not read by these gates. FullProf never runs in a test.

The standalone cross-bank witness has one structural cell, two scales and one width shared by an equality: four
independents. Its covariance reference is `(J.T J)^-1 * chi_square/(N-4)`, with J from central differences of the
calculation and the follower recomputed for every perturbation. It tests the single-structure powder path.

Scale is measured separately on the producer-to-view path; these fixtures impose no timing assertions.

Both PR witnesses use one point and two banks. The slow witness retains one hundred points and five banks.
Actual start vectors are observed at the native scan-driver boundary, with a template different from the first
successful point. The series-derived witness uses three points and two experiments; magnetic components follow
non-collinear functions of the cell parameter, so the magnitude and both angular errors are nonzero. Five separate
channels check the magnitude, polar angle, azimuth, shared phase fraction and relation follower at each point.
The reduced fixtures check fixed atomic references separately from fitted scale columns.
Live fitted checks precede mutation or adopting Save. Each series prefix retains its terminal fitted values and errors;
weighted calculation Jacobians provide a conditional covariance reference at those full-precision fitted seeds.
CSV pairs are independently rounded by ADR-0092's default decimal rule; derived `.edi` category tokens retain the
exact round-trip convention of ADR-0088 point 4 / ADR-0132 point 2. Reload expectations use persisted inputs and
persisted correlations. The angular reference identifies azimuths modulo one turn.

The native crysta probe finds the CMake build whose extension bytes match the imported extension, checks the linked
core's embedded source identity, and checks its headers against that committed source. Archive and header overrides
must match that selected build; timestamps cannot choose another subject. Baseline exports remain identifiable.


Review-5 persistence checks derive the post-adoption Hill–Howard value from rounded independent scales,
rounded marginals/correlations and six-digit fixed cells; equal pre-save volumes are not assumed to survive Save.
The supplied moment reload reference is transformed from the authored inputs/covariance, after separately checking
that every saved marginal and every correlation pair preserves that expectation. Corrupt written covariance cannot
become the reference. Legal CIF2 list cells are retained as single compound tokens for Gemmi scalar checks
(`tests/fixtures/cif2.py`, ADR-0097), including multiline, nested, quoted and commented lists.

Native preparation has one owner: `pixi run joint-series-prepare`. The consuming suite and runtime-measurement
entry points declare it; the direct producer Python-tier script also prepares before selecting the system tier.
The command has a 45-second envelope and a 30-second compiler deadline. It caches an executable with a receipt
binding selected extension/archive/header bytes and observer/preparation sources. The behavior fixture validates
that receipt and embedded source identity, then runs it; it never builds or repairs missing/stale artifacts.
Preparation cost is outside behavioral test cost, and cold preparation remains bounded rather than hidden in import
or collection. No test bound or breach exemption changes.


The owner decision `a2fe1e722` (2026-11-15) supersedes live-precision sequential carry: each point starts from
its preceding successful **written** row, also when multiple workers were requested. Worker count cannot create
chunk restart state in a sequential chain. Independent points still restart from the template. Start controls reject
both full-precision carry and chunk restart; orphan-tail recovery also compares uninterrupted and resumed outputs
exactly. The azimuth reference follows the ADR-0108 convention modulo one turn, represented in `[0,360)`.


Owner decision `6c4f7a9d9` limits the slow cadence witness to 100 points × the five actual NCAF WISH banks.
The per-PR witnesses use one point with two selected banks in both bindings. The generator refuses larger counts before filesystem generation; no larger synthetic scale target
is asserted or executed by these gates. Scientific series runs use the explicit slow cadence.

Local observer selection follows the loaded extension's nearest CMake owner, including nested or external
build directories; installed copies still require one unique byte-matching build. A local edi build resolves
its actual `crysta_DIR` package and linked SHA instead of assuming only the two exported CI directory names.
The two declared CI export layouts retain their relocated prefixes. The prepared observer checks the linked
core identity in both products. A stale embedded crysta source identity whose committed headers differ from
the selected source remains a refused preparation; reconfigure/rebuild that artifact before observing starts.

The full one-hundred-point, five-bank seeded witness is `tests/system/slow/seeded_series.py`.
It runs only through the named slow/nightly cadence. Its filename is outside default pytest discovery,
and the producer path is outside the bounded PR tier roots. The ordinary seeded cases retain one joint point
and two banks with real sparse observed bins and two fitted bank scales. Their module fixture validates the readonly
preparation receipt; every fit remains in its measured test body.
The first-case validation cost remains visible in the runtime receipt; no tier threshold changes.

`joint-series-seeded-prepare` has a ten-second envelope and calculates only the readonly fixed-profile
basis and stages real observed bins. Its receipt binds engine bytes, preparation code, FullProf input files
and every staged byte. The PR test copies that input, solves its weighted linear reference independently,
and performs its actual joint fit in the test body. Missing or changed preparation refuses; tests never
rebuild it. The PR suite declares this preparation; the producer’s `suite-pr` does so without building
the native system observer.
