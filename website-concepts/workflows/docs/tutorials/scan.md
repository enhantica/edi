# Working with a scan

<p class="ed-doc-lead">Follow a changing sample through a sequence of measured patterns.</p>

## One template, many measurements

A scan uses one template experiment with a series of data files. The model describes what is fitted for each pattern; the scan mode determines its starting point.

## Choose the mode

**Sequential** refinement starts each fit from the previous fit's converged parameters. **Independent** refinement starts every pattern from the same initial parameters. Both process the scan serially.

## Inspect before fitting

Use the app's scan selector to inspect measured patterns. Check that the common model is appropriate across the scan, including the background, exclusions and range.

## Follow the parameter evolution

After fitting, inspect the results across patterns. A trend is easier to interpret alongside the individual fits and the patterns that produced it. Use [the same refinement guide](../guides/refine.md) for the shared analysis concepts.
