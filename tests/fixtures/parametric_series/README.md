# Parametric series references

The fixtures use authored inputs and a closed-form linear model. The three-point scan contains five observations per point with unit uncertainty. Its line-segment background is `3.25 * (1 - t) + b[k] * t`, where `t = (two_theta - 12) / 93` and `b = (7.75, 9.25, 6.5)`. The common endpoint may be fixed or free. The other endpoint stays local.

The residual at the stated truth is `0.03 * (k + 1) * (1, -2, 2, -2, 1)`. It is orthogonal to both columns of each point design. The least-squares optimum is therefore the stated truth. The squared residual sum is `14 * 0.03**2 * (1 + 4 + 9)`. The covariance is the inverse of the independently constructed design normal matrix, multiplied by that sum divided by observations minus free columns. The independent decimal reference in `tests/fixtures/report_units/iucr_reference.py` accounts for the public CSV precision.

The joint group fixture has three experiments in project order, with different input values. Its expected sharing and Free transitions follow the model contract. `cases.py` constructs these text inputs without importing a diffraction engine. The GUI fixture is regenerated with `python -m tests.fixtures.parametric_series.generate` in edi.

The noiseless cubic observations were generated with crysta `dfe20fb587a57853f14193876b5bb56f9c01e169` using `python -m tests.fixtures.parametric_series.generate_cubic` on 2026-11-26. The generator inputs in `cubic-truth.json` are the inverse-fit oracle. These observations verify inverse recovery only. The forward calculation is the pre-solver implementation.

The shared-scale scan reuses the first frozen cubic profile as a linear regressor. Its authored common scale is 2.5 and local endpoint pairs are (3.25 + k, 8.75 - k). A deterministic sinusoidal residual is orthogonally projected away from all three regressors before any fit. The independent design matrix supplies the covariance and degrees of freedom. Both fixed and free shared scale pass through save/reload before fitting.
