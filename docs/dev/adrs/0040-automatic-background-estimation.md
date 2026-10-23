# 0040. Automatic background estimation

- **Status:** Accepted
- **Date:** 2026-10-20
- **Implementation:** ✅ Implemented
- **Priority:** Medium

## Context

A line-segment background is a list of points placed by hand, and placing them well is hard: a point on a peak
pulls the background up into it, and where peaks overlap the pattern never comes down to the background at all.
diffraction-lib answers this with `LineSegmentBackground.auto_estimate()`. Its accepted ADR,
`docs/dev/adrs/accepted/background-auto-estimate.md`, fixes the method: a background curve estimated under the peaks
(arPLS by default, or SNIP or FABC), thinned to points that keep both ends of the pattern and never sit on a peak,
with the peak width, the noise and the smoothing derived from the data.

The app's Background group has shown a disabled Autodetect button since ADR-0017 §4, in the place this action
takes.

## Decision

1. **The engine estimates; edi reads its own model.** `edi::estimate_background` (`core/include/edi/
   background_estimate.hpp`) hands the engine the experiment's measured pattern on its whole axis, its excluded
   regions and, when the experiment holds one, its last calculated pattern and background. The engine computes the
   points; edi keeps no estimator of its own. The calculated pattern is used even when it is out of date, as in
   diffraction-lib: subtracting the calculated peaks stays right after the background changes.
2. **The points are an ordinary edit.** An estimate replaces the line-segment points with new ones numbered `1`,
   `2`, … and fixed, through `Edit::background_estimate`, the one write door every edit takes. A polynomial or
   Chebyshev background gets terms instead (the owner, 2026-10-20): the engine fits the coefficients, orders 0, 1,
   … each named by its order, and fixed, to the same estimated curve outside the peaks, adding terms until the series stays within the
   tolerance there or `max_terms` (blank 12) are used, and sets the origin or domain to the middle and range of
   the included data when the experiment declares none. So a file in auto mode may leave out a polynomial's
   origin or either end of a Chebyshev domain, and both loaders read it; a manual file must declare them, and a
   save always writes them. An experiment with nothing measured keeps its background.
   Every term row carries an `id`, as every point and every other loop row does (the owner, 2026-10-20): a file's
   `_background` term loop declares `_background.id`, and the loader refuses one without it. Every committed project,
   fixture and example was rewritten to carry it, with the row ordinals a term read without an id took before, so
   the names of their coefficients did not change. Python's `PolynomialTerm` has `id`, assigning it renames the
   term; the app's terms table shows it before the order, editable, and **Id from order** names every term by its
   order, as **Id from position** names the points.
3. **Python mirrors diffraction-lib.** `experiment.background.auto_estimate(method='auto', width=None,
   smoothness=None, n_points=None, tolerance=None, in_peaks='move', use_model='auto', max_terms=None)`,
   `experiment.background.type` and `experiment.background.show_supported()` have diffraction-lib's names and
   refusals; `use_model` also takes diffraction-lib's `True` and `False`, read as `subtract` and `ignore`, and
   `in_peaks='drop'` with `use_model='subtract'` gives diffraction-lib's estimate. Warnings reach Python as `UserWarning`; the
   one-line summary goes to the `edi` logger.
4. **The settings live in the project** (the owner, 2026-10-20). An experiment's `_background_estimate` category
   declares `mode` (`manual` or `auto`), `method`, `width`, `smoothness`, `n_points`, `tolerance`, `in_peaks`,
   `use_model` and `max_terms`; a blank item is its default or is derived from the data, and only declared items are written. The
   points stay saved too, so a project reads on its own and manual mode starts from the last estimate. The loader
   and the setters refuse the values the engine's loader refuses (a width, smoothness or tolerance must be positive
   and finite, the width at most 100000 points, `in_peaks` `move` or `drop`, `max_terms` 1 to 30), and edi saves through the engine's
   writer, which writes the mode in force. The engine's defaults depart from diffraction-lib's where measured
   (2026-10-20): a point that falls on a peak moves to the nearest point off it, and segments that still miss the
   curve get more points, rather than being dropped; heights are clipped to the measured pattern averaged over
   about one peak width rather than to each noisy value; and `n_points` is the number of points rather than a
   maximum. The tolerance stays twice the noise and `use_model` stays on, as in diffraction-lib: the owner chose
   them from the measurements below after half the noise placed 31 to 150 points on the Co2SiO4 D20 and LBCO
   HRPT projects (their own points are 14 and 5). After one fit, each point set fitted with only its intensities
   free, with N the fitted points, k the points plus the project's other free parameters and BIC = chi2 + k ln N:

   | project | use_model | tolerance | points | chi2 | BIC |
   |---|---|---|---|---|---|
   | Co2SiO4 D20 (N 1418) | off | 2.0 | 9 | 6631.2 | 6907.0 |
   | Co2SiO4 D20 | off | 1.0 | 29 | 5738.2 | 6159.1 |
   | Co2SiO4 D20 | on | 2.0 | 14 | 6187.3 | 6499.3 |
   | Co2SiO4 D20 | on | 1.0 | 20 | 5812.7 | 6168.3 |
   | Co2SiO4 D20 | its own points | | 14 | 6529.5 | 6841.5 |
   | LBCO HRPT (N 3098) | off | 2.0 | 20 | 3747.1 | 4004.3 |
   | LBCO HRPT | off | 1.0 | 40 | 3629.2 | 4047.2 |
   | LBCO HRPT | on | 2.0 | 6 | 4049.6 | 4194.3 |
   | LBCO HRPT | on | 1.0 | 25 | 3653.4 | 3950.8 |
   | LBCO HRPT | its own points | | 5 | 4097.7 | 4234.4 |

   Rwp falls with every free point and BIC keeps falling on Co2SiO4, where extra points absorb model misfit, so
   neither chooses the tolerance on its own.

   `use_model` is the calculated peaks: `auto`, `subtract` or `ignore` (the owner, 2026-10-20; a file saved when
   it was a boolean reads `true` as `subtract` and `false` as `ignore`). `auto`, the default, subtracts the
   calculated peaks only when a calculated pattern exists and matches the data: after subtracting them at most 1%
   of the points fall below three times the noise, as peaks in the wrong place or too strong make them (a first
   rule that also asked most peaks in the data to lie at a calculated reflection never subtracted on LBCO HRPT or
   Si SEPD after a good fit, and was dropped). The estimate says which it chose and why, with that share, and
   Python reads it as
   `background_estimate.model_choice` and `.model_reason`. So one setting serves the first estimate of a project,
   before anything is fitted and when a start model can be far from the data, and the last one before the final
   fit.
5. **Auto mode.** A calculation, fit or scan refreshes the estimates once, first; the app also refreshes after
   every edit and when it opens a project. The engine owns the refresh: edi hands it the project a calculation
   would build and takes back the points and modes, so the engine never estimates a second time on the same
   project. An experiment in auto mode re-estimates its points with its settings when its included measured pattern
   or those settings differ from what its points came from; with `use_model` the estimate subtracts the peaks the
   current model calculates with every constrained parameter at its constraint's value, as the calculation holds
   it, so it does not depend on what calculation edi happens to hold or on whether the constraints were applied
   first. A scan estimates on its template once and fits every file with those points. Choosing auto makes the next
   calculation estimate. In auto mode the estimate owns the points or terms (the owner, 2026-10-20, replacing "a hand
   edit sets manual"): Python refuses an edit of a point's or term's id, position, order or value and a replaced
   table, saying to set the mode to manual first; the app's tables, on the Experiment and Analysis pages, read
   only, and a value written to one anyway is refused before anything changes. A project whose auto-mode rows differ
   from those the experiment had when auto was chosen, when it was loaded or when it last estimated, as a file edited
   outside edi can hold them, is refused by the next calculation, fit or save, the CLI's included, with the same
   advice or to estimate again; the mode never turns manual by itself. Freeing or fixing one stays allowed and is not
   an edit: the engine's digest of the points leaves the free flag out. A fit may refine free auto-mode points or
   terms (2026-10-21): the fitted values, and those an undo of the fit restores, become the ones the estimate is
   compared with, so the next calculation neither refuses nor estimates again. Only a change of the measured data
   or the settings estimates again; when that replaces values a fit refined, the messages say so as an information
   entry. A fit of a project mixing measured and calculation-only experiments keeps the fitted values of those it
   fitted. A native fit given measurements other than an auto-mode experiment's own, or whose estimate is due, is
   refused: its background belongs to the experiment's data. A series' estimate also follows its type and its
   origin or domain, and a type change in auto mode estimates the new type at the next calculation. The calc verb
   saves the project whenever it estimated, points or terms alike. A save that calculates other experiments keeps
   each experiment's whole background as edi holds it. Undo of Estimate restores the background's type with its rows
   and constants. A calculation refused after a fit gives the engine's reason. The
   settings are calculation inputs, so changing one makes the calculated pattern out of date.
6. **What the points came from is saved.** In auto mode the file carries `_background_estimate.inputs_digest` and
   `.points_digest`, the engine's digests of what the points came from and of the points themselves, so a reload
   with neither changed keeps its points without estimating, in edi and in the engine alike. Points changed in the
   file read as manual, and a file without the digests estimates at its first calculation. A save writes the
   points edi holds, even when a setting changed since they were estimated.
7. **The app.** On the Main tab the Background group offers Estimate for every type, in the place and with the
   `magic` icon of the Autodetect button ADR-0017 §4 showed disabled, and the owner's name for the action
   (2026-10-10), with the manual/auto choice beside the type, labelled "estimation mode" for every type, with a
   tooltip on both values (one line above the table holds the type, the estimation mode and a polynomial's origin or
   a Chebyshev series' x min and x max, all of one width; the owner, 2026-10-20); Estimate replaces the points or terms with the estimate the project's settings give, as
   one Undo step. In auto mode the table stays scrollable but is not edited (the owner, 2026-10-20): the id,
   position and order cells and the intensity or coefficient cells keep their look, a free value in green bold, and
   the value's context menu still frees or fixes it; each row's remove button and Add point or Add term, Id from
   position or Id from order, and Estimate are disabled until the mode is manual. The Extra tab shows the settings as the
   Background group's Extras part, for every type, in two columns of equal width and row spacing (the owner,
   2026-10-20): calculated peaks | anchor points (line-segment) or max terms (polynomial, Chebyshev); baseline
   method | peak width; curve smoothness | noise tolerance. Switching the type changes only the second box.
   Curve smoothness is disabled when the method is snip, which does not use it. Every combo value is lower case,
   and a box set to auto shows what auto resolves to after it in grey ("auto · arpls", "auto · subtract"); why
   auto subtracted or ignored the calculated peaks, the share of the points below three times the noise and the 1%
   rule, goes to the messages as an information entry each time Estimate runs with auto, or an automatic estimate
   runs after an edit (the owner, 2026-10-20). The calculated
   peaks have a tooltip of a few sentences, and the baseline method one naming the method in force in full with
   its reference, what it does and which fields it reads. Each blank field shows, in grey until something is
   typed, the value the estimate derives as a whole number: a blank count shows how many points or terms Estimate
   places, and a blank tolerance its default, 2; emptying a field makes it blank again. The summary and any
   warning go to the messages.

## Consequences

- The Python call and the app write the same points for the same experiment and settings: both call
  `edi::estimate_background`.
- Estimated points save and load as any other points, and can be freed for a fit one by one, in auto mode too.
- **A difference from diffraction-lib, on purpose.** Its ADR keeps the method and settings per call and persists
  only the points; edi keeps them in the project. `auto_estimate()` still takes diffraction-lib's per-call
  settings.
- Moving to a newer engine can change the points if the engine follows a newer diffraction-lib.

## Alternatives considered

| Alternative | Verdict (why rejected / deferred) |
|---|---|
| Estimate inside edi | Rejected: a second estimator would drift from the engine's, and the engine is where calculations live. |
| Estimate on load or before a fit when a background has no points | Rejected, as in diffraction-lib: it hides a modelling choice and fights hand-placed points. |
| Keep the placeholder's Autodetect wording | Rejected: the owner named the action Estimate (2026-10-10); the placeholder's place and icon stay. |
| Keep hand-placed points beside estimated ones | Deferred, as in diffraction-lib: every estimate replaces all points. |
| Refresh in edi and again in the engine | Rejected: the two would estimate from different calculations, and the points edi shows would not be the ones the engine's pattern used. |
| Estimate only line-segment backgrounds, as diffraction-lib | Rejected (the owner, 2026-10-20): a user who picks a polynomial or Chebyshev background should not lose the estimate. |
| A use_model check box, on by default | Rejected (the owner, 2026-10-20): a start model far from the data pulls the background into its misplaced peaks; auto checks first. |
| Estimate each scan file before its fit | Rejected for now: the number of points would vary between files, which a scan's fixed parameters and results columns cannot follow. |
| The settings per call only, in a dialog | Rejected (the owner, 2026-10-20): the settings are part of the project, as the other categories' are, and the CLI then needs no flags. |
