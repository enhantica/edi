# pd-neut-cwl_cosio-d20_scan-324f — provenance

The owner's scan that goes down AND up in one run (*"Use this for testing - it goes up and
down"*). Copied **byte-identical** from the owner's local project
`edi/tmp/projects/cosio-d20-scan-324f` (2026-09-25) — the `project/` tree, nothing else: 324 D20
patterns of Co2SiO4, `01_001`–`01_162` measured cooling from 497.379 K to 50.414 K and
`02_001`–`02_162` the same temperatures warming back, plus the project's own four `.edi` files.
Each file's SHA-256 is recorded in `tests/fixtures/c11_t62/scan-inputs.json`, taken directly from
the source tree; the copy matches it file for file.

Before the downward pass reproduced the sequential basin trap measured: every downward file from
340.723 K to 70.225 K failed, while the upward pass over the byte-identical files converged. Its
origin was a reflection at the 180° Bragg limit painting a pedestal over the high-angle data; with
crysta's generation limit fixed, both passes converge at all 324 files.

`expected.json` carries `n_free` — counted from the model's free parameters, an independent
reference — and the terminal record of this project's own fit as **regression pins** (`kind`
recorded per value): they gate drift, not correctness. The terminal record describes the last file,
`02_162` (497.379 K, upward): reduced χ² 4.805953672 after 4 iterations, measured by `python -m edi fit`
of this project on edi `5c0ddf9` linked against crysta `9c1caaec`, `OMP_NUM_THREADS=1` (after the
Bragg-limit fix and the frozen generation limit, crysta `8b95cccc`; 4.805622 before the fix, 4.806071 before
the freeze). The temperatures repeat between the two passes, so no `results[<T>]` key is unique and none is
pinned.

## Full directional acceptance

The terminal pin above checks CLI record drift only. It cannot establish the
downward branch at earlier temperatures. The complete numerical acceptance is
crysta, invoked explicitly with
`--backend edi-cli --project <this project> --output <new evidence directory>`
using edi's Python environment. It runs the real CLI on a fresh copy, requires
all 324 converged rows in original order, proves that each downward observation
is byte-identical to its upward partner, and compares all 162 pairs with a
two-sided absolute reduced-chi-square tolerance of 0.08. No independent-start
value or terminal value substitutes for this comparison. `per-temperature.tsv`
records every comparison; `evidence.json` retains every row, including on failure.

This uninterrupted fit exceeds the 5 s system-test bound (15.323 s at edi
`674cec5` consuming crysta `8d58b295`. It is an
offline acceptance command, not a newly added CI test or a costly shared fixture.
The paired-input check and comparison refusal tests run in CI within their tier
bounds. Frozen FullProf profile and downward-prefix controls remain in crysta;
no acceptance command executes fp2k.
