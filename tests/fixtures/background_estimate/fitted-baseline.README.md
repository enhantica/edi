# Free Auto background fit lifecycle inputs

The measured CoSiO D20 input and structural model come from the public
[Edi example](https://github.com/enhantica/edi/tree/550e48422a66a060f9ef35997ad060a00187d973/docs/user/cli/pd-neut-cwl_cosio-d20_start-4/project).
The manifest hashes its experiments, structures and analysis. Descriptive metadata
is replaced by neutral authored metadata; README is omitted from project copies.

These are **regression inputs**, not physics correctness references. Only the
background is free: nine line-segment points or three coefficients. The visible
generator settles the default calculated-peaks Auto policy before freezing its input, saves the initial Auto input, then fits an identical
Manual control for at most three iterations. The saved Manual results are labelled
**regression pins**. Python gates fit live Manual twins; app Manual controls validate the labelled regression pins; no convergence result
or scientific coefficient is treated as independent truth.

Generate once, from the Crysta repository, with its Python surface available:

```
python -m tests.fixtures.background_estimate.generate_fitted_baseline --module crysta --source tests/fitting/cosio-d20-s4/project --engine-source-commit 3188231bb61f9594e06bbed8e39cb37393477672
```

The same generator accepts `--module edi --source docs/user/cli/pd-neut-cwl_cosio-d20_start-4/project`
in Edi. The manifest records the actual module, engine stamp, compiled-binary hash,
all settings and every project-file hash. The three prepared projects and manifest
are copied byte-for-byte between products; no generator runs in a gate.
The shifted measured input keeps the axis and uncertainties and adds exactly
125 counts to each measured intensity. The polynomial uses the FullProf coordinate x/80 - 1 (origin 80 degrees);
Chebyshev domain is [8.0953, 149.7953] degrees, authored before estimation.

Live Manual/Auto equivalence and stored-curve checks allow 1e-11 relative plus
1e-8 absolute error for floating arithmetic and decimal serialization. The app's labelled Manual regression pin, also checked by its live Manual control,
allows 1e-9 relative plus 1e-7 absolute for native compiler differences. Both are much smaller than the actual fitted changes in the
manifest. Retention on a later in-memory calculation is exact, including row
identity; raw fit quality is not the subject of these tests.

The current authoring run supersedes the earlier saved series digests, which did
not include the type and origin/domain. It runs separately from the gates, then
checks that loading and calculating each saved Auto input preserves every free
row. Numerical input rows and the labelled Manual-fit regression pins are kept;
only the series inputs digests and producer provenance change. Free flags are
fit settings and do not invalidate the saved row-content digest.

The separately labelled `fitted-auto-fast-*` app lifecycle inputs keep every
fourth measured row and the last row (356 of 1418), then independently settle
Auto, free the background, save, reload and calculate before freezing. They
serve mixed-worker, type-change and Undo invariants within the existing time
limit. The full-data Manual-fit regression pins and all physics references stay
unchanged. `app-lifecycle.json` records every source/output hash and producer.
Reproduce with `python -m tests.fixtures.background_estimate.generate_app_lifecycle
--engine-source-commit 3188231bb61f9594e06bbed8e39cb37393477672`.
