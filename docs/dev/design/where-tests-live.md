# Where tests live, and what measures them

edi's placement decisions, recorded with their reasons so later tasks key to a decision
rather than a diff. The claim taxonomy is §P0.1, ratified: *a claim lives at the lowest
layer that can observe its subject* — L1 C++ unit, L2 public-surface pytest, L3
cross-engine parity (never moves down), L4 byte-identity (never moves down). The declared
L3/L4 claim-layer map lives in the packet (§P1.2e); this page records where edi's tests
live and which instruments measure them.

## The tiers: repo × category × language

`tests/{unit,integration,system}/{py,cpp}`. Cross-engine parity lives at system level and reads
paired corpus references; documentation pages are not test cases. Visibility is the
`_hidden.py` suffix in any tier, declared in the committed `tests/hidden-surface.txt` (the
deny authority reads it at `HEAD`); the old `tests/hidden/` home retired in the phase-1
move. C++ probe sources live in `tests/unit/cpp` and are **pre-built by
`core-build`** as default targets (`build/ci/core/*`) — never cmake-compiled ad-hoc inside a
test or fixture (the workers-cannot-share-a-build rule).

**The app tier `tests/unit/app` ([ADR-0015](../adrs/0015-edi-app-stack.md)):** Qt Quick Test cases
(`tst_*.qml`) with their C++ support sources (`test_*.cpp`), compiled into the runner
`edi_app_tests` over the same `edi.app` module and engine setup the host uses — never linked into
`edi_app`. `pixi run -e app app-build` builds the runner; `pixi run -e app app-test` generates the
separate-surface references through the unchanged Python surface (default environment), runs it, and
refuses a run that executes no case. The UI test (`app-ui-test`) compares the demo mode's page images
with the one committed set under `docs/dev/design/app-screenshots/edi/`. `app-gates` runs the app
build, qmllint, qmlformat, the tier and the UI test; `verify-quick` and `verify-full` reach it through
a cross-environment dependency, so the default environment stays Qt-free.

## The gates: the owner-ruled cadence (2026-08-28)

- **Nothing runs per commit.** The former per-commit inner loop and its 300 s wall-clock
  ceiling are retired: a whole-run total is an aggregate time gate under another name, decided
  by host variance, and only per-test tier bounds are checked (`tests/per-pr-runtimes.tsv`,
  the ratchet in `tests/threshold-breaches.md`; every collected test carries a banked runtime
  and the audit fails closed on an unmeasured one — an unchanged collection is never
  re-measured, added nodes are measured once by `pixi run per-pr-measure`).
- **`pixi run verify-quick` runs ONCE before handing to review** — the static checks, the
  core build, the audit and the `quick` group (unit/integration/system + the C++ tier; what CI
  runs on a pull request).
- **`pixi run verify-full` (== `pixi run verify`) runs ONCE when ready to merge, after the
  accept** — the same checks with the `full` group, the notebooks and the strict docs build;
  `tools/ci/local-ci.sh` runs it (`merge-tasks`), in lockstep with the workflow's non-PR path.
  The named irreducible residual is the macOS leg.
- CI on PR runs `group-quick`; `group-full` runs on merge (`push: main`) — a two-platform
  double-check on top of the local cadence, never a different cadence. Both groups select the
  same tiers (`tests/test-groups.json`). CI runs that selection as parallel jobs per platform
  (owner, 2026-10-08): the C++ unit tests, `unit` and `integration` in the `core` job
  (`core-tests`), and `system` in three `system` jobs (`system-tests-part <part>`), which
  pytest-split balances by the test times recorded on `main`; a test with no recorded time counts
  as the average, so nothing is listed by hand.

## The fitting corpus: edi is a consumer, never a home

The corpus lives in crysta (`tests/fitting`) and reaches edi through
`EDI_CRYSTA_CORPUS_ROOT` or the floated checkout (`build/crysta-src`, built by
`tools/ci/build-crysta.sh` from the live crysta `main` head) — resolved by `conftest.corpus_case_dir`, which fails closed on a present root
missing a requested case. Nothing fitting-shaped lives under `edi/`
(`examples/refine-*` retired with the 8d disposition; the CW template is corpus case
`lbco-hrpt-cwl`). The rules that follow:

- **No test owns its fit** (I13): a live fit outside the corpus runs a manifest-named corpus
  case in place — the cheapest admissible per behaviour class. Measured constraints worth
  knowing: the cheapest edi-loadable single is `cosio-d20-cwl` (CW); **the cached surface is
  TOF-only by contract** (it refuses CW loudly), so cached-refit tests ride
  `seam-ncaf-wish-2bank`-class TOF vehicles (`seam-si-sepd-s1`).
- **The ONE live joint fit per suite run is the F-live producer** —
  `conftest.session_joint_fit` on `ncaf-wish-3bank-s5`, run inside the preloaded native I/O
  observer with callback history and the post-fit write-back table in its transcript;
  consumers assert on the shared result, never re-fit.
- **Bounded fits (F-bound) declare their bound in project data** —
  `_minimizer.max_iterations` in the analysis block (edi's CLI deliberately has no iteration
  flag); the loader fails closed on a malformed bound.
- **Recorded expectations (F-rec) are corpus-record goldens** (`goldens/*.json` in the case,
  provenance-stamped, regenerated only as a reviewed act); cross-surface expected tables come
  from the like-config crysta CLI record, and per-side convergence pins ride the case
  `expected.json`'s `edi` overlay.

## What measures the tiers

- Python: coverage instruments arrive with the unit-6 work and raises them; until then the
  per-PR audit (runtime totality) and the wall-clock gates are the measured authorities.
- C++: the probes are correctness gates riding `core-build`; the C++ unit-coverage tier is
  unit-6 work (port of crysta's clang `-O0` + LLVM shape).
- The docs build is a session-shared strict render (`conftest.session_docs_build`) — one
  mkdocs `--strict` run per suite session into a tmp site dir, consumed by the docs gates.

## Honest limits

- The pinned-corpus transition: a case added in a live crysta cycle reaches edi only at the
  ship-time pin bump; until then its consumers fail loudly at the pin (never a silent skip).
- The E02 cross-engine comparison belongs in `tests/system/py` and consumes a
  manifest-declared corpus pair through a public reference loader.
- The macOS CI leg has no local equivalent anywhere in the org; the first push of a branch is
  an experiment the pre-push parity sweep shrinks but cannot eliminate.
