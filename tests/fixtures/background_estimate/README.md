# Independent background estimates

`reference.json` was generated from
[easyscience/diffraction-lib](https://github.com/easyscience/diffraction-lib)
`c0654956a1281f1ea3f3467c3367167f93edee18`, the fetched default branch
`origin/master` on 2026-10-20. Its corpus names HRPT/LBCO and McStas Si.
The input files and `data-index.json` come from diffraction's pinned data
commit `3ec801667904578ea39f1a4f4aa941866543a669`; the manifest retains each
input's upstream checksum and a checksum of the included arrays.

Source: [estimator](https://github.com/easyscience/diffraction-lib/blob/c0654956a1281f1ea3f3467c3367167f93edee18/src/easydiffraction/datablocks/experiment/categories/background/estimate.py),
[adapter](https://github.com/easyscience/diffraction-lib/blob/c0654956a1281f1ea3f3467c3367167f93edee18/src/easydiffraction/datablocks/experiment/categories/background/line_segment.py),
[corpus](https://github.com/easyscience/diffraction-lib/blob/c0654956a1281f1ea3f3467c3367167f93edee18/tests/integration/workflows/test_background_auto_estimate_corpus.py),
and [accepted method ADR](https://github.com/easyscience/diffraction-lib/blob/c0654956a1281f1ea3f3467c3367167f93edee18/docs/dev/adrs/accepted/background-auto-estimate.md).

The external environment used Python 3.14.6, NumPy 2.5.2, SciPy 1.18.0 and
pybaselines 1.2.1. The last three match the selected source's lock file;
the manifest also records these versions. To reproduce from this repository's
root, use Python 3.14.6 and a scratch environment outside the checkout:

```sh
mkdir -p ../background-reference
git clone https://github.com/easyscience/diffraction-lib.git \
    ../background-reference/diffraction-lib
git -C ../background-reference/diffraction-lib checkout --detach \
    c0654956a1281f1ea3f3467c3367167f93edee18
python3.14 -m venv ../background-reference/venv
../background-reference/venv/bin/python -m pip install \
    numpy==2.5.2 scipy==1.18.0 pybaselines==1.2.1
../background-reference/venv/bin/python \
    tests/fixtures/background_estimate/generate.py \
    --source ../background-reference/diffraction-lib \
    --output ../background-reference/generated
```

The manifest records this repo-relative reproduction command. Paths are
normalized from the authoring environment; numerical reference data is unchanged.
The generator loads the
upstream estimator unchanged, extracts and executes the upstream adapter's
`auto_estimate` method and its helper functions, and substitutes only point
storage and logging. It does not import either product. The adapter receives
the complete measured grid and included/excluded statuses, so its own
active-grid selection and intensity clipping execute. Both the raw and
clipped anchors are retained. Tests only read these files; they never import
diffraction-lib, SciPy or pybaselines.

The reference includes all three methods, with data-derived defaults and
with nontrivial overrides: width multiplied by 1.7, smoothing by 3.25, and a
seven-point cap. Those multipliers are test inputs, not physical constants.
SNIP's documented ignored-smoothing path is included. Peak windows come
from the independent estimator's detected peaks and inclusive
`ceil(width)` index windows on the active grid.

| Quantity | Absolute tolerance | Relative tolerance | Reason |
| --- | ---: | ---: | --- |
| Anchor positions, all methods | `1e-9` axis units | `0` | Same measured samples; only decimal-to-binary transport is allowed. |
| arPLS anchor heights | `1e-9` intensity units | `1e-6` | Allows double-precision banded-solver and iterative-weight rounding across implementations. |
| SNIP anchor heights | `1e-12` intensity units | `1e-10` | Direct window arithmetic requires no iterative linear solve. |
| FABC anchor heights | `1e-9` intensity units | `1e-6` | Allows the same banded-solver rounding as arPLS after classification. |
| Independently recomputed noise | `1e-14` intensity units | `1e-12` | The second-difference MAD is a short arithmetic identity. |

Anchor counts and order are exact for every method. The height allowances
are numerical equivalence bounds, not fractions of experimental noise.
No count mismatch or position drift is excused by a height tolerance.
The defaults are also exercised as explicit width/smoothing overrides,
while the frozen noise determines the reference's RDP anchor selection.
The public upstream call returns no metadata object, so these tests do not
require a new result API.

`project.py` writes the same measurements and exclusions into ordinary
projects with a zero-scale Si structure and two zero-height starting
points. Zero measured uncertainties, if any, receive `1e-12` solely to
make a valid loadable project; uncertainties are not estimator inputs.
The app projects are generated from this helper and reference manifest.
The model-guided property uses the existing `lbco-hrpt-s2` fitting project,
also published in edi as `pd-neut-cwl_lbco-hrpt_start-2`. Its background is
zeroed before calculation, then the weighted residual must decrease and
the model-guided result must differ from a data-only estimate.

## Saved estimation settings

`settings.py` materializes auto-mode project inputs from the same measured corpus
and unchanged independent anchors. One case uses derived SNIP defaults; another
uses the existing nontrivial arPLS override reference. No new numerical oracle
is generated. Recreate the app inputs from the repository root with:

```sh
python -m tests.fixtures.background_estimate.settings
```

The saved `background_estimate` category is a project contract: mode, method,
optional width, smoothness and point cap, and the calculated-model choice travel
with the saved points. Round-trip checks compare parsed values exactly. Automatic
results retain the method tolerances above; CLI, Python and app parity compares
identical points exactly. Manual mode preserves saved points.

In the consumer repository, `--freeze-cli` also captures the prior published
LBCO experiment and expected-output files once, refusing to overwrite them.
These are labelled REGRESSION PINS: they constrain the category addition to its
six settings and preserve other input lines, including the saved free points.
The published LBCO project records manual mode and retains every byte of its
existing expected-output pins. Auto-mode calculation and fit behavior use
disposable fixtures instead. These pins are not new physics references.


## Manual-settings serialization regression pin

`manual-bytes.json` is a **REGRESSION PIN**, generated by
`python -m tests.fixtures.background_estimate.manual_bytes --record` at its
recorded public repository commit (and linked engine commit for the consumer).
It keeps the original input and saved experiment digests alongside their new
digests. The generator refuses overwriting this receipt and proves that removing
exactly the canonical manual/arpls category and its separator reproduces the
original immutable digest. No other input or saved byte is admitted.

Before the extension, the LBCO byte witness required no estimate category. After
it, the witness requires the two declared category lines, preserving the full
file inventory and every other historical digest. Changed methods, modes,
missing, duplicate or extra declarations and re-pinned scientific-byte changes
are refused. The consumer also retains the original loop and correlation-fit
input pins through the same exact category projection. Existing expected fit
results remain unchanged; these receipts make no new scientific claim.


The app category/display input hashes are adapted with
`python -m tests.fixtures.background_estimate.adapt_oracles`. The generator
reads the retained public commit named in `app-oracle-bytes.json`, authenticates
the full before/after LBCO input bytes, and changes only the published input's
three hash entries. Every numerical value, free flag, loop, display expectation
and other source identity stays byte-identical. The separate editable-project
input retains its original digest. The receipt records both complete oracle
file digests and the repo-relative command; repeated generation is stable.


## Automatic-estimate lifecycle witnesses

The lifecycle gates constrain ownership and persisted state, not a new numerical
physics oracle. A nonzero LBCO crystal model makes repeated model subtraction
observable. Published background samples must equal the closed-form linear
interpolation of the visible saved points, with relative tolerance `1e-12` and
absolute tolerance `1e-9` counts. Those tolerances allow double interpolation and
transport rounding only. Point values, row identity, mode, file inventories and
unchanged-project bytes use exact comparisons.

The scan witnesses contain three different measured files whose independently
estimated anchor counts differ. The documented scan contract freezes the one
estimate of the template for all files. Both fitting modes exercise row lifetime,
failed predecessors, restart and completed-result resume. Native cases also run
under address and undefined-behavior sanitizers, including float-cast overflow.

Separate gates require a calculated auto project to reload without replacing its
points, and edits to position, intensity, free flag or row membership to select
manual before the first estimate or save. Empty and excluded measurements, and
explicit manual-to-auto transitions, exercise the same ownership rule. Invalid
numeric overrides must be refused before changing points, settings or files;
positive infinity and finite widths beyond the conversion range are included.

The `lifecycle-*` projects are **REGRESSION INPUTS**, generated once with the
linked engine SDK recorded by the public edi build, at commit
`c1a433d9a3090969cd4a4dca05ad8da2de1ca281`. Their hashes and author command
are recorded in `lifecycle-cases.json`. The native helper uses the full project
writer so stored calculated arrays are present; the narrower CLI calculated
block would hide the loader seam. Build and run from this repository root:

```sh
cmake -S tests/fixtures/background_estimate -B ../background-reference/build \
  -DCMAKE_PREFIX_PATH="$PWD/build/crysta-prefix"
cmake --build ../background-reference/build
python -m tests.fixtures.background_estimate.generate_lifecycle \
  --source docs/user/cli/pd-neut-cwl_lbco-hrpt_start-2/project \
  --engine-writer ../background-reference/build/save_auto
```

The generator refuses to overwrite an existing input. The independent method
references above remain unchanged; no estimator library runs inside these tests.


## Saved-auto provenance input

`saved-lifecycle.json` labels `projects/lifecycle-saved-auto` as a **REGRESSION
INPUT** from a separate native calculate/full-save author run with the recorded
linked engine SDK commit. It authenticates every byte of the original digestless
`lifecycle-auto` source, which remains unchanged, and records both saved digests,
points and output-file hashes. It makes no numerical physics claim.

Before: the CLI stability gate treated a file without provenance digests as
already estimated. After: the unchanged-project gate uses a calculated/saved
input with both digests, and requires exact points and digest retention. Files
without digests estimate at the first calculation, as the estimator design says.
The two-loader parity gate uses the same saved input. Generate once, from the
repository root, with the independently built native helper above:

```sh
python -m tests.fixtures.background_estimate.generate_saved_lifecycle \
  --engine-writer ../background-reference/build/save_auto \
  --engine-commit 3a2f73b1b99cc3b4548c32bc40c20bdde1a0d971
```

The generator refuses to overwrite the input or receipt. Existing independent
references, old state witnesses and numerical tolerances stay unchanged.

## Explicit reference profile and new defaults

All diffraction-lib equality calls and app reference projects explicitly select
`tolerance=2.0`, `in_peaks="drop"` and the recorded model setting. The frozen
anchors and the numerical tolerances above are unchanged. The helper's
`DEFAULTS` dictionary names this fixture profile, not the product defaults.

Separate properties cover the new product defaults: half-noise tolerance,
replacement outside peak windows, and calculated-pattern use off. A declared
point count is exact with `move`; the old cap remains tested with `drop`.
The saved category also carries `tolerance` and `in_peaks`. Blank overrides
remain blank; an explicit 0.75 tolerance is a nontrivial round-trip control.

The wider native properties independently compute vertical RDP proposals and
check every inter-anchor sample outside the frozen peak windows. Count,
order, endpoints and exclusion are exact. Segment error admits only the
requested tolerance plus 64 machine epsilons times max(1, curve magnitude),
covering interpolation rounding, not algorithm differences. A closed-form
line followed by a quadratic, with a period-three authored noise signal,
compares equal-length regions at SNIP half-window three. It requires denser
anchors where the known curvature is nonzero. No product output is a golden.

Calculated-peaks policy compatibility: the saved field now uses `auto`, `subtract`, or `ignore`.
The Boolean fields retained in the original inputs deliberately exercise legacy loading; expected
settings use the canonical tokens (`true` becomes `subtract`, `false` becomes `ignore`). Numerical
reference curves and anchors are unchanged. The settings reader understands both input spellings;
the policy round-trip gates additionally inspect raw saved tags and require canonical tokens.

The current saved guided and exact-nine-point inputs have been independently
calculated and saved again with row-content provenance that excludes fit flags.
Before, the guided input was digestless and the placed input included free flags
in its digest. After, their receipts identify the producer and complete saved
bytes; unchanged reloads must retain them. The original digestless lifecycle
input and older saved-state receipt remain historical inputs. Reproduce the
guided flow with `python -m tests.fixtures.background_estimate.generate_current_lifecycle
--engine-source-commit 3188231bb61f9594e06bbed8e39cb37393477672`.
