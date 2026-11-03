# Estimating the background

A line-segment background is a list of points, and a polynomial or Chebyshev background a list of terms. Instead of
setting them by hand, edi can estimate them from the measured pattern: it finds a smooth curve under the peaks, then
keeps the few points a straight line between them needs to follow it, or fits the terms to it, adding terms until the
series follows the curve closely enough.

## In the app

On the Experiment page, the **Background** group's **Estimate** button replaces the points or terms with an
estimate; Undo brings the old ones back. The **estimation mode** beside the type says whether the points or terms
stay as they are and can be edited (manual) or are estimated again whenever the measured data or the settings change
(auto). In auto mode the table only shows them: choose manual to edit them. You can still free or fix a value from its
context menu.

The settings are in the **Extra** tab's **Background** group. Leave a field empty to let the estimate choose; the
grey value is what it would use, and a box set to `auto` shows in grey what auto chose (`auto · arpls`).

| Setting | What it does |
| --- | --- |
| calculated peaks | `auto`, `subtract` or `ignore`: what the estimate does with the calculated pattern's peaks |
| anchor points | line-segment: the number of points to place; the tolerance decides when empty |
| max terms | polynomial and Chebyshev: the most terms to use, up to 30; 12 when empty (a polynomial stops at 6) |
| baseline method | `auto` (arpls), `arpls`, `snip` or `fabc`: how the curve under the peaks is found |
| peak width (points) | the width of a peak in data points; measured from the data when empty |
| curve smoothness | how stiff the arpls or fabc curve is; derived from the width when empty; not used by snip |
| noise tolerance | how far the background may stray from that curve, in units of the noise; 2 when empty |

**Calculated peaks.** Where peaks overlap, the data never come down to the background, so an estimate from the
data alone sits too high. Subtracting the calculated peaks first fixes that, but only if the model is close: with a
wrong wavelength or scale the calculated peaks are in the wrong places or the wrong size, and subtracting them does
harm. `auto`, the default, subtracts them only when subtracting them leaves at most 1% of the points below three
times the noise, which calculated peaks in the wrong place or too strong do; the line under the fields says what it
chose and gives that share. `subtract` and `ignore` decide it yourself.

## A good order

1. Load the data and estimate once at the start. The model is still rough, so `auto` usually ignores it, and the points
   come from the data alone.
2. Fit the structure and profile with the points fixed, or with their intensities free.
3. Before the last fit, estimate once more. With a model that now matches the data, `auto` subtracts the calculated
   peaks and the points sit lower where peaks overlap.

## In Python and the project file

The settings are saved in the experiment's `_background_estimate` category, so a project carries them:

```
_background_estimate.mode manual
_background_estimate.use_model auto
_background_estimate.tolerance 2
```

The same settings are on `experiment.background_estimate`, and an estimate can be run directly:

```python
experiment = project.experiment
experiment.background.auto_estimate()                # with the project's settings left at their defaults
print(experiment.background_estimate.model_choice)   # 'subtract' or 'ignore'
print(experiment.background_estimate.model_reason)   # why
experiment.background.auto_estimate(use_model='ignore', tolerance=3)
experiment.background_estimate.max_terms = 8         # for a polynomial or Chebyshev background
```

With `mode auto`, every calculation and fit first estimates again when the data or the settings changed, also from
the command line.
