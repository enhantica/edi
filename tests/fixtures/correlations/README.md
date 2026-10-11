# Parameter correlations

Run `generate.py <diffraction-lib checkout>` once when authoring. Tests read the
committed outputs and never execute the reference library or this generator.

The polynomial examples use unit-weight observations at t = 0, 0.1, …, 0.8,
with x = 40(1+t) and y = 5 + 2t + 3t² plus projected alternating noise. The
free columns are the first one, two or three powers of t. The covariance is
the inverse of the normal matrix; its scale cancels when normalized.
`reference.json` records the source hashes and source revision.

`reference_methods.txt` contains the covariance projection and heatmap methods
extracted from diffraction-lib at authoring time (BSD-3-Clause, EasyScience
contributors). The projection and upper-triangle storage are invoked directly.
The user-facing plot facade uses a minimal frame adapter and its white theme;
theme-sync is omitted. Its lower triangle and blank diagonal are captured in
`heatmap.json`, the actual Plotly figure returned by the reference facade.
`heatmap.svg` renders its cells, labels and borders on white; it is a geometry
reference, not a screenshot of diffraction-lib's entire host application.

`loop-*.edi` uses diffraction-lib's five storage columns, upper-triangle pairs,
normalized parameter identities and coefficients. The tolerance in the fit
checks is 2e-4 absolute, allowing the engine's numerical Jacobian error without
admitting a sign change or missing cross-covariance.

The inputs derive from the existing constraint-covariance corpus vehicle:
the same structure, instrument and polynomial background, with the constraint
removed and one, two or three coefficients selected independently. The fit-site
registry declares these disposable variants against that corpus case.

The sequential and independent inputs retain this same polynomial vehicle and
fit two scan files. `scan-reference.json` freezes the covariance projection for
each file's measured grid separately. The second grid spans negative and positive
t and uses different polynomial coefficients, so its least-squares solve is real
even after sequential seeding. Its base/ramp pair is positive and base/curve pair
negative; both signs differ from the first experiment. Reusing the last matrix
for both experiments therefore cannot satisfy the reference. The core gate checks
all saved pairs and unchanged analysis bytes on reload. The app actor checks the
association by switching 0 → 1 → 0 → 1 before saving and 1 → 0 → 1 → 0 after loading.
The Qt actor is authored separately from the executed core proof; its execution
must be reported explicitly when an app runner is available.
